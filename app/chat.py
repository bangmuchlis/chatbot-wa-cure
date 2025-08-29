import json
import logging
import traceback
from fastapi import APIRouter, Request, HTTPException
from .config import settings
import re

# Use APIRouter to group routes for better organization
router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/webhook")
async def webhook_verify(request: Request):
    """WhatsApp webhook verification."""
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

@router.post("/webhook")
async def webhook_process(request: Request):
    """Processing incoming messages from WhatsApp."""
    mcp_client = request.app.state.mcp_client
    ollama_client = request.app.state.ollama_client
    whatsapp_client = request.app.state.whatsapp_client
    
    try:
        data = await request.json()
        if not data:
            return {"status": "OK"}

        if settings.DEBUG_LOGGING:
            logger.debug(f"Webhook received: {json.dumps(data, indent=2, ensure_ascii=False)}")

        if data.get('object') != 'whatsapp_business_account':
            return {"status": "OK"}

        if (data.get('entry') and len(data['entry']) > 0 and
                data['entry'][0].get('changes') and len(data['entry'][0]['changes']) > 0 and
                data['entry'][0]['changes'][0].get('value')):

            value = data['entry'][0]['changes'][0]['value']

            if value.get('messages') and len(value['messages']) > 0:
                message = value['messages'][0]

                if message.get('type') == 'text':
                    sender_id = message.get('from', '').strip()
                    
                    # --- FILTER LOGIC - FINAL ATTEMPT ---
                    # Use regex to extract only digits, making the check very robust.
                    sender_id_digits = re.sub(r'\D', '', sender_id)
                    
                    allowed_contact = "6285730784528"
                    if sender_id_digits != allowed_contact:
                        # logger.info(f"Message from '{sender_id}' ignored (filtered number: '{sender_id_digits}').")
                        return {"status": "OK"}
                    # --- END OF FILTER ---

                    incoming_text = message['text'].get('body', '').strip()

                    logger.info(f"📩 New message from {sender_id[-4:]}: {incoming_text[:50]}...")

                    try:
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

        return {"status": "OK"}

    except Exception as e:
        logger.error(f"Webhook error: {str(e)[:100]}...")
        if settings.DEBUG_LOGGING:
            logger.debug(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/")
async def index():
    """Endpoint status untuk memeriksa apakah bot berjalan."""
    return {"status": "✅ Chatbot WhatsApp sedang berjalan."}

@router.get("/test-ollama")
async def test_ollama(request: Request):
    """Test endpoint untuk memeriksa koneksi Ollama."""
    mcp_client = request.app.state.mcp_client
    ollama_client = request.app.state.ollama_client
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
