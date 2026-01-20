"""
this module is used for loading the image related data and vector db retriever
"""

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore, RetrievalMode  # Updated LangChain Qdrant integration
from qdrant_client import QdrantClient
import os

load_dotenv()

from qdrant_client.http.models import Filter

# Try to import FastEmbedSparse for BM25 sparse vectors
try:
    from langchain_qdrant import FastEmbedSparse
    SPARSE_EMBEDDING_AVAILABLE = True
except ImportError:
    SPARSE_EMBEDDING_AVAILABLE = False
    print("Warning: FastEmbedSparse not available. Install with: pip install 'langchain-qdrant[fastembed]' or 'fastembed'")

class load_vector_database():
    "This class is useful for loading the vector DBs"
    def __init__(self, use_hybrid_search: bool = False):
        """
        Initialize vector database loader.
        
        Args:
            use_hybrid_search: If True, use hybrid collections with BM25 sparse vectors.
                              If False, use standard collections.
        """
        # Use hybrid collections if specified, otherwise use standard collections
        if use_hybrid_search:
            self.image_vector_db_path = "multimodel_vector_db_hybrid"  # hybrid collection name
            self.text_vector_db_path = "10K_vector_db_hybrid"
        else:
            self.image_vector_db_path = "multimodel_vector_db_new"  # standard collection name
            self.text_vector_db_path = "10K_vector_db_new"
        
        self.use_hybrid_search = use_hybrid_search
        self.embeddings = OpenAIEmbeddings()
        self.qdrant_url = os.getenv("QDRANT_URL", "")
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY",'')
        
        # Initialize sparse embeddings for hybrid search if available
        self.sparse_embeddings = None
        if use_hybrid_search and SPARSE_EMBEDDING_AVAILABLE:
            try:
                self.sparse_embeddings = FastEmbedSparse(model_name="Qdrant/bm25")
                print("✓ BM25 sparse embeddings initialized for hybrid search")
            except Exception as e:
                print(f"Warning: Failed to initialize sparse embeddings: {e}")
                print("Falling back to dense-only search")
                self.use_hybrid_search = False
        
        # Try cloud Qdrant first, fallback to local
        try:
            print(f"Attempting to connect to Qdrant at: {self.qdrant_url}")
            self.qdrant_client = QdrantClient(url=self.qdrant_url, api_key=self.qdrant_api_key, timeout=60)
            # Test connection by getting collections
            self.qdrant_client.get_collections()
            print(f"✓ Successfully connected to Qdrant at {self.qdrant_url}")
        except Exception as e:
            print(f"✗ Failed to connect to cloud Qdrant: {e}")
            print("Falling back to local Qdrant at http://localhost:6333")
            self.qdrant_url = "http://localhost:6333"
            self.qdrant_api_key = ''
            try:
                self.qdrant_client = QdrantClient(url=self.qdrant_url, api_key=self.qdrant_api_key, timeout=60)
                self.qdrant_client.get_collections()
                print(f"✓ Successfully connected to local Qdrant")
            except Exception as local_error:
                print(f"✗ Failed to connect to local Qdrant: {local_error}")
                raise ConnectionError("Unable to connect to both cloud and local Qdrant instances. Please ensure Qdrant is running.")
    
    def get_image_retriever(self):
        # Configure vector store based on whether hybrid search is enabled
        vector_store_kwargs = {
            "client": self.qdrant_client,
            "collection_name": self.image_vector_db_path,
            "embedding": self.embeddings
        }
        
        # If using hybrid collections (ending with _hybrid), always specify vector_name
        # because these collections use named vectors
        if "_hybrid" in self.image_vector_db_path:
            vector_store_kwargs["vector_name"] = "dense"
        
        # Add sparse vector config if hybrid search is fully enabled
        if self.use_hybrid_search and self.sparse_embeddings:
            vector_store_kwargs.update({
                "sparse_embedding": self.sparse_embeddings,
                "retrieval_mode": RetrievalMode.HYBRID,
                "sparse_vector_name": "sparse"  # Match the sparse vector name from flush.py
            })
        
        image_vectorstore_10k = QdrantVectorStore(**vector_store_kwargs)
        image_retriever_10k = image_vectorstore_10k.as_retriever(search_kwargs={"k": 4})  
        return image_vectorstore_10k, image_retriever_10k, self.image_vector_db_path
    
    def get_text_retriever(self):
        # Configure vector store based on whether hybrid search is enabled
        vector_store_kwargs = {
            "client": self.qdrant_client,
            "collection_name": self.text_vector_db_path,
            "embedding": self.embeddings
        }
        
        # If using hybrid collections (ending with _hybrid), always specify vector_name
        # because these collections use named vectors
        if "_hybrid" in self.text_vector_db_path:
            vector_store_kwargs["vector_name"] = "dense"
        
        # Add sparse vector config if hybrid search is fully enabled
        if self.use_hybrid_search and self.sparse_embeddings:
            vector_store_kwargs.update({
                "sparse_embedding": self.sparse_embeddings,
                "retrieval_mode": RetrievalMode.HYBRID,
                "sparse_vector_name": "sparse"  # Match the sparse vector name from flush.py
            })
        
        vectorstore = QdrantVectorStore(**vector_store_kwargs)
        retriever = vectorstore.as_retriever(
            search_kwargs={"k": 4}
        )
        return retriever, vectorstore, self.text_vector_db_path
    
    def get_vector_store_files(self, vectorstore):
        doc_list = set()

        points, _ = vectorstore.client.scroll(
            collection_name=vectorstore.collection_name,
            with_payload=True,
            limit=1000
        )

        for point in points:
            payload = point.payload  # <-- access directly
            doc_list.add(payload.get("source_file", "Unknown"))

        return ' ,'.join(doc_list)


    def get_img_vector_store_companies(self, img_vector_store):
        doc_list = set()

        points, _ = img_vector_store.client.scroll(
            collection_name=img_vector_store.collection_name,
            with_payload=True,
            limit=1000
        )

        for point in points:
            payload = point.payload  # <-- access directly
            doc_list.add(payload.get("company", "Unknown"))

        return ' ,'.join(doc_list)



