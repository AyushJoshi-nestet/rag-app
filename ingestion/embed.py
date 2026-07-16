import asyncio

async def embedding_documents(documents: list[str], embed_model):
    embeddings = await asyncio.to_thread(embed_model.encode, documents)
    return embeddings