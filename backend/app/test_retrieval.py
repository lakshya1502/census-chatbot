from retrieval.loader import load_markdown_documents
from retrieval.chunker import chunk_documents
from retrieval.vectorstore import add_chunks
from retrieval.retriever import retrieve

documents = load_markdown_documents()

chunks = chunk_documents(documents)

add_chunks(chunks)

results = retrieve("Karnataka literacy rate male")

for result in results:
    print("\n")
    print("SOURCE:", result["source"])
    print("SCORE:", result["score"])
    print(result["text"][:500])