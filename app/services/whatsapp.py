import logging
import aiohttp

logger = logging.getLogger(__name__)

class WhatsAppClient:
    def __init__(self, access_token: str, phone_number_id: str, meta_api_version: str, debug_logging: bool = False):
        self.access_token = access_token
        self.debug_logging = debug_logging
        self.api_url = f"https://graph.facebook.com/{meta_api_version}/{phone_number_id}/messages"
        self.headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

    async def send_message(self, recipient_id: str, message_text: str, type_msg: str = "text") -> bool:
        logger.info(f"🤖 Sending answer to ...{recipient_id[-4:]}: {message_text}")
        
        if type_msg == "text":
            payload = {
                'messaging_product': 'whatsapp',
                'to': recipient_id,
                'type': 'text',
                'text': {'body': message_text}
            }
        else:  # template message
            payload = {
                'messaging_product': 'whatsapp',
                'to': recipient_id,
                'type': 'template',
                'template': {
                    "name": "default_template",
                    "language": {"code": "id"}
                }
            }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, json=payload, headers=self.headers) as response:
                    response_text = await response.text()
                    response.raise_for_status()
                    return True
        except aiohttp.ClientResponseError as e:
            logger.error(f"Failed to send message. Status: {e.status}, Message: {e.message}, Response: {response_text}")
            return False
        except Exception as e:
            logger.error(f"An unexpected error occurred while sending message: {e}")
            return False
