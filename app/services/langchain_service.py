import os
import time

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI


load_dotenv()


API_KEY = os.getenv("GEMINI_API_KEY")

PRIMARY_MODEL = "gemini-3.1-flash-lite"
FALLBACK_MODEL = "gemini-3.5-flash-lite"


def create_llm(model_name: str):
    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=API_KEY,
        temperature=0
    )


primary_llm = create_llm(PRIMARY_MODEL)
fallback_llm = create_llm(FALLBACK_MODEL)


def extract_text(response) -> str:

    content = response.content

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

    return str(content).strip()


def generate_with_langchain(prompt: str) -> str:

    for attempt in range(2):

        try:

            print(
                f"Gemini primary attempt {attempt + 1}: "
                f"{PRIMARY_MODEL}"
            )

            response = primary_llm.invoke(prompt)

            return extract_text(response)

        except Exception as error:

            print(
                f"Primary Gemini attempt {attempt + 1} failed:"
            )

            print(error)

            if attempt == 0:

                print(
                    "Retrying primary model in 3 seconds..."
                )

                time.sleep(3)

    print(
        f"Trying fallback model: {FALLBACK_MODEL}"
    )

    try:

        response = fallback_llm.invoke(prompt)

        return extract_text(response)

    except Exception as error:

        print("Fallback Gemini model failed:")

        print(error)

        raise RuntimeError(
            "Gemini is temporarily unavailable. "
            "Please try again in a moment."
        ) from error