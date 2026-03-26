from rest_framework.decorators import api_view, authentication_classes, permission_classes, parser_classes
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from .serializers import BranchCreateSerializer, UploadPDFSerializer
from .services import (
    list_branches,
    create_branch,
    list_branch_files,
    save_pdfs,
    rebuild_embeddings,
    delete_branch,
    delete_pdf
)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def get_branches(request):
    """
    GET /agent/branches/
    Respuesta: { "branches": [...] }
    """

    branches = list_branches()

    return Response({
        "branches": branches
    })

@swagger_auto_schema(
    method="post",
    request_body=BranchCreateSerializer,
    operation_description="Crear una nueva rama médica"
)
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def create_branch_view(request):
    """
    POST /agent/branch/
    Body JSON: { "name": "..." }
    Respuesta: { "message": "..." }
    """

    serializer = BranchCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    name = serializer.validated_data["name"]

    try:
        create_branch(name)

        return Response({
            "message": f"Rama '{name}' creada correctamente"
        })

    except Exception as e:

        return Response({
            "error": str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def get_branch_files(request, branch):
    """
    GET /agent/branch/{branch}/files/
    Respuesta: { "branch": "...", "files": [...] }
    """

    try:
        files = list_branch_files(branch)

        return Response({
            "branch": branch,
            "files": files
        })

    except Exception as e:

        return Response({
            "error": str(e)
        }, status=status.HTTP_404_NOT_FOUND)

@swagger_auto_schema(
    method="post",
    manual_parameters=[
        openapi.Parameter(
            "branch",
            openapi.IN_FORM,
            description="Nombre de la rama médica",
            type=openapi.TYPE_STRING,
            required=True
        ),
        openapi.Parameter(
            "files",
            openapi.IN_FORM,
            description="PDFs a subir",
            type=openapi.TYPE_ARRAY,
            items=openapi.Items(type=openapi.TYPE_FILE),
            required=True
        ),
    ],
    consumes=["multipart/form-data"],
)
@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
@authentication_classes([])
@permission_classes([AllowAny])
def upload_pdfs_view(request):

    branch = request.data.get("branch")
    files = request.FILES.getlist("files")

    if not branch:
        return Response({"error": "branch es requerido"}, status=400)

    try:

        saved = save_pdfs(branch, files)

        return Response({
            "message": "PDFs subidos correctamente",
            "files": saved
        })

    except Exception as e:

        return Response({
            "error": str(e)
        }, status=400)


@api_view(["POST"])
@authentication_classes([])
@parser_classes([])
@permission_classes([AllowAny])
def rebuild_embeddings_view(request):
    """
    POST /agent/rebuild_embeddings/
    Respuesta: { "message": "...", "output": "..." }
    """

    try:

        output = rebuild_embeddings()

        return Response({
            "message": "Embeddings regenerados correctamente",
            "output": output
        })

    except Exception as e:

        return Response({
            "error": str(e)
        }, status=500)


@swagger_auto_schema(
    method="delete",
    operation_description="Eliminar una rama médica completa"
)
@api_view(["DELETE"])
@authentication_classes([])
@permission_classes([AllowAny])
def delete_branch_view(request, branch):

    result = delete_branch(branch)
    if result is True:

        return Response({
            "message": f"Rama '{branch}' eliminada correctamente"
        })
    else:
        return Response({
            "error": result
        }, status=500)
    


@swagger_auto_schema(
    method="delete",
    operation_description="Eliminar un PDF específico de una rama"
)
@api_view(["DELETE"])
@authentication_classes([])
@permission_classes([AllowAny])
def delete_pdf_view(request, branch, filename):

    result = delete_pdf(branch, filename)

    if result is True:

        return Response({
            "message": f"Archivo '{filename}' eliminado de '{branch}'"
        })
    else:
        return Response({
            "error": result
        }, status=500)
        