from app.services.langchain_service import generate_with_langchain


answer = generate_with_langchain(
    "Explain what a Transformer is in one simple sentence."
)

print("Answer:")
print(answer)