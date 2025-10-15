DEFAULT_CONFIG = {
    # Model settings
    "model": "alibaba/tongyi-deepresearch-30b-a3b:free",
    "temperature": 0.3,
    "timeout": 45,
    
    # Agent settings
    "max_iterations": 3,
    "max_context_tokens": 8000,
    
    # RAG settings
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "top_k_results": 5,
    "embedding_model": "all-MiniLM-L6-v2",
    
    # Paths
    "chroma_db_path": "./chroma_db",
    "papers_folder": "./papers",
    "output_dir": "./output",
}