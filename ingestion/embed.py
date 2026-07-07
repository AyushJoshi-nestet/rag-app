from sentence_transformers import SentenceTransformer

def embedding_documents(documents: list[str]):

    documents = documents
    model = SentenceTransformer('BAAI/bge-small-en-v1.5')
    embeddings = model.encode(documents)

    return embeddings
