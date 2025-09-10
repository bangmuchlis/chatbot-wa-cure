import os
import chromadb
from chromadb.utils.embedding_functions import OpenCLIPEmbeddingFunction
from PIL import Image

CHROMA_DIR = "chroma_db"
COLLECTION_NAME = "images"

chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
embedding_fn = OpenCLIPEmbeddingFunction()
collection = chroma_client.get_or_create_collection(
    name=COLLECTION_NAME,
    embedding_function=embedding_fn
)

def slugify_filename(filename: str) -> str:
    """Ubah nama file jadi ID unik yang stabil (slug)."""
    name, _ = os.path.splitext(filename)
    return name.lower().replace(" ", "-").replace("_", "-")

def ingest_images(image_folder: str = "data/images"):
    if not os.path.exists(image_folder):
        print(f"❌ Folder {image_folder} tidak ditemukan.")
        return
    
    images = [f for f in os.listdir(image_folder) if f.lower().endswith((".png", ".jpg", ".jpeg"))]
    if not images:
        print("❌ Tidak ada gambar ditemukan untuk di-ingest.")
        return
    
    print("🖼 Starting image ingestion...")

    for img_file in images:
        img_path = os.path.join(image_folder, img_file)

        try:
            Image.open(img_path).verify()
        except Exception as e:
            print(f"⚠️ Gagal membaca {img_file}: {e}")
            continue

        label = os.path.splitext(img_file)[0].replace("_", " ").replace("-", " ")
        doc_id = slugify_filename(img_file)

        # Cek apakah ID sudah ada
        existing = collection.get(ids=[doc_id])
        if existing and existing["ids"]:
            print(f"ℹ️ Skip (sudah ada): {label}")
            continue

        collection.add(
            ids=[doc_id],
            documents=[label],
            metadatas=[{"label": label, "path": img_path}]
        )

        print(f"✅ Added image: {label}")

    print(f"🎉 Selesai ingest {len(images)} gambar ke koleksi '{COLLECTION_NAME}'.")

BASE_URL = "https://selected-full-guppy.ngrok-free.app/static"

def calculate_match_score(query: str, label: str) -> float:
    """
    Hitung skor kecocokan antara query dan label.
    Skor lebih tinggi untuk exact match dan word match.
    """
    query_lower = query.lower().strip()
    label_lower = label.lower().strip()
    
    # Exact match mendapat skor tertinggi
    if query_lower == label_lower:
        return 1.0
    
    # Split menjadi kata-kata
    query_words = set(query_lower.split())
    label_words = set(label_lower.split())
    
    # Hitung persentase kata yang cocok
    if not query_words:
        return 0.0
    
    matching_words = query_words.intersection(label_words)
    word_match_score = len(matching_words) / len(query_words)
    
    # Bonus jika semua kata query ada di label
    if query_words.issubset(label_words):
        word_match_score += 0.2
    
    # Penalti jika query adalah substring kecil dari label yang panjang
    if query_lower in label_lower and len(query_lower) < len(label_lower) * 0.3:
        word_match_score *= 0.5
    
    return word_match_score

def search_image(query: str, n_results: int = 3):
    """
    Cari gambar dengan prioritas:
    1. Exact match atau high-score word match
    2. Embedding search dengan threshold ketat sebagai fallback
    """
    # Ambil semua item untuk pencarian manual
    all_items = collection.get(include=["metadatas"])
    
    # Hitung skor untuk setiap item
    candidates = []
    for i, meta in enumerate(all_items["metadatas"]):
        label = meta["label"]
        score = calculate_match_score(query, label)
        if score > 0:
            candidates.append((score, meta, i))
    
    # Urutkan berdasarkan skor (tertinggi dulu)
    candidates.sort(key=lambda x: x[0], reverse=True)
    
    # Jika ada match dengan skor tinggi (>= 0.7), gunakan yang terbaik
    if candidates and candidates[0][0] >= 0.7:
        best_meta = candidates[0][1]
        filename = os.path.basename(best_meta["path"])
        print(f"🎯 Found high-score match: '{best_meta['label']}' (score: {candidates[0][0]:.2f})")
        return f"{BASE_URL}/{filename}"
    
    # Jika ada match dengan skor sedang (>= 0.5), gunakan yang terbaik
    elif candidates and candidates[0][0] >= 0.5:
        best_meta = candidates[0][1]
        filename = os.path.basename(best_meta["path"])
        print(f"📍 Found medium-score match: '{best_meta['label']}' (score: {candidates[0][0]:.2f})")
        return f"{BASE_URL}/{filename}"
    
    # Fallback ke embedding search dengan threshold yang sangat ketat
    print(f"🔍 Using embedding search for: '{query}'")
    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        include=["metadatas", "distances"]
    )
    
    if results and results.get("metadatas") and results["metadatas"][0]:
        # Ambil distance/similarity score dari embedding
        distances = results.get("distances", [[]])[0]
        meta = results["metadatas"][0][0]
        
        if distances:
            # ChromaDB menggunakan distance (semakin kecil = semakin mirip)
            distance = distances[0]
            similarity = 1 - distance  # Convert ke similarity score
            
            print(f"🤖 Embedding distance: {distance:.3f}, similarity: {similarity:.3f}")
            
            # Tambahan validasi semantik: cek apakah ada kata kunci yang bertentangan
            query_lower = query.lower()
            label_lower = meta["label"].lower()
            
            # Daftar warna yang umum - jika query menyebutkan warna yang berbeda, reject
            colors = ["merah", "kuning", "biru", "hijau", "putih", "hitam", "orange", "ungu", "pink"]
            query_colors = [color for color in colors if color in query_lower]
            label_colors = [color for color in colors if color in label_lower]
            
            # Jika ada warna spesifik di query tapi tidak match dengan label, reject
            if query_colors and label_colors and not set(query_colors).intersection(set(label_colors)):
                print(f"❌ Color mismatch: query has {query_colors}, label has {label_colors}")
                print(f"❌ Embedding result rejected: semantic mismatch")
                return None
            
            # Threshold yang lebih ketat: hanya terima jika very similar
            if distance < 0.3 and similarity > 0.7:  # Threshold jauh lebih ketat
                filename = os.path.basename(meta["path"])
                print(f"✅ Embedding search result accepted: '{meta['label']}'")
                return f"{BASE_URL}/{filename}"
            else:
                print(f"❌ Embedding result rejected: similarity too low ({similarity:.3f}) or distance too high ({distance:.3f})")
        else:
            print(f"⚠️ No distance scores available from embedding search")
    
    print(f"❌ No suitable match found for: '{query}'")
    return None

if __name__ == "__main__":
    ingest_images()