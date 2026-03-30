import logging
import sys
from pathlib import Path

from bson import ObjectId
from bson.errors import InvalidId
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils import now_utc
from users.models import Chat, Message, User
from .serializers import ChatCreateSerializer, ChatListResponseSerializer, ChatSummarySerializer, ChatWithMessagesSerializer, MessageCreateSerializer

logger = logging.getLogger(__name__)

USER_ROLE = "user"
ASSISTANT_ROLE = "assistant"
NO_CHAT_HISTORY = "Sin historial previo."

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from orchestrator import sistema_agentico_multidisciplinario
except Exception as exc:
    sistema_agentico_multidisciplinario = None
    logger.warning("No se pudo importar sistema_agentico_multidisciplinario desde manager.py: %s", exc)


def _serialize_message(message: Message):
    role = ASSISTANT_ROLE if message.sender_id == ASSISTANT_ROLE else USER_ROLE
    return {
        "content": message.content,
        "senderId": message.sender_id,
        "sendTime": message.send_time,
        "isAI": role == ASSISTANT_ROLE,
        "role": role,
    }


def _serialize_chat(chat: Chat, owner_id: str):
    return {
        "id": chat.id,
        "title": chat.title,
        "ownerId": owner_id,
        "participantA": owner_id,
        "participantB": ASSISTANT_ROLE,
    }


def _serialize_chat_with_messages(chat: Chat, owner_id: str):
    chat_data = _serialize_chat(chat, owner_id)
    chat_data["messages"] = [_serialize_message(message) for message in chat.messages]
    return chat_data


def _get_user_document(user_id: str):
    try:
        object_id = ObjectId(user_id)
    except InvalidId:
        return None
    return User.objects(id=object_id).first()


