from pydantic import BaseSettings

class Settings(BaseSettings):
    index_api_url: str = "http://localhost:8000"  # default fallback

    class Config:
        env_file = ".env"  # tells pydantic to look here

# shared singleton settings object
settings = Settings()