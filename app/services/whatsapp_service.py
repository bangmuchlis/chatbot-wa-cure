import logging
import aiohttp
import json
import os
from app.core.config import settings

logger = logging.getLogger(__name__)

class WhatsAppClient:
    def __init__(self, access_token: str, phone_number_id: str, meta_api_version: str, debug_logging: bool):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.api_url = f"https://graph.facebook.com/{meta_api_version}/{phone_number_id}/messages"
        self.media_url = f"https://graph.facebook.com/{meta_api_version}/{phone_number_id}/media"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        self.debug_logging = debug_logging
        
    async def upload_media(self, file_path: str, mime_type: str = "image/png") -> str | None:
        """Upload local image to WhatsApp API and return media_id"""
        if not os.path.exists(file_path):
            logger.error(f"⚠️ File not found: {file_path}")
            return None

        url = f"https://graph.facebook.com/v21.0/{self.phone_number_id}/media"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            async with aiohttp.ClientSession() as session:
                with open(file_path, "rb") as f:
                    form = aiohttp.FormData()
                    form.add_field("file", f, filename=os.path.basename(file_path), content_type=mime_type)
                    form.add_field("messaging_product", "whatsapp")

                    async with session.post(url, headers=headers, data=form) as response:
                        resp = await response.json()
                        if response.status == 200:
                            media_id = resp.get("id")
                            logger.info(f"📤 Uploaded media, id={media_id}")
                            return media_id
                        else:
                            logger.error(f"❌ Failed to upload media: {resp}")
                            return None
        except Exception as e:
            logger.error(f"Exception while uploading media: {e}")
            return None
    
        # Text response
    async def send_message(self, recipient_id: str, message_text: str) -> bool:
        if not message_text:
            logger.warning("⚠️ Attempted to send an empty message. Aborting.")
            return False

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_id,
            "type": "text",
            "text": {"body": message_text.strip()}
        }

        if self.debug_logging:
            logger.debug(f"Payload: {json.dumps(payload, indent=2)}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, headers=self.headers, json=payload) as response:
                    if 200 <= response.status < 300:
                        logger.info(f"✅ Message sent to {recipient_id}")
                        return True
                    else:
                        error_details = await response.json()
                        logger.error(f"❌ Failed to send message: {error_details}")
                        return False
        except Exception as e:
            logger.error(f"Exception while sending message: {e}")
            return False
        
    # Image response
    # async def send_image(self, recipient_id: str, media: str, is_link: bool = False) -> bool:
    #     """
    #     Send image to WhatsApp.
    #     - is_link=True →  public URL.
    #     - is_link=False → media_id upload result.
    #     """
    #     image_payload = {"link": media} if is_link else {"id": media}

    #     payload = {
    #         "messaging_product": "whatsapp",
    #         "to": recipient_id,
    #         "type": "image",
    #         "image": image_payload
    #     }

    #     try:
    #         async with aiohttp.ClientSession() as session:
    #             async with session.post(self.api_url, headers=self.headers, json=payload) as response:
    #                 if 200 <= response.status < 300:
    #                     logger.info(f"✅ Image sent to {recipient_id} ({'link' if is_link else 'id'})")
    #                     return True
    #                 else:
    #                     error_details = await response.json()
    #                     logger.error(f"❌ Failed to send image: {error_details}")
    #                     return False
    #     except Exception as e:
    #         logger.error(f"Exception sending image: {e}")
    #         return False
    
   # Image response
    async def send_image(self, recipient_id: str, media: str, is_link: bool = False) -> bool:
        """
        Send image to WhatsApp.
        - is_link=True → public URL
        - is_link=False → media_id upload result
        """
        # --- PERUBAHAN UTAMA: Hapus parameter 'filename' ---
        image_payload = {"link": media} if is_link else {"id": media}

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_id,
            "type": "image",
            "image": image_payload
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, headers=self.headers, json=payload) as response:
                    if 200 <= response.status < 300:
                        logger.info(f"✅ Image sent to {recipient_id} ({'link' if is_link else 'id'})")
                        return True
                    else:
                        error_details = await response.json()
                        logger.error(f"❌ Failed to send image: {error_details}")
                        return False
        except Exception as e:
            logger.error(f"Exception sending image: {e}")
            return False

    # Document response
    async def send_document(self, recipient_id: str, media: str, filename: str, is_link: bool = False) -> bool:
        """
        Send document to WhatsApp.
        - is_link=True →  public URL.
        - is_link=False → media_id upload result..
        """
        document_payload = {"link": media, "filename": filename} if is_link else {"id": media, "filename": filename}

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_id,
            "type": "document",
            "document": document_payload
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, headers=self.headers, json=payload) as response:
                    if 200 <= response.status < 300:
                        logger.info(f"✅ Document sent to {recipient_id} ({filename})")
                        return True
                    else:
                        error_details = await response.json()
                        logger.error(f"❌ Failed to send document: {error_details}")
                        return False
        except Exception as e:
            logger.error(f"Exception sending document: {e}")
            return False
