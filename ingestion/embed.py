def embedding_documents(documents: list[str], embed_model):
    return embed_model.encode(documents)