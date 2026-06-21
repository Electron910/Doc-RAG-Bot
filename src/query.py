import os
from typing import Dict, Any, List
import chromadb
import google.generativeai as genai
from dotenv import load_dotenv

from config import DB_DIR, RETRIEVAL_K, EMBEDDING_MODEL, LLM_MODEL, SIMILARITY_THRESHOLD

load_dotenv()
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

def get_collection():
    """Lazily initialize and return the ChromaDB collection."""
    CHROMA_HOST = os.environ.get("CHROMA_HOST")
    CHROMA_API_KEY = os.environ.get("CHROMA_API_KEY")

    try:
        if CHROMA_HOST and CHROMA_API_KEY:
            clean_key = CHROMA_API_KEY.strip(' "\'\n\r')
            tenant = os.environ.get("CHROMA_TENANT", "default_tenant").strip(' "\'\n\r')
            database = os.environ.get("CHROMA_DATABASE", "default_database").strip(' "\'\n\r')
            
            chroma_client = chromadb.HttpClient(
                host=CHROMA_HOST.strip(' "\'\n\r/'),
                tenant=tenant,
                database=database,
                headers={"x-chroma-token": clean_key}
            )
        else:
            chroma_client = chromadb.PersistentClient(path=DB_DIR)

        return chroma_client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}
        )
    except Exception as e:
        print(f"Error connecting to ChromaDB: {e}")
        raise e

# Initialize Gemini LLM
# generation_config can be customized as needed
model = genai.GenerativeModel(model_name=LLM_MODEL)

SYSTEM_PROMPT = """You are a strict, highly accurate AI assistant. Your only job is to answer the user's question based EXCLUSIVELY on the provided context documents.

Instructions:
1. You must answer the question using ONLY the information found in the provided context.
2. If the provided context does not contain the answer, or if it is irrelevant to the question, you MUST respond exactly with: "I'm sorry, but I couldn't find the answer to your question in the provided documents."
3. Absolutely DO NOT use your own outside knowledge, training data, or assumptions to answer the question or fill in gaps.
4. If you find the answer in the context, synthesize a clear response and include inline citations using the format [Source: filename, Page/Section: X].
"""

def query_rag_pipeline(question: str) -> Dict[str, Any]:
    """
    Given a question, retrieves context from vector DB, and generates an answer.
    Returns a dictionary containing the answer, citations, and raw context.
    """
    collection = get_collection()
    
    # 1. Embed the query
    # task_type="RETRIEVAL_QUERY" is recommended for the search query
    query_embedding_res = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=question,
        task_type="RETRIEVAL_QUERY"
    )
    query_embedding = query_embedding_res['embedding']
    
    # 2. Retrieve chunks from ChromaDB
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=RETRIEVAL_K
    )
    
    if not results['documents'] or not results['documents'][0]:
        return {
            "answer": "I'm sorry, but I couldn't find any relevant documents to search.",
            "citations": [],
            "raw_context": ""
        }
        
    distances = results['distances'][0]
    documents = results['documents'][0]
    metadatas = results['metadatas'][0]
    
    # Filter by similarity threshold
    # For cosine distance, smaller is better (0 = identical, 1 = orthogonal)
    # distance = 1 - cosine_similarity. So threshold of 0.5 means similarity >= 0.5
    valid_chunks = []
    citations = set()
    
    for i in range(len(distances)):
        if distances[i] <= SIMILARITY_THRESHOLD:
            doc_text = documents[i]
            meta = metadatas[i]
            
            source = meta.get("source", "Unknown")
            loc = f"Page {meta['page']}" if "page" in meta else f"Section {meta.get('section', 'Unknown')}"
            
            citation_tag = f"[Source: {source}, {loc}]"
            citations.add(citation_tag)
            
            valid_chunks.append(f"{citation_tag}\n{doc_text}")
            
    if not valid_chunks:
        return {
            "answer": "I'm sorry, but I couldn't find the answer to your question in the provided documents.",
            "citations": [],
            "raw_context": ""
        }
        
    # 3. Build Context
    context_block = "\n\n---\n\n".join(valid_chunks)
    
    prompt = f"""{SYSTEM_PROMPT}

Context:
{context_block}

Question: {question}

Answer:"""
    
    # 4. Generate Response
    response = model.generate_content(prompt)
    answer = response.text
    
    return {
        "answer": answer,
        "citations": list(citations),
        "raw_context": context_block
    }
