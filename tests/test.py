import os
import requests
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import json
import logging
from datetime import datetime

# Setup logging ke file dan konsol
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug.log', encoding='utf-8'),  # Gunakan encoding UTF-8 untuk file
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI()

# Environment variables
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
PHONE_NUMBER_ID = os.getenv('PHONE_NUMBER_ID')
VERIFY_TOKEN = os.getenv('VERIFY_TOKEN')
META_API_VERSION = os.getenv('META_API_VERSION')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL')
OLLAMA_URL = os.getenv('OLLAMA_URL')
META_API_URL = f"https://graph.facebook.com/{META_API_VERSION}/{PHONE_NUMBER_ID}/messages"
DEBUG_LOGGING = os.getenv('DEBUG_LOGGING', 'False').lower() == 'true'
PORT = int(os.getenv('PORT', '8000'))

# Log konfigurasi saat startup
logger.debug(f"Environment variables - PHONE_NUMBER_ID: {PHONE_NUMBER_ID}, META_API_VERSION: {META_API_VERSION}, "
             f"OLLAMA_URL: {OLLAMA_URL}, OLLAMA_MODEL: {OLLAMA_MODEL}, DEBUG_LOGGING: {DEBUG_LOGGING}, "
             f"VERIFY_TOKEN_SET: {bool(VERIFY_TOKEN)}, ACCESS_TOKEN_SET: {bool(ACCESS_TOKEN)}, PORT: {PORT}")

