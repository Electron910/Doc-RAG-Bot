import os
import streamlit as st
from dotenv import load_dotenv

# Ensure environment variables are loaded first
load_dotenv()

from ingest import process_file
from query import query_rag_pipeline
from config import DATA_DIR

# Set page config
st.set_page_config(page_title="RAG Document Q&A Bot")

st.title("RAG Document Q&A Bot")
st.markdown("Upload documents (PDF, DOCX, TXT) and ask questions about them. The bot will answer using *only* the provided context.")

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar for file upload
with st.sidebar:
    st.header("Document Upload")
    uploaded_files = st.file_uploader(
        "Upload a document", 
        type=["pdf", "docx", "txt"], 
        accept_multiple_files=True
    )
    
    if st.button("Ingest Documents"):
        if uploaded_files:
            with st.spinner("Processing documents..."):
                for uploaded_file in uploaded_files:
                    # Save to data directory
                    file_path = os.path.join(DATA_DIR, uploaded_file.name)
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # Process and ingest into ChromaDB
                    st.text(f"Ingesting {uploaded_file.name}...")
                    process_file(file_path)
                    
                st.success("Ingestion complete!")
        else:
            st.warning("Please upload a file first.")

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        # Optionally show citations if available
        if "citations" in message and message["citations"]:
            with st.expander("Sources"):
                for citation in message["citations"]:
                    st.markdown(f"- {citation}")

# React to user input
if prompt := st.chat_input("Ask a question about your documents..."):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        with st.spinner("Searching documents and generating answer..."):
            try:
                result = query_rag_pipeline(prompt)
                
                answer = result["answer"]
                citations = result["citations"]
                
                st.markdown(answer)
                
                if citations:
                    with st.expander("Sources"):
                        for citation in citations:
                            st.markdown(f"- {citation}")
                            
                # Add assistant response to chat history
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": answer,
                    "citations": citations
                })
            except Exception as e:
                st.error(f"An error occurred: {e}")
