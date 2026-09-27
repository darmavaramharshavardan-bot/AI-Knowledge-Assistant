from sentence_transformers import SentenceTransformer


model = SentenceTransformer(
    "sentence-transformers/all-mpnet-base-v2"
)


def create_embedding(text: str):
    """
    Convert text into a 768-dimensional embedding.
    """

    vector = model.encode(text)

    return vector.tolist()