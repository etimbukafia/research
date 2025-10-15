import chromadb
from chromadb.utils import embedding_functions
import PyPDF2
from pathlib import Path
from tavily import TavilyClient
import logging

# Import from YOUR existing tools.py
from utils.tools import RAGTool, VectorStoreRetriever, WebSearchTool
from agents.base_agent import BaseReActAgent
from utils.config import DEFAULT_CONFIG

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.resolve()

class SimpleRAG:
    """
    Simple RAG system using your existing tools.py
    """
    
    def __init__(self, api_key, tavily_api_key, papers_folder="./papers", 
                 chroma_db_path=None, config=None):
        self.api_key = api_key
        self.tavily_api_key = tavily_api_key
        self.tavily_client = TavilyClient(api_key=tavily_api_key)

        
        self.papers_folder = Path(papers_folder)
        self.chroma_db_path = Path(chroma_db_path or Path(__file__).parent / "chroma_db")
        self.config = config or DEFAULT_CONFIG.copy()
        
        # Setup ChromaDB
        embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=self.config["embedding_model"]
        )
        self.client = chromadb.PersistentClient(path=str(self.chroma_db_path))
        self.collection = self.client.get_or_create_collection(
            name="research_papers_v2",  # Match your existing collection name
            metadata={"hnsw:space": "cosine"},
            embedding_function=embed_fn
        )
        
        # Setup retriever using YOUR VectorStoreRetriever
        self.retriever = VectorStoreRetriever(
            collection_name="research_papers_v2",
            chroma_db_path=str(self.chroma_db_path),
            embedding_model=self.config["embedding_model"]
        )
        
        # Setup tools using YOUR RAGTool
        rag_tool = RAGTool(
            collection=self.collection,
            retriever=self.retriever
        )
        websearch_tool = WebSearchTool(self.tavily_client)

        self.tools = [rag_tool, websearch_tool]
        
        # Setup agent
        self.agent = BaseReActAgent(api_key, self.tools, self.config)
    
    def ingest_papers(self):
        """Load PDFs into vector store"""
        if not self.papers_folder.exists():
            logger.warning(f"Papers folder not found: {self.papers_folder}")
            self.papers_folder.mkdir(parents=True, exist_ok=True)
            return
        
        pdf_files = list(self.papers_folder.glob("*.pdf"))
        if not pdf_files:
            logger.warning("No PDF files found")
            return
        
        logger.info(f"Found {len(pdf_files)} papers")
        
        for pdf_file in pdf_files:
            text = self._extract_pdf_text(pdf_file)
            if not text.strip():
                logger.warning(f"No text in {pdf_file.name}")
                continue
            
            chunks = self._chunk_text(text)
            
            # Prepare data
            ids = []
            metadatas = []
            for i, chunk in enumerate(chunks):
                ids.append(f"{pdf_file.stem}_chunk_{i}")
                metadatas.append({
                    "source": pdf_file.name,
                    "chunk_index": i
                })
            
            # Check if already exists
            try:
                existing = self.collection.get(ids=ids[:1])
                if existing["ids"]:
                    logger.info(f"Skipping {pdf_file.name} (already ingested)")
                    continue
            except:
                pass
            
            # Add to collection
            try:
                self.collection.add(
                    documents=chunks,
                    metadatas=metadatas,
                    ids=ids
                )
                logger.info(f"✅ Ingested {pdf_file.name} ({len(chunks)} chunks)")
            except Exception as e:
                logger.error(f"❌ Error ingesting {pdf_file.name}: {e}")
    
    def _extract_pdf_text(self, pdf_path):
        """Extract text from PDF"""
        text = ""
        try:
            with open(pdf_path, 'rb') as f:
                pdf = PyPDF2.PdfReader(f)
                for page in pdf.pages:
                    text += page.extract_text() or ""
        except Exception as e:
            logger.error(f"Error reading PDF {pdf_path.name}: {e}")
        return text
    
    def _chunk_text(self, text):
        """Split text into chunks with overlap"""
        chunk_size = self.config["chunk_size"]
        overlap = self.config["chunk_overlap"]
        
        # Simple sentence-aware chunking
        sentences = text.replace('\n', ' ').split('. ')
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < chunk_size:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def query(self, question):
        """Query the RAG system"""
        return self.agent.run(question)
    
    def reset_database(self):
        """Delete and recreate collection"""
        try:
            self.client.delete_collection("research_papers_v2")
            logger.info("✅ Database reset successful")
        except Exception as e:
            logger.error(f"❌ Error resetting database: {e}")