import os
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()  # reads your .env file

def get_llm():
    # This gives you a connection to Gemini 1.5 Pro
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-pro",
        temperature=0.2,  # low = more predictable answers
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )