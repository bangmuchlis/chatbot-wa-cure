import logging
from fastapi import APIRouter, Request, Response, HTTPException
from app.services.wa_service import send_whatsapp_message
from app.config import settings
from app.crew import run_crew

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get('/webhook', summary="Verifikasi Webhook")
def verify_webhook(request: Request):
    """
    Menangani permintaan verifikasi webhook dari Meta.
    """
    mode = request.query_params.get('hub.mode')
    token = request.query_params.get('hub.verify_token')
    challenge = request.query_params.get('hub.challenge')

    if mode == 'subscribe' and token == settings.VERIFY_TOKEN:
        logger.info('✅ Webhook terverifikasi')
        return Response(content=challenge, status_code=200)
    else:
        logger.warning('❌ Verifikasi webhook gagal')
        raise HTTPException(status_code=403, detail="Forbidden: Verifikasi gagal")

@router.post('/webhook', summary="Tangani Pesan Masuk")
async def handle_webhook(request: Request):
    data = await request.json()
    logger.debug(f"Webhook diterima: {data}")

    try:
        if data.get("entry"):
            message = data["entry"][0]["changes"][0]["value"]["messages"][0]
            if message["type"] == "text":
                sender_id = message["from"]
                incoming_text = message["text"]["body"]
                logger.info(f"💬 Pesan baru dari {sender_id[-4:]}: '{incoming_text}'")

                crew_response = run_crew(incoming_text)
                
                await send_whatsapp_message(sender_id, crew_response)
        
        return Response(content='OK', status_code=200)
    except Exception as e:
        logger.error(f"⚠️ Gagal memproses webhook: {e}", exc_info=True)
        return Response(content='Internal Server Error', status_code=500)
