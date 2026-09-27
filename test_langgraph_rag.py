from app.database import SessionLocal
from app.services.langgraph_rag_service import rag_graph


db = SessionLocal()

result = rag_graph.invoke({
    "question": "What is the Transformer architecture?",
    "context": "",
    "answer": "",
    "sources": [],
    "db": db
})

print("\nANSWER:")
print(result["answer"])

print("\nSOURCES:")
for source in result["sources"]:
    print(source)

db.close()