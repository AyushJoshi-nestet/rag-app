from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance,PayloadSchemaType
from dotenv import load_dotenv

from sentence_transformers import SentenceTransformer
import os

load_dotenv()

client = QdrantClient(url= os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))
model = SentenceTransformer('BAAI/bge-small-en-v1.5')

if not client.collection_exists("rag_app_collection"):
    client.create_collection(
        collection_name="rag_app_collection",
        vectors_config=VectorParams(size=model.get_embedding_dimension(), distance=Distance.COSINE))

COLLECTION_NAME = "rag_app_collection"


client.create_payload_index(
    collection_name= COLLECTION_NAME,
    field_name= "pipeline",
    field_schema= PayloadSchemaType.KEYWORD
)

client.create_payload_index(
    collection_name= COLLECTION_NAME,
    field_name= "document_id",
    field_schema= PayloadSchemaType.INTEGER
)

client.create_payload_index(
    collection_name= COLLECTION_NAME,
    field_name= "page_number",
    field_schema= PayloadSchemaType.INTEGER
)

def collection_save(prepared_batch):
    results = []
    for ids, documents, metadata, embeddings in prepared_batch:
        points = []
        for i in range(len(ids)):
            vector = embeddings[i]
            if hasattr(vector, "tolist"):
                vector = vector.tolist()

            points.append(
                PointStruct(
                    id=ids[i],
                    vector=vector,
                    payload={"text": documents[i], **metadata[i]}
                )
            )
        result = client.upsert(collection_name=COLLECTION_NAME, points=points)
        results.append(result)

    return True