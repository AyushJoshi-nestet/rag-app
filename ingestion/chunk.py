def make_chunks(pdf_text, document_id, chunk_size=700, chunk_overlap=50):
    all_chunks = []
    chunk_id = 0

    for page in pdf_text:
        text = page["text"]
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end]

            all_chunks.append({
                "id": f"{document_id}_{chunk_id}",
                "text": chunk_text,
                "page_number": page["page_number"],
                "file_path": page["file_path"],
                "document_id": document_id,
            })

            chunk_id += 1
            start += chunk_size - chunk_overlap

    return all_chunks       