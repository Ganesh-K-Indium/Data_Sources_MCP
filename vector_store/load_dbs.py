"""
this module is used for loading the image related data and vector db retriever
"""

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore  # Updated LangChain Qdrant integration
from qdrant_client import QdrantClient
import os

load_dotenv()

from qdrant_client.http.models import Filter

class load_vector_database():
    "This class is useful for loading the vector DBs"
    def __init__(self):
        self.image_vector_db_path = "multimodel_vector_db"  # collection name
        self.text_vector_db_path = "10K_vector_db"      
        self.embeddings = OpenAIEmbeddings()
        self.qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY",'')
        
        # Try cloud Qdrant first, fallback to local
        try:
            print(f"Attempting to connect to Qdrant at: {self.qdrant_url}")
            self.qdrant_client = QdrantClient(url=self.qdrant_url, api_key=self.qdrant_api_key, timeout=5)
            # Test connection by getting collections
            self.qdrant_client.get_collections()
            print(f"✓ Successfully connected to Qdrant at {self.qdrant_url}")
        except Exception as e:
            print(f"✗ Failed to connect to cloud Qdrant: {e}")
            print("Falling back to local Qdrant at http://localhost:6333")
            self.qdrant_url = "http://localhost:6333"
            self.qdrant_api_key = ''
            try:
                self.qdrant_client = QdrantClient(url=self.qdrant_url, api_key=self.qdrant_api_key, timeout=5)
                self.qdrant_client.get_collections()
                print(f"✓ Successfully connected to local Qdrant")
            except Exception as local_error:
                print(f"✗ Failed to connect to local Qdrant: {local_error}")
                raise ConnectionError("Unable to connect to both cloud and local Qdrant instances. Please ensure Qdrant is running.")
    
    def get_image_retriever(self):
        image_vectorstore_10k = QdrantVectorStore(
            client=self.qdrant_client,
            collection_name=self.image_vector_db_path,
            embedding=self.embeddings
        )
        image_retriever_10k = image_vectorstore_10k.as_retriever(search_kwargs={"k": 4})  
        return image_vectorstore_10k, image_retriever_10k, self.image_vector_db_path
    
    def get_text_retriever(self):
        vectorstore = QdrantVectorStore(
            client=self.qdrant_client,
            collection_name=self.text_vector_db_path,
            embedding=self.embeddings
        )
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



