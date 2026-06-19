import sys
from ingest import process_all_files_in_data_dir
from query import query_rag_pipeline

def main():
    print("========================================")
    print("      RAG Document Q&A Bot (CLI)        ")
    print("========================================")
    print("Loading collection... (Make sure you have ingested documents first)\n")
    
    while True:
        try:
            question = input("Ask a question (or type 'exit' to quit): ").strip()
            
            if not question:
                continue
                
            if question.lower() in ['exit', 'quit']:
                print("Exiting...")
                break
                
            print("\nThinking...\n")
            result = query_rag_pipeline(question)
            
            print("----------------------------------------")
            print(f"ANSWER:\n{result['answer']}")
            print("----------------------------------------")
            
            if result['citations']:
                print("CITATIONS:")
                for citation in result['citations']:
                    print(f"- {citation}")
            print("========================================\n")
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nAn error occurred: {e}\n")

if __name__ == "__main__":
    main()
