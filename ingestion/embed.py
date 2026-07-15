async def embedding_documents(documents: list[str], embed_model):

    documents = documents
    model = embed_model
    embeddings = model.encode(documents)
    return embeddings
