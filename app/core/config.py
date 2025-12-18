from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "GameBrain Backend"
    
    # LLM Settings
    OLLAMA_BASE_URL: str = "http://llm:11434"
    OLLAMA_MODEL: str = "qwen2.5:0.5b-instruct"
    
    # Twitch / IGDB Settings
    TWITCH_CLIENT_ID: str = ""
    TWITCH_CLIENT_SECRET: str = ""
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings():
    return Settings()
