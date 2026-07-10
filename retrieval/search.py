import os
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

COLLECTION_NAME = "rag_app_collection"
client = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))

def get_data(question, pipeline, document_id, embed_model, rerank_model, top_k: int = 4, fetch_k: int = 20):

    model = embed_model
    reranker = rerank_model
    embedded_question = model.encode(question)
    query_filter = Filter(
        must=[
            FieldCondition(key="pipeline", match=MatchValue(value=pipeline)),
            FieldCondition(key="document_id", match=MatchValue(value=document_id)),
        ]
    )
    candidates = client.query_points(
        collection_name=COLLECTION_NAME,
        query=embedded_question,
        query_filter=query_filter,
        limit=fetch_k,
        with_payload=True,
    ).points

    if not candidates:
        return []

    pairs = [(question, c.payload["text"]) for c in candidates]
    scores = reranker.predict(pairs)

    print(scores)

    # 3. Sort candidates by cross-encoder score, take top_k
    reranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)[:top_k]

    chunks = []
    for c, score in reranked:
        chunks.append(c.payload["text"])

    return chunks