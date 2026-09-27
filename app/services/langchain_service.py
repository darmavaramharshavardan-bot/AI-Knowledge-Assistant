import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI


load_dotenv()


llm = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite",
    google_api_key=os.getenv("GEMINI_API_KEY"),
    temperature=0
)


def generate_with_langchain(prompt: str) -> str:
    """
    Send a prompt to Gemini through LangChain.
    """

    response = llm.invoke(prompt)

    return response.content