import os
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()  # reads your .env file

def get_llm():
    model_name = os.getenv("MODEL", "gemini-2.5-flash")
    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=0.2,  # low = more predictable answers
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )