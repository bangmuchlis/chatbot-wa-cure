import os
import requests
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import json

load_dotenv()

app = FastAPI()

ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
PHONE_NUMBER_ID = os.getenv('PHONE_NUMBER_ID')
VERIFY_TOKEN = os.getenv('VERIFY_TOKEN')
META_API_VERSION = os.getenv('META_API_VERSION')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL')
OLLAMA_URL = os.getenv('OLLAMA_URL')
META_API_URL = f"https://graph.facebook.com/{META_API_VERSION}/{PHONE_NUMBER_ID}/messages"
DEBUG_LOGGING = os.getenv('DEBUG_LOGGING', 'False').lower() == 'true'

async def get_ollama_response(user_message: str) -> str:
    """
    Mengirim pesan ke Ollama Mistral dan mendapatkan response.
    """
    try:
        if DEBUG_LOGGING:
            print(f"🤖 User: {user_message}")
        
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
                print(f"🤖 AI: {ollama_reply}")
            return ollama_reply
        else:
            print(f"❌ Ollama error: {response.status_code}")
            return "Maaf, saya sedang mengalami masalah teknis. Coba lagi nanti ya! 😅"
            
    except requests.exceptions.Timeout:
        print("⏰ Ollama timeout")
        return "Maaf, respons terlalu lama. Coba dengan pertanyaan yang lebih singkat ya! ⏰"
    except requests.exceptions.ConnectionError:
        print("🔌 Cannot connect to Ollama")
        return "Maaf, saya sedang offline. Pastikan sistem sedang berjalan. 🔧"
    except Exception as e:
        print(f"⚠️ Ollama error: {e}")
        return "Maaf, terjadi kesalahan sistem. Coba lagi nanti ya! 🙏"

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
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        print(f"✅ Message sent to {recipient_id[-4:]}")
        if DEBUG_LOGGING:
            print(f"📤 Response: {response.status_code}")
        
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to send message: {str(e)[:100]}...")
        if DEBUG_LOGGING and hasattr(e, 'response') and e.response is not None:
            print(f"📄 Response body: {e.response.text}")
        return False

@app.get("/webhook")
async def webhook_verify(request: Request):
    mode = request.query_params.get('hub.mode')
    token = request.query_params.get('hub.verify_token')
    challenge = request.query_params.get('hub.challenge')

    if mode and token:
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            print('✅ Webhook verified')
            return int(challenge)
        else:
            print('❌ Webhook verification failed')
            raise HTTPException(status_code=403, detail="Forbidden: Webhook verification failed")
    
    print('⚠️ Bad request: Missing parameters')
    raise HTTPException(status_code=400, detail="Bad Request: Missing parameters")

@app.post("/webhook")
async def webhook_process(request: Request):
    try:
        data = await request.json()
        if not data:
            return {"status": "OK"}

        if DEBUG_LOGGING:
            print("📨 Webhook received:", json.dumps(data, indent=2, ensure_ascii=False))

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
                    
                    print(f"💬 New message from {sender_id[-4:]}: {incoming_text[:50]}...")

                    try:
                        ai_response = await get_ollama_response(incoming_text)
                        
                        if len(ai_response) > 4000:
                            ai_response = ai_response[:4000] + "..."
                        
                        success = await send_whatsapp_message(sender_id, ai_response)
                        if not success:
                            print(f"❌ Failed to send reply to {sender_id[-4:]}")
                            
                    except Exception as e:
                        print(f"⚠️ Error processing message: {str(e)[:100]}...")
                        await send_whatsapp_message(sender_id, "Maaf, saya sedang mengalami masalah. Coba lagi nanti.")
                
                elif DEBUG_LOGGING:
                    print(f"⚠️ Unsupported message type: {message.get('type')}")
                    
            elif value.get('statuses') and DEBUG_LOGGING:
                for status in value['statuses']:
                    if status.get('status') == 'read':
                        print(f"👁️ Message read by user")

        return {"status": "OK"}

    except Exception as e:
        print(f"⚠️ Webhook error: {str(e)[:100]}...")
        if DEBUG_LOGGING:
            import traceback
            print(f"🔍 Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/")
async def index():
    return {"status": "✅ Chatbot WhatsApp sedang berjalan."}

@app.get("/test")
async def test_webhook():
    """Test endpoint to verify webhook is accessible"""
    return {
        'status': 'webhook accessible',
        'phone_number_id': PHONE_NUMBER_ID,
        'api_version': META_API_VERSION,
        'ollama_url': OLLAMA_URL,
        'ollama_model': OLLAMA_MODEL,
        'debug_logging': DEBUG_LOGGING,
        'verify_token_set': bool(VERIFY_TOKEN),
        'access_token_set': bool(ACCESS_TOKEN)
    }

@app.get("/test-ollama")
async def test_ollama():
    """Test endpoint to check Ollama connection"""
    try:
        test_message = "Halo, siapa kamu?"
        response = await get_ollama_response(test_message)
        return {
            'status': 'success',
            'ollama_url': OLLAMA_URL,
            'model': OLLAMA_MODEL,
            'test_message': test_message,
            'ollama_response': response
        }
    except Exception as e:
        return {
            'status': 'error',
            'ollama_url': OLLAMA_URL,
            'model': OLLAMA_MODEL,
            'error': str(e)
        }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting WhatsApp Chatbot with Ollama...")
    print(f"🤖 Model: {OLLAMA_MODEL}")
    print(f"🔧 Debug logging: {DEBUG_LOGGING}")
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv('PORT', 5000)))