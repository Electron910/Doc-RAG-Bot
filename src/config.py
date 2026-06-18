import os

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_DIR = os.path.join(BASE_DIR, "db")

# Chunking Configuration
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Retrieval Configuration
RETRIEVAL_K = 3
SIMILARITY_THRESHOLD = 0.3 # Minimum similarity score to consider a chunk relevant (distance threshold, lower distance = higher similarity depending on metric, chroma uses distance by default)

# Model Configuration
EMBEDDING_MODEL = "models/gemini-embedding-2"
LLM_MODEL = "models/gemini-2.5-flash"

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(DB_DIR, exist_ok=True)
