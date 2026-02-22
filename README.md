# Python Voice Agent with Gemini and Twilio

Este proyecto implementa un agente de voz telefónico en tiempo real utilizando Python (FastAPI), la API REST y Media Streams de Twilio, y la API Multimodal Live de Google Gemini (WebSockets).

El objetivo es lograr una conversación telefónica natural, con mínima latencia y con soporte para interrupciones (barge-in), donde el agente de IA inicia la conversación tan pronto como el usuario contesta la llamada.

## Requisitos Previos

1.  Python 3.9 o superior.
2.  Una cuenta de [Twilio](https://www.twilio.com/) con un número de teléfono adquirido y saldo disponible.
3.  Una clave API de [Google AI Studio](https://aistudio.google.com/) con acceso a la Multimodal Live API (ej: `gemini-2.5-flash-native-audio-latest`).
4.  [ngrok](https://ngrok.com/) para exponer tu servidor local a Internet y que Twilio pueda comunicarse con él.

## Configuración del Entorno Local

1.  **Clonar el repositorio y crear un entorno virtual:**
    ```bash
    python -m venv .venv
    # En Windows:
    .\.venv\Scripts\activate
    # En macOS/Linux:
    # source .venv/bin/activate
    ```

2.  **Instalar las dependencias:**
    ```bash
    pip install fastapi "uvicorn[standard]" twilio websockets google-genai python-dotenv
    ```

3.  **Configurar Variables de Entorno:**
    Renombra el archivo `.env.example` a `.env` (o crea uno directamente) en la raíz con el siguiente contenido y reemplaza con tus valores:
    ```env
    TWILIO_ACCOUNT_SID=TuAccountSIDDeTwilio
    TWILIO_AUTH_TOKEN=TuAuthTokenDeTwilio
    TWILIO_PHONE_NUMBER=TuNumeroDeTwilioConCodigoDeArea
    GEMINI_API_KEY=TuClaveAPIdeGoogleGemini

    # El host público que generará ngrok (se agregará en el siguiente paso)
    PUBLIC_URL=https://xxxx-xxx-xx-x-x.ngrok.app
    ```

## Ejecución y Pruebas

Para probar el agente localmente, necesitas exponer el puerto de tu servidor de desarrollo con `ngrok`.

1.  **Levantar ngrok en un terminal separado:**
    ```bash
    ngrok http 8000
    ```
    *Copia la URL `https` que te proporciona ngrok y ponla en la variable `PUBLIC_URL` de tu archivo `.env`.*

2.  **Iniciar el servidor FastAPI:**
    ```bash
    uvicorn app.main:app --reload
    ```
    *Cualquier cambio en el código reiniciará el servidor automáticamente.*

3.  **Realizar una llamada de prueba:**
    Utiliza una herramienta como Postman, cURL o cualquier cliente HTTP para enviar una petición `POST` al endpoint `/make-call` de tu servidor local. Asegúrate de incluir el número de destino (tu teléfono móvil) en el body.
    
    *Ejemplo con PowerShell:*
    ```powershell
    Invoke-RestMethod -Uri "http://localhost:8000/make-call" -Method Post -ContentType "application/json" -Body '{"destination_number": "+58414XXXXXXX"}'
    ```

    1. El servidor enviará la petición a Twilio para que llame al `destination_number`.
    2. Cuando contestes la llamada, Twilio iniciará el TwiML `<Connect><Stream>` apuntando al WebSocket de tu servidor (`/stream`).
    3. Python conectará automáticamente con Gemini por WebSocket y enviará el audio de tu llamada, mientras simultáneamente convierte el audio de respuesta de Gemini y lo inyecta a Twilio en tiempo real.
    4. El agente te saludará inmediatamente y podrás conversar fluidamente.

## Características Técnicas

-   **Conversión de Audio Bidireccional Nativa:** El proyecto utiliza transcodificación sobre la memoria por chunks para convertir entre el formato de la red telefónica (G.711 mu-law a 8kHz) y el formato requerido por Gemini (PCM lineal a 16kHz/24kHz) simultáneamente en tiempo real.
-   **Interrupciones (Barge-In):** Si interrumpes al agente mientras él está hablando, el evento `interrupted` de Gemini Live API enviará una señal asíncrona a Twilio para limpiar su buffer de reproducción al instante, frenando el discurso en seco replicando la dinámica humana.
