from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance, PayloadSchemaType,SparseVector, SparseVectorParams
from dotenv import load_dotenv
import os

load_dotenv()

client = AsyncQdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))

async def collection_save(prepared_batch, embed_model):
    model = embed_model
    
    COLLECTION_NAME = "rag_app_collection"

    if not await client.collection_exists(COLLECTION_NAME):
        await client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config={
                "dense": VectorParams(
                    size=model.get_embedding_dimension(),
                    distance=Distance.COSINE,
                )
            },
            sparse_vectors_config={
                "bm25": SparseVectorParams()
            },
        )
        await client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="source_name",
            field_schema=PayloadSchemaType.KEYWORD
        )
        await client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="page_number",
            field_schema=PayloadSchemaType.INTEGER
        )
        await client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="file_id",
            field_schema=PayloadSchemaType.KEYWORD
        )

    results = []
    for ids, documents, metadata, embeddings, sparse_embeddings in prepared_batch:
        points = []
        for i in range(len(ids)):
            vector = embeddings[i]
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
        result = await client.upsert(collection_name=COLLECTION_NAME, points=points)
        results.append(result)
    return True