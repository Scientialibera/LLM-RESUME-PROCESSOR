"""
Configuration settings for the resume processor application.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class AzureOpenAISettings(BaseSettings):
    """Azure OpenAI service settings."""
    endpoint: str
    chat_deployment: str = "gpt-4"
    embedding_deployment: str = "text-embedding-ada-002"
    api_version: str = "2024-02-15-preview"
    temperature: float = 0.5
    max_tokens: int = 4000

    class Config:
        env_prefix = "AZURE_OPENAI_"


class CosmosDBSettings(BaseSettings):
    """Azure Cosmos DB settings."""
    endpoint: str
    database_name: str = "resume-processor"
    raw_resumes_container: str = "raw-resumes"
    processed_resumes_container: str = "processed-resumes"

    class Config:
        env_prefix = "COSMOS_DB_"


class BlobStorageSettings(BaseSettings):
    """Azure Blob Storage settings."""
    account_url: str
    container_name: str = "resumes"

    class Config:
        env_prefix = "BLOB_STORAGE_"


class EventGridSettings(BaseSettings):
    """Azure Event Grid settings."""
    topic_endpoint: Optional[str] = None
    topic_key: Optional[str] = None
    webhook_secret: Optional[str] = None

    class Config:
        env_prefix = "EVENT_GRID_"


class AppSettings(BaseSettings):
    """Application settings."""
    app_name: str = "Resume Processor API"
    version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    cors_origins: list = ["http://localhost:3000", "http://localhost:5173"]
    log_level: str = "INFO"

    # Azure settings
    azure_openai: AzureOpenAISettings
    cosmos_db: CosmosDBSettings
    blob_storage: BlobStorageSettings
    event_grid: EventGridSettings

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> AppSettings:
    """Get application settings singleton."""
    return AppSettings(
        azure_openai=AzureOpenAISettings(),
        cosmos_db=CosmosDBSettings(),
        blob_storage=BlobStorageSettings(),
        event_grid=EventGridSettings()
    )
