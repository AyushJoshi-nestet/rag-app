import os
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

COLLECTION_NAME = "rag_app_collection"

client = QdrantClient(url= os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))
model = SentenceTransformer('BAAI/bge-small-en-v1.5')


def get_data(question: str = 'question', pipeline: str = 'pipeline', document_id: str = 'document_id'):

    embedded_question = model.encode(question)
    query_filter = Filter(
        must=[
            FieldCondition(key="pipeline", match=MatchValue(value=pipeline)),
            FieldCondition(key="document_id", match=MatchValue(value=document_id)),
        ]
    )

    get_results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=embedded_question,
        query_filter=query_filter,
        limit=3,
        with_payload=True,
    ).points

    chunks = []
    for r in get_results:
        print(f"Score: {r.score}")
        print(f"Text Chunk: {r.payload['text']}\n")
        chunks.append(r.payload['text'])

    return chunks