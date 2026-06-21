import os
from typing import List, Dict, Any
from pypdf import PdfReader
import docx
import chromadb
import google.generativeai as genai
from langchain_text_splitters import RecursiveCharacterTextSplitter
from tqdm import tqdm
from dotenv import load_dotenv

from config import DATA_DIR, DB_DIR, CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDING_MODEL

load_dotenv()
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

def get_collection():
    """Lazily initialize and return the ChromaDB collection."""
    CHROMA_HOST = os.environ.get("CHROMA_HOST")
    CHROMA_API_KEY = os.environ.get("CHROMA_API_KEY")

    try:
        if CHROMA_HOST and CHROMA_API_KEY:
            print("Connecting to Chroma Cloud...")
            import chromadb.config
            clean_key = CHROMA_API_KEY.strip(' "\'\n\r')
            
            chroma_client = chromadb.HttpClient(
                host=CHROMA_HOST.strip(' "\'\n\r/'),
                headers={"x-chroma-token": clean_key}
            )
        else:
            print("Connecting to Local ChromaDB...")
            chroma_client = chromadb.PersistentClient(path=DB_DIR)

        return chroma_client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"} # Use cosine similarity
        )
    except Exception as e:
        print(f"Error connecting to ChromaDB: {e}")
        raise e

def load_pdf(file_path: str) -> List[Dict[str, Any]]:
    """Load a PDF and extract text page by page."""
    docs = []
    reader = PdfReader(file_path)
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text and text.strip():
            docs.append({
                "text": text.strip(),
                "source": os.path.basename(file_path),
                "page": i + 1
            })
    return docs

def load_docx(file_path: str) -> List[Dict[str, Any]]:
    """Load a DOCX and extract text. Since there are no pages, we group by paragraphs into sections."""
    docs = []
    doc = docx.Document(file_path)
    current_section_text = []
    section_counter = 1
    
    for para in doc.paragraphs:
        if para.text.strip():
            current_section_text.append(para.text.strip())
        
        if len(current_section_text) >= 10:
            docs.append({
                "text": "\n".join(current_section_text),
                "source": os.path.basename(file_path),
                "section": section_counter
            })
            current_section_text = []
            section_counter += 1
            
    if current_section_text:
        docs.append({
            "text": "\n".join(current_section_text),
            "source": os.path.basename(file_path),
            "section": section_counter
        })
        
    return docs

def load_txt(file_path: str) -> List[Dict[str, Any]]:
    """Load a text file as a single section."""
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    if text.strip():
        return [{
            "text": text.strip(),
            "source": os.path.basename(file_path),
            "section": 1
        }]
    return []

def load_document(file_path: str) -> List[Dict[str, Any]]:
    """Route to correct loader based on extension."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        return load_pdf(file_path)
    elif ext == '.docx':
        return load_docx(file_path)
    elif ext == '.txt':
        return load_txt(file_path)
    else:
        print(f"Unsupported file type: {ext}")
        return []

def chunk_documents(loaded_docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Chunk documents using recursive character splitting."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""]
    )
    
    chunks = []
    for doc in loaded_docs:
        splits = splitter.split_text(doc["text"])
        for split in splits:
            # Carry over metadata
            metadata = {"source": doc["source"]}
            if "page" in doc:
                metadata["page"] = doc["page"]
            if "section" in doc:
                metadata["section"] = doc["section"]
                
            chunks.append({
                "text": split,
                "metadata": metadata
            })
    return chunks

def embed_and_store_chunks(chunks: List[Dict[str, Any]]):
    """Embed chunks using Gemini and store in Chroma in batches."""
    if not chunks:
        return

    collection = get_collection()
    BATCH_SIZE = 25
    for i in tqdm(range(0, len(chunks), BATCH_SIZE), desc="Embedding batches"):
        batch = chunks[i:i + BATCH_SIZE]
        
        texts = [chunk["text"] for chunk in batch]
        metadatas = [chunk["metadata"] for chunk in batch]
        
        import time
        
        # We use source + page/section + index as a unique ID
        ids = []
        for j, chunk in enumerate(batch):
            meta = chunk["metadata"]
            loc = meta.get("page", meta.get("section", 0))
            chunk_id = f"{meta['source']}_loc{loc}_idx{i+j}"
            ids.append(chunk_id)
            
        # Call Gemini embedding API with retry for rate limits
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = genai.embed_content(
                    model=EMBEDDING_MODEL,
                    content=texts,
                    task_type="RETRIEVAL_DOCUMENT",
                    title="Document chunk"
                )
                embeddings = response['embedding']
                break
            except Exception as e:
                if "429" in str(e) or "ResourceExhausted" in str(e):
                    if attempt < max_retries - 1:
                        print(f"Rate limit hit. Waiting 5 seconds before retry {attempt+1}...")
                        time.sleep(5)
                    else:
                        raise e
                else:
                    raise e
        
        collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
        
        time.sleep(2)

def process_file(file_path: str):
    """Process a single file end-to-end."""
    print(f"Processing {file_path}...")
    
    collection = get_collection()
    
    # Prevent duplication by deleting any existing chunks for this file
    filename = os.path.basename(file_path)
    try:
        collection.delete(where={"source": filename})
        print(f"Cleared existing chunks for {filename} from the database.")
    except Exception:
        pass
        
    loaded_docs = load_document(file_path)
    if not loaded_docs:
        return
    print(f"Loaded {len(loaded_docs)} pages/sections.")
    
    chunks = chunk_documents(loaded_docs)
    print(f"Created {len(chunks)} chunks.")
    
    embed_and_store_chunks(chunks)
    print(f"Finished storing chunks for {file_path}.")

def process_all_files_in_data_dir():
    """Process all files currently in the data directory."""
    collection = get_collection()
    for filename in os.listdir(DATA_DIR):
        file_path = os.path.join(DATA_DIR, filename)
        if os.path.isfile(file_path) and not filename.startswith('.'):
            collection.delete(where={"source": filename})
            process_file(file_path)

if __name__ == "__main__":
    process_all_files_in_data_dir()
