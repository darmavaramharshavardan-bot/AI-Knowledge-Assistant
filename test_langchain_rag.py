from app.database import SessionLocal
from app.services.langchain_rag_service import answer_question_with_langchain


db = SessionLocal()

result = answer_question_with_langchain(
    db,
    "What is the Transformer architecture?"
)

print("\nANSWER:")
print(result["answer"])

print("\nSOURCES:")
for source in result["sources"]:
    print(source)

db.close()