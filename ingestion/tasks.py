from ingestion.celery_app import app
from ingestion.extract import extract_text_from_pdf
from ingestion.chunk import make_chunks
import uuid
from ingestion.embed import embedding_documents
from fastembed import SparseTextEmbedding
from retrieval.vector_store import collection_save
from sentence_transformers import SentenceTransformer
from sqlmodel import Session, select
from storage.db import engine
from storage.data import Documents

embed_model = SentenceTransformer('BAAI/bge-small-en-v1.5')
sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")


def set_status(document_id, status_value):
    with Session(engine) as session:
        doc = session.exec(select(Documents).where(Documents.file_id == document_id)).first()
        if doc:
            doc.status = status_value
            session.add(doc)
            session.commit()


@app.task(bind=True, max_retries=3)
def save_embeddings_through_task(self, file_path, document_id, source_name, batch_size: int = 500):
    try:
        set_status(document_id, "processing")

        extract_text = extract_text_from_pdf(file_path=file_path)
        get_chunks = make_chunks(pdf_text=extract_text, document_id=document_id)

        if not get_chunks:
            raise ValueError("No chunks are being sent for embeddings.")

        prepared_batch = []

        for i in range(0, len(get_chunks), batch_size):
            batch = get_chunks[i:i + batch_size]
            ids = [str(uuid.uuid5(uuid.NAMESPACE_DNS, c['id'])) for c in batch]
            documents = [c["text"] for c in batch]
            metadata = [
                {"page_number": c["page_number"], "source_name": source_name, "file_id": c['document_id']}
                for c in batch
            ]

            embeddings = embedding_documents(documents, embed_model)
            sparse_embeddings = list(sparse_model.embed(documents))
            prepared_batch.append((ids, documents, metadata, embeddings, sparse_embeddings))

        store_embeddings = collection_save(prepared_batch=prepared_batch, embed_model=embed_model)

        set_status(document_id, "completed")
        return store_embeddings

    except Exception as e:
        try:
            raise self.retry(exc=e, countdown=10)
        except self.MaxRetriesExceededError:
            set_status(document_id, "failed")
            raise




