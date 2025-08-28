import requests
import logging
# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class WhatsAppClient:
    def __init__(self, access_token: str, phone_number_id: str, meta_api_version: str, debug_logging: bool = False):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.meta_api_version = meta_api_version
        self.debug_logging = debug_logging
        self.api_url = f"https://graph.facebook.com/{meta_api_version}/{phone_number_id}/messages"

    async def send_message(self, recipient_id: str, message_text: str, type_msg: str = "text") -> bool:
        """
        Mengirim pesan ke WhatsApp Cloud API.
        
        Args:
            recipient_id: ID penerima (nomor telepon).
            message_text: Teks pesan yang akan dikirim.
            type_msg: Tipe pesan ('text' atau 'template').
        
        Returns:
            True jika pengiriman berhasil, False jika gagal.
        """
        if type_msg == "text":
            payload = {
                'messaging_product': 'whatsapp',
                'to': recipient_id,
                'type': 'text',
                'text': {'body': message_text}
            }
        else:
            payload = {
                'messaging_product': 'whatsapp',
                'to': recipient_id,
                'type': 'template',
                'template': {
                    "name": "default_template",
                    "language": {"code": "id"}
                }
            }

        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

        try:
            response = requests.post(self.api_url, json=payload, headers=headers)
            response.raise_for_status()

            logger.info(f"✅ Message sent to {recipient_id[-4:]}: {response}")
            if self.debug_logging:
                print(f"📤 Response: {response.status_code}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to send message: {str(e)[:100]}...")
            if self.debug_logging and hasattr(e, 'response') and e.response is not None:
                print(f"📄 Response body: {e.response.text}")
            return False