import tempfile
import os
import re
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.entities.document import PDFDocument
from app.core.database import SessionLocal
from app.services.whatsapp_service import WhatsAppClient

logger = logging.getLogger(__name__)

def clean_query(query: str) -> str:
    common_words = r"\b(kirimkan|file|tolong|cari|dokumen|pdf|unduh|download|kirim)\b"
    cleaned = re.sub(common_words, "", query, flags=re.IGNORECASE)
    cleaned = " ".join(cleaned.split())
    return cleaned.strip().lower()


def find_pdf_by_title_or_desc(query: str) -> PDFDocument | None:
    session: Session = SessionLocal()
    try:
        clean_query_str = clean_query(query)
        if not clean_query_str:
            logger.warning("Query is empty after cleaning.")
            return None

        logger.info(f"🔍 Searching for document with original query: '{query}' → cleaned: '{clean_query_str}'")
        normalized_query = clean_query_str.replace("_", " ")

        pdf = (
            session.query(PDFDocument)
            .filter(
                (func.replace(func.lower(PDFDocument.title), "_", " ").ilike(f"%{normalized_query}%")) |
                (func.replace(func.lower(PDFDocument.description), "_", " ").ilike(f"%{normalized_query}%"))
            )
            .first()
        )

        if pdf:
            logger.info(f"✅ Found document: {pdf.title}")
        else:
            logger.info("❌ No matching document found.")

        return pdf
    finally:
        session.close()


async def handle_list_documents(client: WhatsAppClient, recipient_id: str):
    session: Session = SessionLocal()
    try:
        docs = session.query(PDFDocument.title).limit(10).all()
        if not docs:
            await client.send_message(recipient_id, "Maaf, belum ada dokumen yang tersedia.")
        else:
            titles = "\n".join([f"📄 {d[0]}" for d in docs])
            await client.send_message(recipient_id, f"📋 *Berikut daftar dokumen yang tersedia:*\n{titles}")
    finally:
        session.close()


async def handle_user_pdf_request(client: WhatsAppClient, recipient_id: str, query: str):
    pdf_doc = find_pdf_by_title_or_desc(query)
    if not pdf_doc:
        await client.send_message(recipient_id, "Maaf, dokumen tidak ditemukan.")
        logger.info(f"❌ Document for query '{query}' not found in database.")
        return

    bot_message_before = f"Saya sudah menemukan dokumen '{pdf_doc.title}'. Mohon tunggu sebentar..."
    await client.send_message(recipient_id, bot_message_before)
    logger.info(f"🤖 Bot message sent before document: {bot_message_before}")

    if pdf_doc.media_id:
        logger.info(f"🚀 Sending directly via stored media_id: {pdf_doc.media_id}")

        ext = pdf_doc.file_extension or "pdf"
        filename = f"{pdf_doc.title}.{ext}"

        success = await client.send_document(
            recipient_id,
            media=pdf_doc.media_id,
            filename=filename,
            is_link=False
        )

        if success:
            logger.info(f"✅ Document '{pdf_doc.title}' sent using existing media_id.")
            if pdf_doc.description:
                await client.send_message(recipient_id, pdf_doc.description)
                logger.info(f"📄 Sent document description: {pdf_doc.description}")

            bot_message_after = "Dokumen sudah terkirim! Apakah ada yang bisa saya bantu lagi?"
            await client.send_message(recipient_id, bot_message_after)
            logger.info(f"🤖 Bot message sent after document: {bot_message_after}")
        else:
            await client.send_message(recipient_id, "Gagal mengirim dokumen ke WhatsApp.")
            logger.error(f"❌ Failed to send document '{pdf_doc.title}' via media_id.")
        return

    logger.info("📤 No media_id yet — uploading document to WhatsApp...")
    ext = pdf_doc.file_extension or "pdf"
    suffix = f".{ext}"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(pdf_doc.file_data)
        tmp_path = tmp.name

    mime_type_map = {
        "pdf": "application/pdf",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xls": "application/vnd.ms-excel",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "doc": "application/msword",
    }
    mime_type = mime_type_map.get(ext, "application/octet-stream")

    media_id = await client.upload_media(tmp_path, mime_type=mime_type)
    os.unlink(tmp_path)

    if not media_id:
        await client.send_message(recipient_id, "Gagal mengupload dokumen ke WhatsApp.")
        logger.error(f"❌ Failed to upload document '{pdf_doc.title}' to WhatsApp.")
        return

    session: Session = SessionLocal()
    try:
        doc_to_update = session.query(PDFDocument).filter(PDFDocument.id == pdf_doc.id).first()
        if doc_to_update:
            doc_to_update.media_id = media_id
            session.commit()
            logger.info(f"💾 media_id saved to database: {media_id}")
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Failed to save media_id: {e}")
    finally:
        session.close()

    filename = f"{pdf_doc.title}.{ext}"
    success = await client.send_document(
        recipient_id,
        media=media_id,
        filename=filename,
        is_link=False
    )
    if success:
        logger.info(f"✅ Document '{pdf_doc.title}' sent successfully.")
        if pdf_doc.description:
            await client.send_message(recipient_id, pdf_doc.description)
            logger.info(f"📄 Sent document description: {pdf_doc.description}")

        bot_message_after = "Dokumen sudah terkirim! Jangan ragu untuk meminta bantuan lagi ya!"
        await client.send_message(recipient_id, bot_message_after)
        logger.info(f"🤖 Bot message sent after document: {bot_message_after}")
    else:
        logger.error(f"❌ Failed to send document '{pdf_doc.title}' after upload.")
        await client.send_message(recipient_id, "Terjadi kesalahan saat memproses permintaan Anda.")
