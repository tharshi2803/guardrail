"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central config — reads from .env file or environment."""

    ANTHROPIC_API_KEY: str = ""
    BACKEND: str = "claude"
    CHROMA_PATH: str = "./chroma_db"
    CHROMA_COLLECTION: str = "healthcare_docs"
    RULES_FILE: str = "./guardrails.yaml"
    GUARDRAIL_USER: str = "guardrailuser"
    GUARDRAIL_PASSWORD: str = "tharshika123$$"
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64
    TOP_K: int = 10
    LLM_MODEL: str = "claude-sonnet-5"
    CLASSIFIER_MODEL: str = "claude-haiku-4-5"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
