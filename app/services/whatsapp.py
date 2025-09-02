# Di dalam file services/whatsapp.py

import logging
import aiohttp
import json

logger = logging.getLogger(__name__)

class WhatsAppClient:
    def __init__(self, access_token: str, phone_number_id: str, meta_api_version: str, debug_logging: bool):
        self.api_url = f"https://graph.facebook.com/{meta_api_version}/{phone_number_id}/messages"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        self.debug_logging = debug_logging

    async def send_message(self, recipient_id: str, message_text: str) -> bool:
        """Sends a text message to a WhatsApp user."""
        if not message_text:
            logger.warning("Attempted to send an empty message. Aborting.")
            return False

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_id,
            "type": "text",
            "text": {
                "body": message_text.strip()
            }
        }

        logger.info(f"🤖 Sending answer to ...{recipient_id[-4:]}:")
        if self.debug_logging:
            logger.debug(f"Payload: {json.dumps(payload, indent=2)}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, headers=self.headers, json=payload) as response:
                    if 200 <= response.status < 300:
                        logger.info(f"Message sent successfully to {recipient_id}. Status: {response.status}")
                        return True
                    else:
                        error_details = await response.json()
                        logger.error(
                            f"Failed to send message. Status: {response.status}, "
                            f"Message: {response.reason}, Response: {json.dumps(error_details)}"
                        )
                        return False
        except Exception as e:
            logger.error(f"An exception occurred while sending message: {str(e)}")
            return False