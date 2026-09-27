import os

from dotenv import load_dotenv
from google import genai


load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=API_KEY)


def generate_answer(message: str) -> str:
    """
    Send the user's message to Gemini
    and return the generated answer.
    """

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=message
    )

    return response.text


def generate_answer_stream(prompt: str):
    """
    Stream Gemini's response chunk by chunk.
    """

    response = client.models.generate_content_stream(
        model="gemini-3.1-flash-lite",
        contents=prompt
    )

    for chunk in response:
        if chunk.text:
            yield chunk.text