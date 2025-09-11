import os
import datetime
import asyncio
import tempfile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.entities.image import ImageDocument
from app.services.whatsapp_service import WhatsAppClient
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, echo=True, future=True)
SessionLocal = sessionmaker(bind=engine)

def get_mime_type(filename: str) -> str:
    """Determines MIME type for images based on extension."""
    ext = filename.lower().split(".")[-1]
    mime_types = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp",
    }
    return mime_types.get(ext, "application/octet-stream")

async def ingest_images(folder: str = "data/images"):
    """
    Scans a folder for supported images, uploads them to WhatsApp to get a media_id,
    and saves their information to the database.
    """
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
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp"))
        ]
        if not files:
            print("📁 No supported images found in the folder.")
            return

        for fname in files:
            print(f"\n🖼️ Processing: {fname}")
            path = os.path.join(folder, fname)
            with open(path, "rb") as f:
                file_data = f.read()

            title = os.path.splitext(fname)[0]
            existing = session.query(ImageDocument).filter(ImageDocument.title == title).first()
            if existing:
                print(f"⚠️ Image '{fname}' already exists. Skipping.")
                continue

            mime_type = get_mime_type(fname)
            print(f"📤 Uploading to WhatsApp with MIME type: {mime_type}...")
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(file_data)
                tmp_path = tmp.name

            media_id = await wa_client.upload_media(tmp_path, mime_type=mime_type)
            os.unlink(tmp_path)

            if not media_id:
                print(f"❌ Failed to upload {fname}. Skipping.")
                continue

            ext = fname.lower().split(".")[-1]
            img_doc = ImageDocument(
                title=title,
                description=f"Image: {fname}",
                file_data=file_data,
                media_id=media_id,
                file_extension=ext,
                uploaded_at=datetime.datetime.utcnow(),
                updated_at=datetime.datetime.utcnow(),
            )
            session.add(img_doc)
            print(f"✅ Success: {fname} → media_id: {media_id}")

        session.commit()
        print("\n🎉 All images successfully ingested and uploaded to WhatsApp!")
    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    asyncio.run(ingest_images())






# import os
# import chromadb
# from chromadb.utils.embedding_functions import OpenCLIPEmbeddingFunction
# from PIL import Image

# CHROMA_DIR = "chroma_db"
# COLLECTION_NAME = "images"

# chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
# embedding_fn = OpenCLIPEmbeddingFunction()
# collection = chroma_client.get_or_create_collection(
#     name=COLLECTION_NAME,
#     embedding_function=embedding_fn
# )

# def slugify_filename(filename: str) -> str:
#     name, _ = os.path.splitext(filename)
#     return name.lower().replace(" ", "-").replace("_", "-")

# def ingest_images(image_folder: str = "data/images"):
#     """
#     Scans a folder for images, verifies them, and adds them to a collection 
#     if they do not already exist.
#     """
#     if not os.path.exists(image_folder):
#         print(f"❌ Folder {image_folder} not found.")
#         return
    
#     images = [f for f in os.listdir(image_folder) if f.lower().endswith((".png", ".jpg", ".jpeg"))]
#     if not images:
#         print("❌ No images found to ingest.")
#         return
    
#     print("🖼 Starting image ingestion...")

#     for img_file in images:
#         img_path = os.path.join(image_folder, img_file)

#         try:
#             Image.open(img_path).verify()
#         except Exception as e:
#             print(f"⚠️ Failed to read {img_file}: {e}")
#             continue

#         label = os.path.splitext(img_file)[0].replace("_", " ").replace("-", " ")
#         doc_id = slugify_filename(img_file)

#         existing = collection.get(ids=[doc_id])
#         if existing and existing["ids"]:
#             print(f"ℹ️ Skipping (already exists): {label}")
#             continue

#         collection.add(
#             ids=[doc_id],
#             documents=[label],
#             metadatas=[{"label": label, "path": img_path}]
#         )

#         print(f"✅ Added image: {label}")

#     print(f"🎉 Finished ingesting {len(images)} images into collection '{COLLECTION_NAME}'.")

# BASE_URL = "https://selected-full-guppy.ngrok-free.app/static"

# def calculate_match_score(query: str, label: str) -> float:
#     query_lower = query.lower().strip()
#     label_lower = label.lower().strip()
    
#     if query_lower == label_lower:
#         return 1.0
    
#     query_words = set(query_lower.split())
#     label_words = set(label_lower.split())
    
#     if not query_words:
#         return 0.0
    
#     matching_words = query_words.intersection(label_words)
#     word_match_score = len(matching_words) / len(query_words)
    
#     if query_words.issubset(label_words):
#         word_match_score += 0.2
    
#     if query_lower in label_lower and len(query_lower) < len(label_lower) * 0.3:
#         word_match_score *= 0.5
    
#     return word_match_score

# def search_image(query: str, n_results: int = 3):
#     all_items = collection.get(include=["metadatas"])
    
#     candidates = []
#     for i, meta in enumerate(all_items["metadatas"]):
#         label = meta["label"]
#         score = calculate_match_score(query, label)
#         if score > 0:
#             candidates.append((score, meta, i))
    
#     candidates.sort(key=lambda x: x[0], reverse=True)
    
#     if candidates and candidates[0][0] >= 0.7:
#         best_meta = candidates[0][1]
#         filename = os.path.basename(best_meta["path"])
#         print(f"🎯 Found high-score match: '{best_meta['label']}' (score: {candidates[0][0]:.2f})")
#         return f"{BASE_URL}/{filename}"
    
#     elif candidates and candidates[0][0] >= 0.5:
#         best_meta = candidates[0][1]
#         filename = os.path.basename(best_meta["path"])
#         print(f"📍 Found medium-score match: '{best_meta['label']}' (score: {candidates[0][0]:.2f})")
#         return f"{BASE_URL}/{filename}"

#     print(f"🔍 Using embedding search for: '{query}'")
#     results = collection.query(
#         query_texts=[query],
#         n_results=n_results,
#         include=["metadatas", "distances"]
#     )
    
#     if results and results.get("metadatas") and results["metadatas"][0]:
#         distances = results.get("distances", [[]])[0]
#         meta = results["metadatas"][0][0]
        
#         if distances:
#             distance = distances[0]
#             similarity = 1 - distance 
            
#             print(f"🤖 Embedding distance: {distance:.3f}, similarity: {similarity:.3f}")
            
#             query_lower = query.lower()
#             label_lower = meta["label"].lower()
            
#             colors = ["merah", "kuning", "biru", "hijau", "putih", "hitam", "orange", "ungu", "pink"]
#             query_colors = [color for color in colors if color in query_lower]
#             label_colors = [color for color in colors if color in label_lower]
            
#             if query_colors and label_colors and not set(query_colors).intersection(set(label_colors)):
#                 print(f"❌ Color mismatch: query has {query_colors}, label has {label_colors}")
#                 print(f"❌ Embedding result rejected: semantic mismatch")
#                 return None
            
#             if distance < 0.3 and similarity > 0.7: 
#                 filename = os.path.basename(meta["path"])
#                 print(f"✅ Embedding search result accepted: '{meta['label']}'")
#                 return f"{BASE_URL}/{filename}"
#             else:
#                 print(f"❌ Embedding result rejected: similarity too low ({similarity:.3f}) or distance too high ({distance:.3f})")
#         else:
#             print(f"⚠️ No distance scores available from embedding search")
    
#     print(f"❌ No suitable match found for: '{query}'")
#     return None

# if __name__ == "__main__":
#     ingest_images()