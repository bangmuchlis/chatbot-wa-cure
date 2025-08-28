import json
import logging
import traceback
from fastapi import FastAPI, Request, HTTPException

# Import the centralized settings
from config import settings
from services.mcp import MCPClient
from services.ollama import OllamaClient
from services.whatsapp import WhatsAppClient

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# Initialize clients using the settings object
mcp_client = MCPClient(server_script_path="server.py", debug_logging=settings.DEBUG_LOGGING)
ollama_client = OllamaClient(url=settings.OLLAMA_URL, model=settings.OLLAMA_MODEL, debug_logging=settings.DEBUG_LOGGING)
whatsapp_client = WhatsAppClient(
    access_token=settings.ACCESS_TOKEN,
    phone_number_id=settings.PHONE_NUMBER_ID,
    meta_api_version=settings.META_API_VERSION,
    debug_logging=settings.DEBUG_LOGGING
)

@app.on_event("startup")
async def startup_event():
    """Initialize MCP connection on startup."""
    logger.info("Starting MCP client connection...")
    await mcp_client.connect()

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up MCP connection on shutdown."""
    logger.info("Shutting down MCP client...")
    await mcp_client.cleanup()

@app.get("/webhook")
async def webhook_verify(request: Request):
    """Verifikasi webhook WhatsApp."""
    mode = request.query_params.get('hub.mode')
    token = request.query_params.get('hub.verify_token')
    challenge = request.query_params.get('hub.challenge')

    if mode and token:
        if mode == 'subscribe' and token == settings.VERIFY_TOKEN:
            logger.info("Webhook verified successfully")
            return int(challenge)
        else:
            logger.error("Webhook verification failed")
            raise HTTPException(status_code=403, detail="Forbidden: Webhook verification failed")

    logger.warning("Bad request: Missing parameters")
    raise HTTPException(status_code=400, detail="Bad Request: Missing parameters")

@app.post("/webhook")
async def webhook_process(request: Request):
    """Memproses pesan masuk dari WhatsApp."""
    try:
        data = await request.json()
        if not data:
            return {"status": "OK"}

        if settings.DEBUG_LOGGING:
            logger.debug(f"Webhook received: {json.dumps(data, indent=2, ensure_ascii=False)}")

        if data.get('object') != 'whatsapp_business_account':
            return {"status": "OK"}

        if (data.get('entry') and
                len(data['entry']) > 0 and
                data['entry'][0].get('changes') and
                len(data['entry'][0]['changes']) > 0 and
                data['entry'][0]['changes'][0].get('value')):

            value = data['entry'][0]['changes'][0]['value']

            if value.get('messages') and len(value['messages']) > 0:
                message = value['messages'][0]

                if message.get('type') == 'text':
                    sender_id = message.get('from')
                    incoming_text = message['text'].get('body', '').strip()

                    logger.info(f"New message from {sender_id[-4:]}: {incoming_text[:50]}...")

                    try:
                        # Get knowledge base and generate response
                        knowledge_base = await mcp_client.get_knowledge_base()
                        ai_response = await ollama_client.get_response(incoming_text, knowledge_base)

                        if len(ai_response) > 4000:
                            ai_response = ai_response[:4000] + "..."

                        success = await whatsapp_client.send_message(sender_id, ai_response)
                        if not success:
                            logger.error(f"Failed to send reply to {sender_id[-4:]}")

                    except Exception as e:
                        logger.error(f"Error processing message: {str(e)[:100]}...")
                        await whatsapp_client.send_message(sender_id, "Maaf, saya sedang mengalami masalah. Coba lagi nanti.")

                elif settings.DEBUG_LOGGING:
                    logger.warning(f"Unsupported message type: {message.get('type')}")

            elif value.get('statuses') and settings.DEBUG_LOGGING:
                for status in value['statuses']:
                    if status.get('status') == 'read':
                        logger.info("Message read by user")

        return {"status": "OK"}

    except Exception as e:
        logger.error(f"Webhook error: {str(e)[:100]}...")
        if settings.DEBUG_LOGGING:
            logger.debug(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/")
async def index():
    """Endpoint status untuk memeriksa apakah bot berjalan."""
    return {"status": "✅ Chatbot WhatsApp sedang berjalan."}

@app.get("/test")
async def test_webhook():
    """Test endpoint untuk memverifikasi akses webhook."""
    return {
        'status': 'webhook accessible',
        'phone_number_id': settings.PHONE_NUMBER_ID,
        'api_version': settings.META_API_VERSION,
        'ollama_url': settings.OLLAMA_URL,
        'ollama_model': settings.OLLAMA_MODEL,
        'debug_logging': settings.DEBUG_LOGGING,
        'verify_token_set': bool(settings.VERIFY_TOKEN),
        'access_token_set': bool(settings.ACCESS_TOKEN)
    }

@app.get("/test-ollama")
async def test_ollama():
    """Test endpoint untuk memeriksa koneksi Ollama."""
    try:
        test_message = "Halo, siapa kamu?"
        knowledge_base = await mcp_client.get_knowledge_base()
        response = await ollama_client.get_response(test_message, knowledge_base)
        return {
            'status': 'success',
            'ollama_url': settings.OLLAMA_URL,
            'model': settings.OLLAMA_MODEL,
            'test_message': test_message,
            'ollama_response': response
        }
    except Exception as e:
        logger.error(f"Ollama test error: {str(e)}")
        return {
            'status': 'error',
            'ollama_url': settings.OLLAMA_URL,
            'model': settings.OLLAMA_MODEL,
            'error': str(e)
        }

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting WhatsApp Chatbot with Ollama and MCP...")
    logger.info(f"Model: {settings.OLLAMA_MODEL}")
    logger.info(f"Debug logging: {settings.DEBUG_LOGGING}")
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)
