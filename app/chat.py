import json
import logging
import traceback
import re
from typing import Set
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from .config import settings
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

router = APIRouter()
logger = logging.getLogger(__name__)

def extract_clean_response(result: dict) -> str | None:
    """Mengekstrak dan membersihkan konten dari pesan terakhir yang dihasilkan agent."""
    if not isinstance(result, dict) or "messages" not in result:
        return None
    messages = result.get("messages", [])
    if not messages or not isinstance(messages, list):
        return None
    last_message = messages[-1]
    content = getattr(last_message, 'content', None)
    if not content or not isinstance(content, str):
        return None

    clean_content = re.sub(r'\[{.*}\]', '', content).strip()
    clean_content = re.sub(r'\[.*?\]', '', clean_content).strip()
    return clean_content if clean_content else None

async def process_message_background(agent, whatsapp_client, chat_histories, system_instruction, sender_id, incoming_text, processing_ids: Set[str], message_id: str):
    """Fungsi ini akan berjalan di latar belakang dan menghapus ID pesan setelah selesai."""
    try:
        logger.info(f"Background task started for ...{sender_id[-4:]}")
        user_history = chat_histories.get(sender_id, [])
        
        full_conversation = [SystemMessage(content=system_instruction)]
        full_conversation.extend(user_history)
        full_conversation.append(HumanMessage(content=incoming_text))
        
        input_data = {"messages": full_conversation}
        
        result = await agent.ainvoke(input_data)
        ai_response = extract_clean_response(result)
        
        if not ai_response:
            ai_response = "Maaf, saya tidak memiliki informasi mengenai hal tersebut."
            logger.warning(f"Agent returned an empty or invalid response for ...{sender_id[-4:]}. Full result: {result}")

        user_history.extend([
            HumanMessage(content=incoming_text),
            AIMessage(content=ai_response)
        ])
        chat_histories[sender_id] = user_history

        if len(ai_response) > 4000:
            ai_response = ai_response[:4000] + "..."

        logger.info(f"🚀 Attempting to send reply to {sender_id[-4:]}: {ai_response}...")
        await whatsapp_client.send_message(sender_id, ai_response)

    except Exception as e:
        logger.error(f"Error in background task for message_id {message_id}: {str(e)}")
        if settings.DEBUG_LOGGING:
            logger.debug(f"Full traceback in background task: {traceback.format_exc()}")
        await whatsapp_client.send_message(
            sender_id, "Maaf, saya sedang mengalami masalah. Silakan coba lagi nanti."
        )
    finally:
        processing_ids.discard(message_id)
        logger.info(f"Finished processing for message_id: {message_id}")

@router.get("/webhook")
async def webhook_verify(request: Request):
    """Memverifikasi webhook Meta."""
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
async def webhook_process(request: Request, background_tasks: BackgroundTasks):
    """Menerima pesan, memeriksa duplikat, lalu memproses di latar belakang."""
    try:
        data = await request.json()
        if settings.DEBUG_LOGGING:
            logger.debug(f"Webhook received: {json.dumps(data, indent=2, ensure_ascii=False)}")

        if data.get('object') == 'whatsapp_business_account':
            entry = data.get('entry', [])
            if entry and entry[0].get('changes'):
                value = entry[0]['changes'][0].get('value', {})
                messages = value.get('messages', [])
                if messages:
                    message = messages[0]
                    message_id = message.get('id')
                    processing_ids = request.app.state.processing_message_ids

                    # Logika anti-duplikat
                    if not message_id or message_id in processing_ids:
                        logger.warning(f"Ignoring duplicate or invalid message_id: {message_id}")
                        return {"status": "OK"}
                    
                    processing_ids.add(message_id)

                    if message.get('type') == 'text':
                        sender_id = message.get('from', '').strip()
                        sender_id_digits = re.sub(r'\D', '', sender_id)
                        allowed_contact = "6285730784528"

                        if sender_id_digits == allowed_contact:
                            incoming_text = message['text'].get('body', '').strip()
                            logger.info(f"📩 New message from {sender_id[-4:]} (id: {message_id[-10:]}...): {incoming_text[:50]}...")

                            # --- PERUBAHAN UTAMA: Mengambil dan meneruskan system_instruction ---
                            agent = request.app.state.agent
                            whatsapp_client = request.app.state.whatsapp_client
                            chat_histories = request.app.state.chat_histories
                            system_instruction = request.app.state.system_instruction
                            
                            background_tasks.add_task(
                                process_message_background,
                                agent, whatsapp_client, chat_histories,
                                system_instruction, sender_id, incoming_text,
                                processing_ids, message_id
                            )
                            # --- AKHIR PERUBAHAN ---
        
        return {"status": "OK"}
    except Exception as e:
        logger.error(f"Error in main webhook endpoint: {str(e)}")
        return {"status": "error", "detail": str(e)}

@router.get("/")
async def index():
    """Endpoint status untuk memeriksa apakah bot berjalan."""
    return {"status": "✅ Chatbot WhatsApp sedang berjalan."}

