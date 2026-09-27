from app.database import SessionLocal
from app.services.vector_search import search_similar_chunks


db = SessionLocal()


question = "What is the Transformer architecture?"


results = search_similar_chunks(
    db,
    question,
    user_id=3,
    limit=3
)


print("\nNumber of results:", len(results))

print("\nResults:")

for result in results:
    print("-----------------------------")
    print("Chunk ID:", result.id)
    print("Document ID:", result.document_id)
    print("Content:")
    print(result.content[:300])


db.close()