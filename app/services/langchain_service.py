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
    Send a prompt to Gemini through LangChain
    and return only the plain text answer.
    """

    response = llm.invoke(prompt)

    content = response.content

    # Gemini may return structured content blocks.
    if isinstance(content, list):
        text_parts = []

        for item in content:
            if isinstance(item, dict):
                text = item.get("text")

                if text:
                    text_parts.append(text)

            elif isinstance(item, str):
                text_parts.append(item)

        return "".join(text_parts).strip()

    # Normal string response
    return str(content).strip()