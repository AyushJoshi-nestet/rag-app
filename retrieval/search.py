import os
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, Prefetch, SparseVector, RrfQuery, Rrf

COLLECTION_NAME = "rag_app_collection"
client = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))

def get_data(question, embed_model, rerank_model, sparse_model ,top_k: int = 4, fetch_k: int = 20):
    model = embed_model
    sparse_model = sparse_model
    reranker = rerank_model

    embedded_question = model.encode(question)

    if hasattr(embedded_question, "tolist"):
        embedded_question = embedded_question.tolist()

    sparse_query = list(sparse_model.embed([question]))[0]

    # query_filter = Filter(
    #     must=[
    #         FieldCondition(key="source_name", match=MatchValue(value=".pdf")),
    #     ]
    # )

    candidates = client.query_points(
        collection_name=COLLECTION_NAME,
        prefetch=[
            Prefetch(
                query=embedded_question,
                using="dense",
                # filter=query_filter,
                limit=fetch_k,
            ),
            Prefetch(
                query=SparseVector(
                    indices=sparse_query.indices.tolist(),
                    values=sparse_query.values.tolist(),
                ),
                using="bm25",
                # filter=query_filter,
                limit=fetch_k,
            ),
        ],
        query= RrfQuery(rrf=Rrf()),
        limit=fetch_k,
        with_payload=True,
    ).points
    if not candidates:
        return []

    pairs = [(question, c.payload["text"]) for c in candidates]
    scores = reranker.predict(pairs)
    reranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)[:top_k]


    chunks = [c.payload["text"] for c, score in reranked]

    return chunks   

