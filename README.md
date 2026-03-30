
# MedBotics Backend

MedBotics es una plataforma diseñada para ejecutar agentes de IA especializados en distintos dominios. Este repositorio contiene el **backend**, encargado de procesar documentos PDF, gestionar el entrenamiento de agentes específicos y enrutar consultas mediante un sistema agentic ya configurado que identifica automáticamente el área adecuada para cada petición.

---

## 🚀 Características principales
- Ingesta y procesamiento de documentos PDF para entrenamiento de agentes.
- Arquitectura agentic que detecta el dominio más adecuado para responder cada consulta.
- Integración mediante API para comunicación con clientes externos.
- Configuración flexible mediante variables de entorno.

---

## 🔧 Ejecución del proyecto
A continuación se detalla el proceso recomendado para ejecutar el backend en un entorno local.

### 1. Crear entorno virtual
```bash
python -m venv venv
```

### 2. Activar el entorno virtual
**Windows (PowerShell):**
```bash
.\venv\Scripts\Activate.ps1
```
**Linux / macOS:**
```bash
source venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
Crea un archivo `.env` en la raíz del proyecto e incorpora los valores necesarios.

Puedes usar `.env.example` como referencia.

### 5. Ejecutar el servidor
Asegúrate de estar dentro del entorno virtual antes de correr:
```bash
python manager.py runserver
```

---

## ✅ Notas adicionales
- Verifica que tus PDFs estén correctamente formateados antes de subirlos.
- Mantén actualizado el entorno virtual cuando modifiques dependencias.
- Para despliegues, se recomienda configurar un servidor WSGI como Gunicorn o Uvicorn.
