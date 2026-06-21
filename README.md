# RAG Document Q&A Bot

A Streamlit-based web application and CLI that allows you to upload documents (PDF, DOCX, TXT) and ask natural language questions. It retrieves the most relevant information from your documents and uses a Large Language Model (Gemini) to synthesize an answer, providing citations to show exactly where the information came from.

## Tech Stack
- **Language**: Python 3.11+
- **LLM & Embeddings**: Google Gemini (`models/gemini-2.5-flash` & `models/text-embedding-004`) via `google-generativeai>=0.3.0`
- **Vector Database**: ChromaDB (`chromadb>=0.4.22`) for persistent local vector storage
- **Document Loaders**: `pypdf>=4.0.0` (PDFs), `python-docx>=1.1.0` (DOCX)
- **Chunking**: `langchain-text-splitters>=0.2.0`
- **UI Framework**: `streamlit>=1.30.0`

## Architecture Overview

```text
[Documents] -> (Ingestion Pipeline) -> [Chunking] -> [Embeddings (Gemini)] -> [Vector Store (ChromaDB)]
                                                                                     |
                                                                                     v
[User Query] -> (Query Pipeline) -> [Embed Query] -> [Retrieve Top-K Chunks] -> [Context + Prompt]
                                                                                     |
                                                                                     v
[Answer + Citations] <------------------------------------------ [Gemini LLM]
```

## Decisions & Limitations

- **Chunking Strategy**: This project uses a **Recursive Character Text Splitter**. Unlike a naive fixed-size sliding window, the recursive splitter attempts to keep paragraphs and sentences together by splitting on `\n\n`, then `\n`, then spaces. This provides much higher quality context to the LLM.
- **Embedding Model & Vector DB**: ChromaDB is used as the persistent client because it runs locally with zero configuration and persists to disk. We use Google's `text-embedding-2` which is optimized for retrieval tasks.
- **Batched Embeddings**: During ingestion, document chunks are batched into groups of 50 before being sent to the Gemini Embedding API, respecting API limits and improving ingestion speed.
- **Known Limitations**:
  - **Page Boundary Blindness**: Chunks are processed page-by-page (for PDFs), meaning a sentence that spans across a page break may lose its surrounding context.
  - **No Reranking**: It relies entirely on dense cosine similarity retrieval; there is no secondary reranker (like Cohere) or hybrid keyword search (BM25).

## Setup Instructions

1. **Clone the repository** (if not already local).
2. **Set up a virtual environment**:
   ```bash
   python -m venv venv
   # On Windows
   .\venv\Scripts\Activate.ps1
   # On Mac/Linux
   source venv/bin/activate
   ```
3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Configure Environment Variables**:
   Open the `.env` file and add your Gemini API key:
   ```env
   GEMINI_API_KEY=your_actual_api_key_here
   ```

## Running the Application

1. **Start the Streamlit UI**:
   ```bash
   streamlit run src/app.py
   ```
2. **Upload Documents**: Use the sidebar to upload your PDFs, DOCX or TXT files. Click "Ingest Documents".
3. **Ask Questions**: Use the chat input box to ask questions based on the uploaded context.

## Example Queries

If you upload documents on history or science, try asking:

**Q: "What are the main causes mentioned in Roman Empire?"**
> **A:** The Roman Republic, a predecessor to the Roman Empire, became severely destabilized by a series of civil wars and political conflicts, which ultimately led to the rise of Octavian as the first Roman emperor, Augustus [Source: roman_empire.docx, Section 1]....

**Q: "Can you summarize second paragraph in machine learning?"**
> **A:** Machine learning approaches are traditionally categorized into three main types based on the nature of the "signal" or "feedback" available to the learning system: supervised learning, unsupervised learning, and reinforcement learning....

**Q: "Who were the key figures involved in roman empire?"**
> **A:** Octavian / Augustus - He was granted overarching power and the title Augustus in 27 BC, effectively making him the first Roman emperor. His victory over Mark Antony and Cleopatra at the Battle of Actium in 31 BC culminated....

**Q: "How does this technology work according to quantum computing?"**
> **A:** In quantum computing, technology works by utilizing quantum bits, or qubits, as the basic unit of memory. Qubits are created using physical systems, such as the spin of an electron or....

**Q: "What does the author say about quantum computing?"**
> **A:** Quantum computing is a rapidly-emerging technology that uses quantum mechanics to solve problems too complex for classical computers [Source: quantum_computing.pdf, Page 1]. IBM Quantum provides real quantum hardware....

If you ask a completely unrelated question (e.g., "What is the capital of France?" when your docs are about Machine Learning), the bot will politely decline, adhering to its system prompt.
