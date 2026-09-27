from app.database import SessionLocal
from app.services.vector_search import search_similar_chunks


db = SessionLocal()

results = search_similar_chunks(
    db,
    "What is Python?",
    limit=3
)

for result in results:
    print("Chunk ID:", result.id)
    print("Content:", result.content)
    print("--------------------")

db.close()