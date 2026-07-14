from fastapi import HTTPException, status
from ingestion.embed import embedding_documents
from retrieval.vector_store import collection_save
from fastembed import SparseTextEmbedding
import uuid

sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")

async def store(embed_model, chunks, batch_size: int = 500):
    
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No chunks are being sent for embeddings."
        )

    prepared_batch = []

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        ids = [str(uuid.uuid5(uuid.NAMESPACE_DNS, f"id_{c['id']}")) for c in batch]
        documents = [c["text"] for c in batch]
        metadata = [
            {
                "page_number": c["page_number"]
            } for c in batch
        ]

        embeddings = await embedding_documents(documents, embed_model)
        sparse_embeddings = list(sparse_model.embed(documents))
        prepared_batch.append((ids, documents, metadata, embeddings, sparse_embeddings))

    store_embeddings = await collection_save(prepared_batch=prepared_batch, embed_model=embed_model)
    return store_embeddings