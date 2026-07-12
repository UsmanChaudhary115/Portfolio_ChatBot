import os
import logging
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

logger = logging.getLogger("portfolio-chatbot")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


def get_response(prompt_or_messages: str | list[dict], model: str | None = None, temperature: float = 0.4, max_tokens: int = 400) -> str:
    if not client:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    selected_model = model or GROQ_MODEL

    if isinstance(prompt_or_messages, str):
        messages = [{"role": "user", "content": prompt_or_messages}]
    else:
        messages = prompt_or_messages

    try:
        response = client.chat.completions.create(
            model=selected_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error("Groq API completion error: %s", e)
        raise