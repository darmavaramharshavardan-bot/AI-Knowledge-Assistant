from app.services.llm_service import generate_answer_stream


prompt = """
Explain the Transformer architecture in simple language.
Give a detailed explanation.
"""


for chunk in generate_answer_stream(prompt):
    print(chunk, end="", flush=True)