from app.database import SessionLocal
from app.models import Document, DocumentChunk
from app.services.embedding_service import create_embedding


db = SessionLocal()


# Create a test document
document = Document(
    filename="test.txt",
    user_id=1
)

db.add(document)
db.commit()
db.refresh(document)


# Create text
text = "Python is a programming language."


# Create embedding
embedding = create_embedding(text)


# Create document chunk
chunk = DocumentChunk(
    document_id=document.id,
    content=text,
    embedding=embedding
)

db.add(chunk)
db.commit()
db.refresh(chunk)


print("Document ID:", document.id)
print("Chunk ID:", chunk.id)
print("Embedding size:", len(embedding))


db.close()