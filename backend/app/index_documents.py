from retrieval.loader import load_markdown_documents
from retrieval.chunker import chunk_documents
from retrieval.vectorstore import add_chunks

documents = load_markdown_documents()

print(f"Loaded {len(documents)} documents")

chunks = chunk_documents(documents)

print(f"Created {len(chunks)} chunks")

add_chunks(chunks)

print("Indexing complete")