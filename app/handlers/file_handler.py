import tempfile
import re
import os
import logging

from sqlalchemy.orm import Session
from app.models import PDFDocument
from app.database import SessionLocal
from app.services.whatsapp import WhatsAppClient
from sqlalchemy import func

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
            logger.warning("Query kosong setelah dibersihkan.")
            return None

        logger.info(f"🔍 Mencari dokumen dengan query asli: '{query}' → dibersihkan: '{clean_query_str}'")

        normalized_query = clean_query_str.replace("_", " ") 

        pdf = (
            session.query(PDFDocument)
            .filter(
                (
                    func.replace(func.lower(PDFDocument.title), "_", " ").ilike(f"%{normalized_query}%")
                ) |
                (
                    func.replace(func.lower(PDFDocument.description), "_", " ").ilike(f"%{normalized_query}%")
                )
            )
            .first()
        )

        if pdf:
            logger.info(f"✅ Ditemukan dokumen: {pdf.title}")
        else:
            logger.info("❌ Tidak ada dokumen yang cocok ditemukan.")

        return pdf
    finally:
        session.close()


async def handle_list_documents(client: WhatsAppClient, recipient_id: str):
    session: Session = SessionLocal()
    try:
        docs = session.query(PDFDocument.title).limit(10).all()
        if not docs:
            await client.send_message(recipient_id, "📂 Belum ada dokumen tersedia.")
        else:
            titles = "\n".join([f"📄 {d[0]}" for d in docs])
            await client.send_message(recipient_id, f"📋 *Daftar Dokumen Tersedia:*\n{titles}")
    finally:
        session.close()


async def handle_user_pdf_request(client: WhatsAppClient, recipient_id: str, query: str):
    pdf_doc = find_pdf_by_title_or_desc(query)
    if not pdf_doc:
        await client.send_message(recipient_id, "❌ Maaf, dokumen tidak ditemukan.")
        return

    if pdf_doc.media_id:
        logger.info(f"🚀 Langsung kirim via media_id yang sudah tersimpan: {pdf_doc.media_id}")

        ext = pdf_doc.file_extension or "pdf"
        filename = f"{pdf_doc.title}.{ext}"

        success = await client.send_document(
            recipient_id,
            media=pdf_doc.media_id,
            filename=filename, 
            is_link=False
        )
        if not success:
            await client.send_message(recipient_id, "❌ Gagal mengirim dokumen (error WA).")
        return

    logger.info("📤 Belum ada media_id — upload dokumen ke WhatsApp...")

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
    if not media_id:
        await client.send_message(recipient_id, "❌ Gagal upload dokumen ke WhatsApp.")
        os.unlink(tmp_path)
        return
    
    session: Session = SessionLocal()
    try:
        pdf_doc.media_id = media_id
        session.commit()
        logger.info(f"💾 media_id disimpan ke database: {media_id}")
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Gagal simpan media_id: {e}")
    finally:
        session.close()

    os.unlink(tmp_path)

    filename = f"{pdf_doc.title}.{ext}"
    success = await client.send_document(
        recipient_id,
        media=media_id,
        filename=filename,
        is_link=False
    )
    if not success:
        await client.send_message(recipient_id, "❌ Gagal mengirim dokumen setelah upload.")