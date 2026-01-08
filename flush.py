# from langchain_openai import OpenAIEmbeddings
# from qdrant_client import QdrantClient
# from qdrant_client.models import Distance, VectorParams
# from dotenv import load_dotenv

# load_dotenv()

# def create_qdrant_collection(collection_name: str, qdrant_url: str = "qdrant-alb-1638819799.us-east-1.elb.amazonaws.com:80"):
#     # Initialize embeddings
#     #embeddings = OpenAIEmbeddings()
    
#     # Detect embedding dimension dynamically
#     #dummy_vector = embeddings.embed_query("Hello world")
#     embedding_dim = 1536
#     print(f"Detected embedding dimension: {embedding_dim}")
    
#     # Connect to Qdrant
#     client = QdrantClient(
#     url="https://edb6ba88-59c8-4b02-b8d1-2e7a7738ca40.us-east-1-1.aws.cloud.qdrant.io:6333", 
#     api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.FaGNNWrPYfqylEckrKjiwOmBvcTFxqx0pvOT5dy_k5M",
#     )
    
#     # Drop + recreate collection
#     client.recreate_collection(
#         collection_name=collection_name,
#         vectors_config=VectorParams(size=embedding_dim, distance=Distance.COSINE)
#     )
    
#     print(f" Collection '{collection_name}' recreated with vector size {embedding_dim}.")

# if __name__ == "__main__":
#     # Recreate both collections fresh
#     create_qdrant_collection("multimodel_vector_db")
#     create_qdrant_collection("10K_vector_db")


from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PayloadSchemaType,
    CreateCollection,
)
from dotenv import load_dotenv

load_dotenv()

def create_qdrant_collection(collection_name: str, qdrant_url: str):
    embedding_dim = 1536

    client = QdrantClient(
        url=qdrant_url,
        api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.FaGNNWrPYfqylEckrKjiwOmBvcTFxqx0pvOT5dy_k5M"   # <- put your cloud key
    )

    print(f"Recreating collection '{collection_name}' with payload indexes...")

    # Drop and recreate collection
    client.recreate_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=embedding_dim, distance=Distance.COSINE)
    )

    # -------------------------------
    # Add payload indexes required by your ingestion/filter code
    # -------------------------------
    payload_fields = {
        "metadata.source_file": PayloadSchemaType.KEYWORD,
        "metadata.company": PayloadSchemaType.KEYWORD,
        "metadata.content_type": PayloadSchemaType.KEYWORD,
        "metadata.content_hash": PayloadSchemaType.KEYWORD,
        "metadata.image_content_hash": PayloadSchemaType.KEYWORD,
        "metadata.page_num": PayloadSchemaType.INTEGER,
        "metadata.ingestion_timestamp": PayloadSchemaType.KEYWORD,
    }

    for field_name, schema in payload_fields.items():
        print(f"Creating index for {field_name} ({schema})...")
        client.create_payload_index(
            collection_name=collection_name,
            field_name=field_name,
            field_schema=schema,
        )

    print(f"✅ Collection '{collection_name}' created with all required indexes.")


if __name__ == "__main__":
    create_qdrant_collection("multimodel_vector_db",
                             qdrant_url="https://edb6ba88-59c8-4b02-b8d1-2e7a7738ca40.us-east-1-1.aws.cloud.qdrant.io:6333")

    create_qdrant_collection("10K_vector_db",
                             qdrant_url="https://edb6ba88-59c8-4b02-b8d1-2e7a7738ca40.us-east-1-1.aws.cloud.qdrant.io:6333")