async def get_ollama_response(user_message: str) -> str:
    """
    Mengirim pesan ke Ollama Mistral dan mendapatkan response.
    """
    try:
        if DEBUG_LOGGING:
            logger.debug(f"User message to Ollama: {user_message}")
        
        # Template prompt dalam bahasa Indonesia
        system_prompt = """Anda adalah asisten AI yang ramah dan membantu melalui WhatsApp. 
        Gunakan aturan berikut:
        1. Selalu jawab dalam bahasa Indonesia yang sopan dan mudah dipahami
        2. Jawaban harus singkat dan jelas (maksimal 3-4 kalimat)
        3. Gunakan emoji yang sesuai untuk membuat percakapan lebih menyenangkan
        4. Jika ditanya tentang identitas, katakan Anda adalah asisten AI
        5. Berikan jawaban yang informatif dan membantu
        6. Jika tidak tahu jawaban, akui dengan jujur dan sarankan alternatif

        Pertanyaan pengguna: {user_message}

        Jawaban Anda:"""
        
        full_prompt = system_prompt.format(user_message=user_message)
        
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "max_tokens": 500,
                "top_p": 0.9,
                "repeat_penalty": 1.1
            }
        }
        
        logger.debug(f"Sending request to Ollama: {OLLAMA_URL}/api/generate with payload: {json.dumps(payload, indent=2)}")
        response = requests.post(
            f"{OLLAMA_URL}/api/generate", 
            json=payload, 
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            ollama_reply = result.get('response', '').strip()
            ollama_reply = ollama_reply.replace('Jawaban Anda:', '').strip()
            
            if DEBUG_LOGGING:
                logger.debug(f"Ollama response: {ollama_reply}")
            return ollama_reply
        else:
            logger.error(f"Ollama error: Status code {response.status_code}, Response: {response.text}")
            return "Maaf, saya sedang mengalami masalah teknis. Silahkan coba lagi nanti!"
            
    except requests.exceptions.Timeout:
        logger.error("Ollama timeout")
        return "Maaf, respons terlalu lama. Coba ulangi pertanyaan anda."
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Cannot connect to Ollama: {str(e)}")
        return "Maaf, saya sedang offline. Pastikan sistem sedang berjalan."
    except Exception as e:
        logger.error(f"Ollama error: {str(e)}")
        return "Maaf, terjadi kesalahan sistem. Silahkan coba lagi nanti!"

async def send_whatsapp_message(recipient_id: str, message_text: str, type_msg: str = "text") -> bool:
    """
    Mengirim pesan teks ke WhatsApp Cloud API.
    """
    url = f"https://graph.facebook.com/{META_API_VERSION}/{PHONE_NUMBER_ID}/messages"
    
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
        'Authorization': f'Bearer {ACCESS_TOKEN}',
        'Content-Type': 'application/json'
    }

    try:
        logger.debug(f"Sending WhatsApp message to {recipient_id}: {json.dumps(payload, indent=2)}")
        response = requests.post(META_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        
        logger.info(f"Message sent to {recipient_id[-4:]}")
        if DEBUG_LOGGING:
            logger.debug(f"WhatsApp API response: Status {response.status_code}, Body: {response.text}")
        
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send message to {recipient_id[-4:]}: {str(e)[:100]}...")
        if DEBUG_LOGGING and hasattr(e, 'response') and e.response is not None:
            logger.debug(f"WhatsApp API error response: {e.response.text}")
        return False

@app.get("/webhook")
async def webhook_verify(request: Request):
    mode = request.query_params.get('hub.mode')
    token = request.query_params.get('hub.verify_token')
    challenge = request.query_params.get('hub.challenge')

    logger.debug(f"Webhook verification attempt: mode={mode}, token={token}, challenge={challenge}")
    
    if mode and token:
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            logger.info(f"Webhook verified with challenge: {challenge}")
            return int(challenge)
        else:
            logger.error(f"Webhook verification failed: mode={mode}, token={token}")
            raise HTTPException(status_code=403, detail="Forbidden: Webhook verification failed")
    
    logger.warning("Bad request: Missing parameters")
    raise HTTPException(status_code=400, detail="Bad Request: Missing parameters")

@app.post("/webhook")
async def webhook_process(request: Request):
    try:
        data = await request.json()
        logger.debug(f"Webhook received: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        if not data:
            logger.warning("Webhook received empty data")
            return {"status": "OK"}

        if data.get('object') != 'whatsapp_business_account':
            logger.warning(f"Invalid object type: {data.get('object')}")
            return {"status": "OK"}

        if (data.get('entry') and
            len(data['entry']) > 0 and
            data['entry'][0].get('changes') and
            len(data['entry'][0]['changes']) > 0 and
            data['entry'][0]['changes'][0].get('value')):
            
            value = data['entry'][0]['changes'][0]['value']
            
            if value.get('messages') and len(value['messages']) > 0:
                message = value['messages'][0]
                logger.debug(f"Processing message: {json.dumps(message, indent=2, ensure_ascii=False)}")

                if message.get('type') == 'text':
                    sender_id = message.get('from')
                    incoming_text = message['text'].get('body', '').strip()
                    
                    logger.info(f"New message from {sender_id[-4:]}: {incoming_text[:50]}...")

                    try:
                        ai_response = await get_ollama_response(incoming_text)
                        
                        if len(ai_response) > 4000:
                            logger.warning(f"AI response too long, truncating: {ai_response[:50]}...")
                            ai_response = ai_response[:4000] + "..."
                        
                        success = await send_whatsapp_message(sender_id, ai_response)
                        if not success:
                            logger.error(f"Failed to send reply to {sender_id[-4:]}")
                            
                    except Exception as e:
                        logger.error(f"Error processing message: {str(e)[:100]}...")
                        await send_whatsapp_message(sender_id, "Maaf, saya sedang mengalami masalah. Coba lagi nanti.")
                
                elif DEBUG_LOGGING:
                    logger.warning(f"Unsupported message type: {message.get('type')}")
                    
            elif value.get('statuses') and DEBUG_LOGGING:
                for status in value['statuses']:
                    if status.get('status') == 'read':
                        logger.info(f"Message read by user: {status}")

        return {"status": "OK"}

    except Exception as e:
        logger.error(f"Webhook error: {str(e)[:100]}...")
        if DEBUG_LOGGING:
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/")
async def index():
    logger.debug("Accessing root endpoint")
    return {"status": "Chatbot WhatsApp sedang berjalan."}

@app.get("/test")
async def test_webhook():
    """Test endpoint to verify webhook is accessible"""
    logger.debug("Accessing /test endpoint")
    return {
        'status': 'webhook accessible',
        'phone_number_id': PHONE_NUMBER_ID,
        'api_version': META_API_VERSION,
        'ollama_url': OLLAMA_URL,
        'ollama_model': OLLAMA_MODEL,
        'debug_logging': DEBUG_LOGGING,
        'verify_token_set': bool(VERIFY_TOKEN),
        'access_token_set': bool(ACCESS_TOKEN),
        'port': PORT
    }

@app.get("/test-ollama")
async def test_ollama():
    """Test endpoint to check Ollama connection"""
    logger.debug("Accessing /test-ollama endpoint")
    try:
        test_message = "Halo, siapa kamu?"
        response = await get_ollama_response(test_message)
        logger.info(f"Ollama test successful: {response[:50]}...")
        return {
            'status': 'success',
            'ollama_url': OLLAMA_URL,
            'model': OLLAMA_MODEL,
            'test_message': test_message,
            'ollama_response': response
        }
    except Exception as e:
        logger.error(f"Ollama test failed: {str(e)}")
        return {
            'status': 'error',
            'ollama_url': OLLAMA_URL,
            'model': OLLAMA_MODEL,
            'error': str(e)
        }

@app.post("/test-webhook")
async def test_webhook_post(request: Request):
    """Test endpoint to simulate WhatsApp webhook POST request"""
    try:
        data = await request.json()
        logger.debug(f"Test webhook POST received: {json.dumps(data, indent=2, ensure_ascii=False)}")
        return {"status": "OK", "received_data": data}
    except Exception as e:
        logger.error(f"Test webhook error: {str(e)}")
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting WhatsApp Chatbot with Ollama...")
    logger.info(f"Model: {OLLAMA_MODEL}")
    logger.info(f"Debug logging: {DEBUG_LOGGING}")
    logger.info(f"Server will run on port: {PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)