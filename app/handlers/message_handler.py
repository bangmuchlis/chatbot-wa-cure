import logging
import traceback
import time
from typing import Set
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
# from app.utils.ingest_image import search_image
from app.handlers.file_handler import handle_user_pdf_request, handle_list_documents
from app.core.config import settings
from app.handlers.image_handler import handle_user_image_request, handle_list_images
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)

def extract_clean_response(result: dict) -> str | None:
    """Extract AI response, removing <think> blocks and unnecessary text."""
    if not isinstance(result, dict) or "messages" not in result:
        return None

    messages = result.get("messages", [])
    if not messages or not isinstance(messages, list):
        return None

    last_message = messages[-1]
    content = getattr(last_message, 'content', None)
    if not content or not isinstance(content, str):
        return None

    logger.info(f"Raw agent response: {content}")

    if "</think>" in content:
        parts = content.split("</think>", 1)
        clean_content = parts[1].strip() if len(parts) > 1 else ""
    else:
        clean_content = content.strip()

    return clean_content if clean_content else None


async def process_message_background(
    agent,
    whatsapp_client,
    chat_histories,
    system_instruction,
    sender_id,
    incoming_text,
    processing_ids: Set[str],
    message_id: str
):
    """Process incoming WhatsApp messages in the background."""
    start_time = time.perf_counter()
    try:
        logger.info(f"[{message_id}] 🚀 Background task started for sender ...{sender_id[-4:]}")

        # Handle image search from vectordb
        # if "gambar" in incoming_text.lower():
        #     image_url = search_image(incoming_text, n_results=1)
        #     if image_url:
        #         await whatsapp_client.send_image(sender_id, image_url, is_link=True)
        #         logger.info(f"[{message_id}] 🖼 Sent image for query: {incoming_text}")
        #         return
        #     else:
        #         await whatsapp_client.send_message(sender_id, "Sorry, no image found.")
        #         return

        # Handle listing images
        if any(kw in incoming_text.lower() for kw in ["daftar gambar", "list gambar", "gambar tersedia", "lihat gambar"]):
            await handle_list_images(whatsapp_client, sender_id)
            logger.info(f"[{message_id}] 🖼 Sent image list")
            return

        # Handle image search from SQL DB
        if any(kw in incoming_text.lower() for kw in ["gambar", "image", "foto"]):
            db = SessionLocal()
            try:
                await handle_user_image_request(whatsapp_client, sender_id, incoming_text, db)
                logger.info(f"[{message_id}] 🖼 Sent image for query: {incoming_text}")
            except Exception as e:
                logger.error(f"[{message_id}] ❌ Error handling image request: {e}")
                db.rollback()
                await whatsapp_client.send_message(sender_id, "⚠️ Terjadi kesalahan saat mengambil gambar.")
            finally:
                db.close()
            return
        
        # Handle listing documents
        if any(kw in incoming_text.lower() for kw in ["daftar dokumen", "list dokumen", "dokumen tersedia"]):
            await handle_list_documents(whatsapp_client, sender_id)
            logger.info(f"[{message_id}] 📋 Sent document list")
            return
        
        # Handle sending PDF/documents
        if any(kw in incoming_text.lower() for kw in ["pdf", "dokumen", "file", "unduh", "download"]):
            await handle_user_pdf_request(whatsapp_client, sender_id, incoming_text)
            logger.info(f"[{message_id}] 📄 Sent PDF for query: {incoming_text}")
            return

        # Forward query to AI agent
        user_history = chat_histories.get(sender_id, [])
        full_conversation = [SystemMessage(content=system_instruction)]
        full_conversation.extend(user_history)
        full_conversation.append(HumanMessage(content=incoming_text))

        input_data = {"messages": full_conversation}
        result = await agent.ainvoke(input_data)

        raw_response = extract_clean_response(result)
        ai_response = raw_response if raw_response else "Sorry, the system could not process your request."

        # Update chat history
        user_history.extend([
            HumanMessage(content=incoming_text),
            AIMessage(content=ai_response)
        ])
        chat_histories[sender_id] = user_history

        # Limit long messages
        if len(ai_response) > 4000:
            ai_response = ai_response[:4000] + "..."

        await whatsapp_client.send_message(sender_id, ai_response)

    except Exception as e:
        logger.error(f"[{message_id}] ❌ Error in background task: {str(e)}")
        if settings.DEBUG_LOGGING:
            logger.debug(f"[{message_id}] Full traceback: {traceback.format_exc()}")
        await whatsapp_client.send_message(
            sender_id, "Sorry, the system is experiencing issues. Please try again later."
        )
    finally:
        elapsed = time.perf_counter() - start_time
        logger.info(f"[{message_id}] ⏱ Response time: {elapsed:.2f} seconds")
        processing_ids.discard(message_id)
