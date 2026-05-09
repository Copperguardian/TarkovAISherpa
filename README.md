# Tarkov AI Sherpa

## Descripción del Proyecto
Tarkov AI Sherpa es un asistente inteligente basado en modelos de lenguaje (LLM) diseñado específicamente para el ecosistema del videojuego Escape from Tarkov. Su objetivo principal es actuar como un sherpa táctico, proporcionando información en tiempo real, asesoramiento sobre equipamiento, análisis balístico y guías de misiones. El sistema combina una base de conocimiento documental mediante Generación Aumentada por Recuperación (RAG) con capacidades de búsqueda de datos estructurados utilizando la API GraphQL de tarkov.dev.

## Funcionalidades Principales

* Agente Conversacional Especializado: Sistema basado en LangChain y LangGraph que mantiene el contexto de las conversaciones (memoria) y adapta sus respuestas al perfil táctico del usuario.
* Perfil de Usuario Persistente: Autenticación segura mediante JWT y Argon2. Los usuarios almacenan su nivel, facción, progresión del refugio (hideout) y estilo de juego. El agente parametriza sus recomendaciones basándose en este perfil (por ejemplo, sugiriendo munición de bajo costo para niveles bajos).
* Historial de Conversaciones: Soporte para múltiples hilos de conversación. Los usuarios pueden revisar consultas anteriores y retomar contextos analíticos previos de forma transparente.
* Integración de Datos Dinámicos (`tools.py`):
  El agente dispone de herramientas especializadas para extraer información en tiempo real del ecosistema del juego:
  - **Munición** (`get_ammo`, `get_multiAmmo`): Recupera estadísticas balísticas, de daño y penetración.
  - **Armamento** (`get_weapons_by_name`, `get_weapons_by_category`, `get_weapons_by_caliber`, `get_multi_weapons`): Búsqueda y filtrado exhaustivo de armas.
  - **Misiones** (`search_tasks`): Recuperación de objetivos, ubicaciones y recompensas.
  - **Objetos y Economía** (`search_items`): Búsqueda de valor de mercado en tiempo real (flea market) y comerciantes.
  - **Refugio** (`search_hideout`): Requisitos de construcción y beneficios de los módulos.
  - **Mapas** (`get_map_info`): Recuperación de detalles y características de las zonas de incursión.
  - **Progreso** (`get_user_progress`): Consulta dinámica del avance del jugador en el juego.
* **Model Context Protocol (MCP)**: El backend incluye la infraestructura básica (`langchain-mcp-adapters`) para la comunicación con servidores MCP. Aunque no es estrictamente necesario para la funcionalidad principal, este protocolo permite expandir modularmente el contexto del agente con herramientas estandarizadas externas y requiere tener descargado el servidor mcp para que el backend se ejecute correctamente.
https://github.com/Yaniddze/tarkov-mcp

* Interfaz Táctica: Frontend desarrollado en React con un diseño industrial, orientado a reducir la carga cognitiva del usuario y asemejarse a un terminal militar.

## Tecnologías Utilizadas

### Backend
* FastAPI: Framework para el desarrollo de la API REST de alto rendimiento.
* SQLAlchemy: ORM utilizado para la gestión de la base de datos relacional SQLite.
* LangChain & LangGraph: Orquestación del flujo cognitivo del agente, definición de herramientas (tools) y gestión de persistencia de memoria.
* Python-Jose & Passlib: Manejo criptográfico de tokens de sesión y contraseñas.

### Frontend
* React.js: Construcción de la arquitectura basada en componentes.
* Vite: Entorno de desarrollo, compilación y empaquetado.
* Axios: Gestión de peticiones HTTP e interceptores para control de sesiones expiradas.
* Tailwind CSS: Framework de utilidades para el diseño adaptativo y estilizado del sistema.

### Inteligencia Artificial y Datos
* Ollama: Motor de ejecución para operar modelos fundacionales localmente, garantizando privacidad y menor latencia en las respuestas.
* ChromaDB: Base de datos vectorial utilizada para la indexación y recuperación semántica de documentos (RAG).
* GraphQL: Lenguaje de consulta para interactuar eficientemente con fuentes de datos de terceros.

## Configuración e Instalación

### Requisitos Previos
* Python 3.10 o versión superior.
* Node.js v18 o versión superior.
* Ollama instalado y ejecutándose en la máquina host con el modelo pertinente previamente descargado (por ejemplo: `ollama pull llama3`).

### Instalación del Backend
1. Clonar el repositorio y acceder al directorio raíz.
2. Crear un entorno virtual aislado:
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```
3. Instalar las dependencias definidas:
   ```bash
   pip install -r requirements.txt
   ```
4. Establecer las variables de entorno. Crear un archivo `.env` en la carpeta `Backend` e incluir los parámetros criptográficos:
   ```env
   SECRET_KEY=clave_criptografica_segura
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=1440
   ```
5. Iniciar el servidor web:
   ```bash
   cd Backend
   uvicorn main:app --reload --port 8000
   ```
6. Cambiar el modelo. Por defecto se usa un modelo con una IP en local. Esto se debe cambiar para usar otro modelo local o la funcionalidad con chatnvidia.

### Instalación del Frontend
1. Acceder al subdirectorio del cliente:
   ```bash
   cd Frontend/sherpa-ui
   ```
2. Instalar los módulos de Node:
   ```bash
   npm install
   ```
3. Iniciar el servidor de desarrollo:
   ```bash
   npm run dev
   ```

## Arquitectura del Sistema
El proyecto emplea un patrón cliente-servidor donde la lógica de negocio compleja recae en un agente autónomo de backend. El ciclo de procesamiento se inicia cuando el cliente transmite una orden. FastAPI enruta la petición hacia LangGraph. El agente clasifica la intención de la consulta y decide procesarla utilizando conocimiento implícito, delegar en una búsqueda vectorial sobre ChromaDB (para documentación densa de misiones), o invocar scripts de GraphQL dirigidos a tarkov.dev para obtener datos volátiles. La respuesta consolidada se envía al frontend para su renderizado.

## Áreas de Mejora y Evolución
* Optimización de Contexto: Diseño e implementación de un algoritmo de resumen de memoria que compacte hilos de conversación largos, mitigando la degradación del rendimiento al aproximarse al límite de tokens del LLM.
* Soporte Agnostic para Modelos: Modularizar el instanciador del agente para permitir transiciones sin fricción entre modelos operados localmente y APIs comerciales externas, dependiendo del tipo de carga de trabajo.
* Procesamiento RAG Avanzado: Refinar las estrategias de fragmentación (chunking) e integrar algoritmos de re-ranking que perfeccionen la extracción de datos topológicos y guías espaciales complejas.
* Observabilidad: Despliegue de un sistema de trazabilidad (tracing) integral para monitorizar la latencia individual de las herramientas y evaluar el porcentaje de fallos en llamadas a endpoints externos.
* Interfaces Multimodales: Investigación sobre la integración de sistemas de transcripción de voz local para permitir consultas tácticas mediante comandos de voz durante el transcurso de una sesión de juego.
