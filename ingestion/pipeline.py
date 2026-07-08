from fastapi import HTTPException, status
from ingestion.embed import embedding_documents
from retrieval.vector_store import collection_save 
import uuid

def store(document_id: int,  chunks: str, batch_size: int = 500):
    chunks = chunks
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No chunks are being sent for embeddings."
        )
    batch_size = batch_size
    prepared_batch = []
    for i in range(0, len(chunks), batch_size):
        
        batch = chunks[i:i + batch_size]
        ids = [str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{document_id}_{c['id']}")) for c in batch]
        print(ids)
        documents = [c["text"] for c in batch]
        
        metadata = [
            {
                "pipeline": "rag",
                "document_id": document_id,
                "page_number": c["page_number"]
            } for c in batch
        ]
        
        embeddings = embedding_documents(documents)
        prepared_batch.append((ids, documents, metadata, embeddings))
    
    store_embeddings = collection_save(prepared_batch=prepared_batch)

    return store_embeddings