import tempfile
import re
import os
import logging
from sqlalchemy.orm import Session
from app.entities.image import ImageDocument
from app.services.whatsapp_service import WhatsAppClient
from app.core.database import SessionLocal
from sqlalchemy import func

logger = logging.getLogger(__name__)

def clean_image_query(query: str) -> str:
    common_words = r"\b(kirimkan|gambar|image|foto|tolong|cari|kirim)\b"
    cleaned = re.sub(common_words, "", query, flags=re.IGNORECASE)
    cleaned = " ".join(cleaned.split())
    return cleaned.strip().lower()


def find_image_by_title_or_desc(query: str) -> ImageDocument | None:
    session: Session = SessionLocal()
    try:
        clean_query_str = clean_image_query(query)
        if not clean_query_str:
            logger.warning("Image query is empty after cleaning.")
            return None

        logger.info(f"🔍 Searching for image with original query: '{query}' → cleaned: '{clean_query_str}'")
        normalized_query = clean_query_str.replace("_", " ").replace("-", " ")

        image = (
            session.query(ImageDocument)
            .filter(
                (
                    func.replace(func.replace(func.lower(ImageDocument.title), "_", " "), "-", " ").ilike(f"%{normalized_query}%")
                ) |
                (
                    func.replace(func.replace(func.lower(ImageDocument.description), "_", " "), "-", " ").ilike(f"%{normalized_query}%")
                )
            )
            .first()
        )

        if image:
            logger.info(f"✅ Image found: {image.title}")
        else:
            logger.info("❌ No matching image found.")

        return image
    finally:
        session.close()


async def handle_list_images(client: WhatsAppClient, recipient_id: str):
    session: Session = SessionLocal()
    try:
        images = session.query(ImageDocument.title).limit(10).all()
        if not images:
            await client.send_message(recipient_id, "Maaf, belum ada gambar yang tersedia.")
        else:
            titles = "\n".join([f"🖼️ {img[0]}" for img in images])
            await client.send_message(recipient_id, f"📋 *Berikut daftar gambar yang tersedia:*\n{titles}")
    finally:
        session.close()


async def handle_user_image_request(whatsapp_client, recipient_id: str, query: str, db: Session):
    try:
        image = find_image_by_title_or_desc(query)

        if not image:
            await whatsapp_client.send_message(recipient_id, "Maaf, gambar tidak ditemukan.")
            logger.info(f"❌ Image for query '{query}' not found in the database.")
            return

        bot_message_before = f"Saya sudah menemukan gambar: *{image.title}*. Mohon tunggu sebentar..."
        await whatsapp_client.send_message(recipient_id, bot_message_before)
        logger.info(f"🤖 Bot message sent before image: {bot_message_before}")

        if image.media_id:
            success = await whatsapp_client.send_image(recipient_id, image.media_id, is_link=False)
            if success:
                logger.info(f"📤 Image '{image.title}' sent using existing media_id.")

                if image.description:
                    await whatsapp_client.send_message(recipient_id, image.description)
                    logger.info(f"📄 Image description '{image.title}' sent: {image.description}")

                bot_message_after = "Gambar sudah terkirim! Apakah ada yang bisa saya bantu lagi?"
                await whatsapp_client.send_message(recipient_id, bot_message_after)
                logger.info(f"🤖 Bot message sent after image: {bot_message_after}")
            else:
                logger.error(f"❌ Failed to send image '{image.title}' using existing media_id.")
            return

        logger.info(f"📤 No media_id for image '{image.title}' — uploading to WhatsApp...")

        suffix = f".{image.file_extension}" if image.file_extension else ".jpg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(image.file_data)
            tmp_file.flush()
            file_path = tmp_file.name

        mime_type = f"image/{image.file_extension}" if image.file_extension else "image/jpeg"
        media_id = await whatsapp_client.upload_media(file_path, mime_type=mime_type)
        os.unlink(file_path) 

        if not media_id:
            await whatsapp_client.send_message(recipient_id, "Gagal mengupload gambar ke WhatsApp.")
            logger.error(f"❌ Failed to get media_id for image '{image.title}'.")
            return

        session: Session = SessionLocal()
        try:
            image_to_update = session.query(ImageDocument).filter(ImageDocument.id == image.id).first()
            if image_to_update:
                image_to_update.media_id = media_id
                session.commit()
                logger.info(f"💾 media_id '{media_id}' successfully saved to database for image '{image.title}'.")
            else:
                logger.error(f"❌ Failed to find image with ID {image.id} to update media_id.")
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Failed to save media_id to database: {e}")
        finally:
            session.close()

        success = await whatsapp_client.send_image(recipient_id, media_id, is_link=False)
        if success:
            logger.info(f"✅ Image '{image.title}' successfully sent.")

            if image.description:
                await whatsapp_client.send_message(recipient_id, image.description)
                logger.info(f"📄 Image description '{image.title}' sent: {image.description}")

            bot_message_after = "Gambar sudah terkirim! Jangan ragu untuk meminta bantuan lagi ya!"
            await whatsapp_client.send_message(recipient_id, bot_message_after)
            logger.info(f"🤖 Bot message sent after image: {bot_message_after}")
        else:
            logger.error(f"❌ Failed to send image '{image.title}' after upload.")

    except Exception as e:
        logger.error(f"❌ Exception in handle_user_image_request: {e}")
        await whatsapp_client.send_message(recipient_id, "Terjadi kesalahan saat memproses permintaan Anda.")
