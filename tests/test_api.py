# from fastapi.testclient import TestClient
# from main import app

# client = TestClient(app)

# def test_upload():
#     response = client.post("/upload/")
#     assert response.status_code == 200
#     assert response.json() == {"id", "file_id", "file_path", "file_name"}

from celery_app import celery_app
from ingestion.extract import extract_text_from_pdf
from ingestion.chunk import make_chunks
from sentence_transformers import SentenceTransformer
from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance, PayloadSchemaType, SparseVector, SparseVectorParams
import uuid
import os

# Loaded once per worker process, not per task
embed_model = SentenceTransformer('BAAI/bge-small-en-v1.5')
sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")
qdrant_client = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))

COLLECTION_NAME = "rag_app_collection"


@celery_app.task(bind=True, max_retries=3)
def process_document_task(self, file_path, document_id, source_name):
    try:
        # Step 1: OCR + text extraction
        pdf_text = extract_text_from_pdf(file_path)

        # Step 2: Chunking
        chunks = make_chunks(pdf_text, document_id)
        if not chunks:
            raise ValueError("No chunks produced from document")

        # Step 3: Embedding
        documents = [c["text"] for c in chunks]
        ids = [str(uuid.uuid5(uuid.NAMESPACE_DNS, c['id'])) for c in chunks]
        metadata = [
            {
                "page_number": c["page_number"],
                "source_name": source_name,
                "file_id": c['document_id']
            } for c in chunks
        ]

        dense_embeddings = embed_model.encode(documents)
        sparse_embeddings = list(sparse_model.embed(documents))

        # Step 4: Upsert into Qdrant
        if not qdrant_client.collection_exists(COLLECTION_NAME):
            qdrant_client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config={
                    "dense": VectorParams(
                        size=embed_model.get_sentence_embedding_dimension(),
                        distance=Distance.COSINE,
                    )
                },
                sparse_vectors_config={"bm25": SparseVectorParams()},
            )
            qdrant_client.create_payload_index(COLLECTION_NAME, "source_name", PayloadSchemaType.KEYWORD)
            qdrant_client.create_payload_index(COLLECTION_NAME, "page_number", PayloadSchemaType.INTEGER)
            qdrant_client.create_payload_index(COLLECTION_NAME, "file_id", PayloadSchemaType.KEYWORD)

        points = []
        for i in range(len(ids)):
            vector = dense_embeddings[i]
            if hasattr(vector, "tolist"):
                vector = vector.tolist()
            sparse = sparse_embeddings[i]
            points.append(
                PointStruct(
                    id=ids[i],
                    vector={
                        "dense": vector,
                        "bm25": SparseVector(
                            indices=sparse.indices.tolist(),
                            values=sparse.values.tolist(),
                        ),
                    },
                    payload={"text": documents[i], **metadata[i]}
                )
            )

        qdrant_client.upsert(collection_name=COLLECTION_NAME, points=points)

        return {"status": "success", "document_id": document_id, "chunks_stored": len(points)}

    except Exception as e:
        # Retry with exponential-ish backoff, up to max_retries
        raise self.retry(exc=e, countdown=10)