def _get_authenticated_user_document(request):
    request_user = getattr(request, "user", None)
    if not getattr(request_user, "is_authenticated", False):
        return None, Response({"detail": "Autenticación requerida"}, status=status.HTTP_401_UNAUTHORIZED)

    jwt_payload = getattr(request, "jwt_payload", None)
    token_subject = jwt_payload.get("sub") if isinstance(jwt_payload, dict) else None
    if token_subject and token_subject != request_user.id:
        logger.warning("Subject del token no coincide con el usuario autenticado")
        return None, Response({"detail": "Token inválido"}, status=status.HTTP_401_UNAUTHORIZED)

    user = _get_user_document(request_user.id)
    if not user:
        return None, Response({"detail": "Usuario no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    return user, None


def _find_chat(user: User, chat_id: int):
    for chat in user.chats:
        if chat.id == chat_id:
            return chat
    return None


def _save_chat_for_user(user: User, chat: Chat):
    for index, existing_chat in enumerate(user.chats):
        if existing_chat.id == chat.id:
            user.chats[index] = chat
            user.updated_at = now_utc()
            user.save()
            return

    user.chats.append(chat)
    user.updated_at = now_utc()
    user.save()


def _delete_chat_for_user(user: User, chat_id: int) -> bool:
    for index, existing_chat in enumerate(user.chats):
        if existing_chat.id == chat_id:
            del user.chats[index]
            user.updated_at = now_utc()
            user.save()
            return True
    return False


def _build_chat_history(chat: Chat, latest_user_message: str | None = None) -> str:
    history_lines = []

    for message in chat.messages:
        speaker = "IA" if message.sender_id == ASSISTANT_ROLE else "Usuario"
        history_lines.append(f"{speaker}: {message.content}")

    if latest_user_message:
        history_lines.append(f"Usuario: {latest_user_message}")

    return "\n".join(history_lines) or NO_CHAT_HISTORY


def _normalize_chat_history_payload(chat_history) -> str:
    if not chat_history:
        return NO_CHAT_HISTORY

    if isinstance(chat_history, str):
        normalized_history = chat_history.strip()
        return normalized_history or NO_CHAT_HISTORY

    if isinstance(chat_history, list):
        history_lines = []
        for item in chat_history:
            if isinstance(item, dict):
                content = str(item.get("content", "")).strip()
                if not content:
                    continue

                role = item.get("role")
                if role not in {USER_ROLE, ASSISTANT_ROLE}:
                    role = ASSISTANT_ROLE if item.get("isAI") else USER_ROLE

                speaker = "IA" if role == ASSISTANT_ROLE else "Usuario"
                history_lines.append(f"{speaker}: {content}")
                continue

            if isinstance(item, str) and item.strip():
                history_lines.append(item.strip())

        return "\n".join(history_lines) or NO_CHAT_HISTORY

    return NO_CHAT_HISTORY


def _invoke_agentic(message: str) -> str:
    if sistema_agentico_multidisciplinario is None:
        raise RuntimeError(
            "La implementación agentic no está disponible. Verifica manager.py y sus dependencias."
        )

    return sistema_agentico_multidisciplinario(message)


def _build_agentic_input(message: str, chat_history: str | None = None) -> str:
    normalized_history = (chat_history or "").strip()
    if not normalized_history or normalized_history == NO_CHAT_HISTORY:
        return message

    return (
        "Historial de la conversación:\n"
        f"{normalized_history}\n\n"
        f"Consulta actual del usuario: {message}"
    )


class ChatDeleteRequestSerializer(serializers.Serializer):
    chat_id = serializers.IntegerField(min_value=1)


class ChatMessageRequestSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=4000)
    chat_history = serializers.JSONField(required=False)


class ChatMessageResponseSerializer(serializers.Serializer):
    answer = serializers.CharField()
    sources = serializers.ListField(child=serializers.CharField())
    chat_history = serializers.CharField(required=False)


class ChatRoundTripResponseSerializer(serializers.Serializer):
    content = serializers.CharField()
    senderId = serializers.CharField()
    sendTime = serializers.DateTimeField()
    isAI = serializers.BooleanField()
    role = serializers.CharField()
    chatId = serializers.IntegerField()
    userMessage = serializers.DictField()
    messages = serializers.ListField(child=serializers.DictField())
    sources = serializers.ListField(child=serializers.CharField())


class ChatListCreateView(APIView):
    @swagger_auto_schema(
        tags=["Chats"],
        responses={200: ChatListResponseSerializer},
        security=[{"Bearer": []}],
    )
    def get(self, request):
        user, error_response = _get_authenticated_user_document(request)
        if error_response:
            return error_response

        return Response({"chats": [_serialize_chat(chat, str(user.id)) for chat in user.chats]})

    @swagger_auto_schema(
        tags=["Chats"],
        request_body=ChatCreateSerializer,
        responses={201: ChatSummarySerializer},
        security=[{"Bearer": []}],
    )
    def post(self, request):
        serializer = ChatCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        current_user, error_response = _get_authenticated_user_document(request)
        if error_response:
            return error_response

        chat = Chat(
            id=int(now_utc().timestamp() * 1000000),
            title=serializer.validated_data["title"],
            participant_a=str(current_user.id),
            participant_b=ASSISTANT_ROLE,
            messages=[],
        )
        _save_chat_for_user(current_user, chat)

        return Response(_serialize_chat(chat, str(current_user.id)), status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        tags=["Chats"],
        query_serializer=ChatDeleteRequestSerializer,
        responses={204: ""},
        security=[{"Bearer": []}],
    )
    def delete(self, request):
        serializer = ChatDeleteRequestSerializer(data=request.query_params or request.data)
        serializer.is_valid(raise_exception=True)

        current_user, error_response = _get_authenticated_user_document(request)
        if error_response:
            return error_response

        chat_id = serializer.validated_data["chat_id"]
        if not _delete_chat_for_user(current_user, chat_id):
            return Response({"detail": "Chat no encontrado"}, status=status.HTTP_404_NOT_FOUND)

        return Response(status=status.HTTP_204_NO_CONTENT)


class MessageListCreateView(APIView):
    @swagger_auto_schema(
        tags=["Messages"],
        responses={200: ChatWithMessagesSerializer},
        security=[{"Bearer": []}],
    )
    def get(self, request, chat_id: int):
        current_user, error_response = _get_authenticated_user_document(request)
        if error_response:
            return error_response

        chat = _find_chat(current_user, chat_id)
        if not chat:
            return Response({"detail": "Chat no encontrado"}, status=status.HTTP_404_NOT_FOUND)

        return Response(_serialize_chat_with_messages(chat, str(current_user.id)))

    @swagger_auto_schema(
        tags=["Messages"],
        request_body=MessageCreateSerializer,
        responses={201: ChatRoundTripResponseSerializer},
        security=[{"Bearer": []}],
    )
    def post(self, request, chat_id: int):
        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        current_user, error_response = _get_authenticated_user_document(request)
        if error_response:
            return error_response

        chat = _find_chat(current_user, chat_id)
        if not chat:
            return Response({"detail": "Chat no encontrado"}, status=status.HTTP_404_NOT_FOUND)

        user_message = Message(
            content=serializer.validated_data["content"],
            sender_id=USER_ROLE,
            send_time=now_utc(),
        )
        chat_history = _build_chat_history(chat)
        agentic_input = _build_agentic_input(user_message.content, chat_history)

        try:
            answer = _invoke_agentic(agentic_input)
            sources = []
        except Exception as exc:
            logger.error("Error al generar respuesta agentic para el chat %s: %s", chat_id, exc, exc_info=True)
            return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        assistant_message = Message(
            content=answer,
            sender_id=ASSISTANT_ROLE,
            send_time=now_utc(),
        )
        chat.messages.extend([user_message, assistant_message])
        _save_chat_for_user(current_user, chat)

        response_payload = _serialize_message(assistant_message)
        response_payload["chatId"] = chat.id
        response_payload["userMessage"] = _serialize_message(user_message)
        response_payload["messages"] = [_serialize_message(message) for message in chat.messages]
        response_payload["sources"] = sources
        return Response(response_payload, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        tags=["Chats"],
        responses={204: ""},
        security=[{"Bearer": []}],
    )
    def delete(self, request, chat_id: int):
        current_user, error_response = _get_authenticated_user_document(request)
        if error_response:
            return error_response

        if not _delete_chat_for_user(current_user, chat_id):
            return Response({"detail": "Chat no encontrado"}, status=status.HTTP_404_NOT_FOUND)

        return Response(status=status.HTTP_204_NO_CONTENT)


@swagger_auto_schema(
    method="post",
    request_body=ChatMessageRequestSerializer,
    responses={200: ChatMessageResponseSerializer},
    operation_description="Enviar un mensaje al manager agentic y obtener la misma respuesta que en consola.",
)
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def chat_view(request):
    """
    POST /chat/message/
    Body JSON: { "message": "..." }
    Respuesta: { "answer": "...", "sources": [] }
    """
    message = request.data.get("message", "").strip()
    if not message:
        return Response(
            {"error": "El mensaje no puede estar vacío."},
            status=status.HTTP_400_BAD_REQUEST,
        )


    chat_history = _normalize_chat_history_payload(request.data.get("chat_history"))
    #agentic_input = _build_agentic_input(message, chat_history)

    #try:
    #    answer = _invoke_agentic(agentic_input)
    #    return Response({"answer": answer, "sources": [], "chat_history": chat_history})
    try:
        answer = _invoke_agentic(message=message)
        return Response({"answer": answer, "sources": [], "chat_history": chat_history})
    except Exception as exc:
        logger.error("Error en chat_view agentic: %s", exc, exc_info=True)
        return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def health_view(request):
    """GET /chat/health/"""
    return Response(
        {
            "status": "ok",
            "runtime": "agentic-manager",
            "agentic_available": sistema_agentico_multidisciplinario is not None,
            "agentic_source": str(PROJECT_ROOT / "manager.py"),
        }
    )
