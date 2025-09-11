from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from app.core.config import settings

def get_model(model_type="openrouter"):
    if model_type == "ollama":
        return ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_URL,
            temperature=0,
            num_predict=500
        )
    elif model_type == "openrouter":
        return ChatOpenAI(
            model="deepseek/deepseek-chat-v3.1:free",
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY,
            temperature=0,
            max_tokens=500,
        )
    elif model_type == "gemini":
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0,
            max_tokens=500,
        )
    elif model_type == "groq":
        return ChatGroq(
            model="openai/gpt-oss-120b",
            groq_api_key=settings.GROQ_API_KEY,
            temperature=0,
            max_tokens=500,
        )
    else:
        raise ValueError(f"Unknown model type: {model_type}")
