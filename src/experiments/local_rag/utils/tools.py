from pathlib import Path
from typing import List, Dict, Any, Optional
from chromadb.utils import embedding_functions
import chromadb


class Tool:
    """Base class for agent tools"""
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    def execute(self, query=None, **kwargs) -> str:
        """
        Main execute method that normalizes input before calling _execute
        """
        # 🔧 Normalize query input to handle lists, dicts, None
        if isinstance(query, list):
            query = " ".join(map(str, query))
        elif isinstance(query, dict):
            # Handle dict - could be {"query": ["item1", "item2"]}
            if "query" in query:
                q = query["query"]
                if isinstance(q, list):
                    query = " ".join(map(str, q))
                else:
                    query = str(q)
            else:
                query = " ".join(f"{k}: {v}" for k, v in query.items())
        elif query is None:
            query = ""
        else:
            query = str(query)
        
        # Call subclass implementation
        return self._execute(query, **kwargs)
    
    def _execute(self, query: str, **kwargs) -> str:
        """Override this in subclasses"""
        raise NotImplementedError("Subclass must implement _execute()")


class WebSearchTool(Tool):
    """Tool for performing web searches using Tavily"""
    def __init__(self, tavily_client):
        super().__init__(
            name="web_search",
            description="Search the internet for current information. Use this when you need information not in the knowledge base or need recent/current data. Input should be a search query string."
        )
        self.client = tavily_client
    
    def _execute(self, query: str, n_results: int = 3) -> str:
        """
        Execute web search with normalized string query
        """
        try:
            response = self.client.search(query=query, max_results=n_results)
            
            if not response or not response.get('results'):
                return "No relevant web results found."
            
            context = "\n\n".join([
                f"[Source: {res.get('url', 'Unknown')}]\n{res.get('content', res.get('snippet', ''))}"
                for res in response['results']
            ])
            return context
            
        except Exception as e:
            return f"Error performing web search: {str(e)}"


class RAGTool(Tool):
    """Tool for searching the knowledge base"""
    def __init__(self, collection, retriever=None):
        super().__init__(
            name="vectorstore_search",
            description="Retrieve relevant info from a vectorstore that contains AI research papers. Input should be a search query string."
        )
        self.retriever = retriever
        self.collection = collection
    
    def _execute(self, query: str, n_results: int = 3) -> str:
        """
        Execute vectorstore search with normalized string query
        """
        try:
            if self.retriever:
                results = self.retriever.retrieve_formatted(query=query, n_results=n_results)
            else:
                # Fallback to direct collection query
                raw_results = self.collection.query(
                    query_texts=[query],
                    n_results=n_results
                )
                
                if not raw_results["documents"][0]:
                    return "No relevant documents found."
                
                # Format results
                formatted = []
                for i, (doc, metadata) in enumerate(zip(
                    raw_results["documents"][0], 
                    raw_results["metadatas"][0]
                )):
                    source = metadata.get("source", "unknown")
                    formatted.append(f"[{i+1}] From {source}:\n{doc[:500]}...")
                
                results = "\n\n".join(formatted)
            
            return results
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            return f"Error searching papers: {str(e)}\nDetails: {error_details}"
        

class VectorStoreRetriever:
    """Custom retriever for ChromaDB"""
    
    def __init__(
        self, 
        collection_name: str = "research_papers_v2",
        chroma_db_path: str = None,
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        
        if chroma_db_path is None:
            chroma_db_path = Path(__file__).parent / "chroma_db"
        
        self.embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=embedding_model
        )
        
        self.client = chromadb.PersistentClient(path=str(chroma_db_path))
        self.collection = self.client.get_collection(
            name=collection_name,
            embedding_function=self.embed_fn
        )
    
    def retrieve(
        self, 
        query: str, 
        n_results: int = 3,
        where: Optional[Dict] = None,
        where_document: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:

        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
            where_document=where_document
        )
        

        documents = []
        for i in range(len(results['ids'][0])):
            documents.append({
                'id': results['ids'][0][i],
                'content': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i] if 'distances' in results else None
            })
        
        return documents
    
    def retrieve_with_scores(
        self, 
        query: str, 
        n_results: int = 3,
        score_threshold: float = None
    ) -> List[tuple[Dict[str, Any], float]]:

        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        documents_with_scores = []
        for i in range(len(results['ids'][0])):
            # Convert distance to similarity score 
            distance = results['distances'][0][i] if 'distances' in results else 0
            similarity_score = 1 - (distance / 2)  # Convert to 0-1 scale
            
            if score_threshold is None or similarity_score >= score_threshold:
                doc = {
                    'id': results['ids'][0][i],
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                }
                documents_with_scores.append((doc, similarity_score))
        
        return documents_with_scores
    
    def retrieve_by_source(
        self, 
        query: str, 
        source: str, 
        n_results: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents filtered by source
        
        Args:
            query: Search query
            source: Source file name (e.g., "ARE.pdf")
            n_results: Number of results
        """
        return self.retrieve(
            query=query,
            n_results=n_results,
            where={"source": source}
        )
    
    def retrieve_formatted(
        self, 
        query: str, 
        n_results: int = 3,
        include_metadata: bool = True
    ) -> str:
        """
        Retrieve and format documents as a string
        
        Args:
            query: Search query
            n_results: Number of results
            include_metadata: Whether to include source info
            
        Returns:
            Formatted string with all retrieved documents
        """
        documents = self.retrieve(query, n_results)
        
        if not documents:
            return "No relevant documents found."
        
        formatted_docs = []
        for i, doc in enumerate(documents, 1):
            if include_metadata:
                header = f"[Document {i} - Source: {doc['metadata'].get('source', 'Unknown')}]"
            else:
                header = f"[Document {i}]"
            
            formatted_docs.append(f"{header}\n{doc['content']}")
        
        return "\n\n" + "="*80 + "\n\n".join(formatted_docs)