import json
import logging
import re
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from app.core.config import settings
from app.handlers.message_handler import process_message_background

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/webhook")
async def webhook_verify(request: Request):
    """Verifying Meta webhook."""
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
    """Receives messages, checks for duplicates, then processes in the background."""
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
                            logger.info(
                                f"📩 New message from {sender_id[-4:]} "
                                f"(id: {message_id[-10:]}...): {incoming_text[:50]}..."
                            )

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

        return {"status": "OK"}
    except Exception as e:
        logger.error(f"Error in main webhook endpoint: {str(e)}")
        return {"status": "error", "detail": str(e)}


