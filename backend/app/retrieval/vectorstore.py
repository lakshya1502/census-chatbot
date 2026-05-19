from rank_bm25 import BM25Okapi

tokenized_chunks = []
document_metadata = []

bm25 = None


def tokenize(text):
    return text.lower().split()


def add_chunks(chunks):

    global bm25

    for chunk in chunks:

        tokens = tokenize(chunk["text"])

        tokenized_chunks.append(tokens)

        document_metadata.append(chunk)

    bm25 = BM25Okapi(tokenized_chunks)