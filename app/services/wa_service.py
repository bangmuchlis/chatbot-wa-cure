import httpx
import logging
from app.config import settings

logger = logging.getLogger(__name__)

async def send_whatsapp_message(recipient_id: str, message_text: str) -> bool:
    url = f"https://graph.facebook.com/{settings.META_API_VERSION}/{settings.PHONE_NUMBER_ID}/messages"
    payload = {
        'messaging_product': 'whatsapp',
        'to': recipient_id,
        'type': 'text',
        'text': {'body': message_text}
    }
    headers = {
        'Authorization': f'Bearer {settings.ACCESS_TOKEN}',
        'Content-Type': 'application/json'
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            logger.info(f"✅ Pesan terkirim ke {recipient_id[-4:]}")
            return True
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Gagal mengirim pesan: {e.response.status_code} - {e.response.text}")
            return False
        except httpx.RequestError as e:
            logger.error(f"❌ Kesalahan jaringan saat mengirim pesan: {e}")
            return False

