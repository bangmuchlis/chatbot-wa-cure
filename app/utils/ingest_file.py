import os
import datetime
import asyncio
import tempfile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, PDFDocument 
from app.services.whatsapp import WhatsAppClient
from app.config import settings

engine = create_engine(settings.DATABASE_URL, echo=True, future=True)
SessionLocal = sessionmaker(bind=engine)

def get_mime_type(filename: str) -> str:
    ext = filename.lower().split(".")[-1]
    mime_types = {
        "pdf": "application/pdf",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xls": "application/vnd.ms-excel",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "doc": "application/msword",
    }
    return mime_types.get(ext, "application/octet-stream")


async def ingest_files(folder: str = "data/files"):
    wa_client = WhatsAppClient(
        access_token=settings.ACCESS_TOKEN,
        phone_number_id=settings.PHONE_NUMBER_ID,
        meta_api_version=settings.META_API_VERSION,
        debug_logging=True
    )

    session = SessionLocal()
    try:
        files = [
            f for f in os.listdir(folder)
            if f.lower().endswith((".pdf", ".xlsx", ".xls", ".docx", ".doc"))
        ]
        if not files:
            print("📁 Tidak ada file yang didukung ditemukan di folder.")
            return

        for fname in files:
            print(f"\n📄 Memproses: {fname}")
            path = os.path.join(folder, fname)

            with open(path, "rb") as f:
                file_data = f.read()

            title = os.path.splitext(fname)[0]
            existing = session.query(PDFDocument).filter(PDFDocument.title == title).first()
            if existing:
                print(f"⚠️ Dokumen '{fname}' sudah ada. Lewati.")
                continue

            mime_type = get_mime_type(fname)
            print(f"📤 Upload ke WhatsApp dengan MIME type: {mime_type}...")

            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(file_data)
                tmp_path = tmp.name

            media_id = await wa_client.upload_media(tmp_path, mime_type=mime_type)
            os.unlink(tmp_path)

            if not media_id:
                print(f"❌ Gagal upload {fname}. Lewati.")
                continue

            ext = fname.lower().split(".")[-1]

            pdf_doc = PDFDocument(
                title=title,
                description=f"Document: {fname}",
                file_data=file_data,
                media_id=media_id,
                file_extension=ext,
                uploaded_at=datetime.datetime.utcnow(),
                updated_at=datetime.datetime.utcnow(),
            )
            session.add(pdf_doc)
            print(f"✅ Berhasil: {fname} → media_id: {media_id}")

        session.commit()
        print("\n🎉 Semua file berhasil diingest + diupload ke WhatsApp!")
    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    asyncio.run(ingest_files())