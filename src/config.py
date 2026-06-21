import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_DIR = os.path.join(BASE_DIR, "db")

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Retrieval Configuration
RETRIEVAL_K = 5
SIMILARITY_THRESHOLD = 0.7 # Relaxed threshold to let the LLM decide if the retrieved context is relevant

EMBEDDING_MODEL = "models/gemini-embedding-2"
LLM_MODEL = "models/gemini-2.5-flash"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(DB_DIR, exist_ok=True)
