from fastapi import HTTPException, status
from ingestion.embed import embedding_documents
from retrieval.vector_store import collection_save 

def store(document_id: int,  chunks: str, batch_size: int = 500):
    chunks = chunks
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No chunks are being sent for embeddings."
        )
    batch_size = batch_size

    for i in range(0, len(chunks), batch_size):
        
        batch = chunks[i:i + batch_size]
        id = [f"{document_id}_{c['id']}" for c in batch]
        documents = [c["text"] for c in batch]
        
        metadata = [
            {
                "pipeline": "rag",
                "document_id": document_id,
                "page_number": c["page_number"]
            } for c in batch
        ]
        
        embeddings = embedding_documents(documents)
        store_embeddings = collection_save(id=id, documents=documents, embedings=embeddings, metadata=metadata)
        print(embeddings)