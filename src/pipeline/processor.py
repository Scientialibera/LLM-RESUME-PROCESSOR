"""Sequential resume-processing pipeline orchestration."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

import structlog
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI

from src.pipeline.extractor import extract_resume_data
from src.pipeline.pii_remover import remove_pii
from src.pipeline.storage import ResumeStorage
from src.pipeline.summarizer import generate_summary

logger = structlog.get_logger(__name__)


class ConfigurationError(ValueError):
    """Raised when pipeline configuration cannot be resolved safely."""


class ResumeProcessor:
    """Extract, summarize, reduce PII and optionally persist resume data."""

    def __init__(self, config_path: str = "config/agent.toml") -> None:
        path = Path(config_path)
        if not path.is_file():
            raise ConfigurationError(f"Configuration file not found: {path}")

        with path.open("rb") as handle:
            self.config = tomllib.load(handle)

        self._client: AzureOpenAI | None = None
        self._openai_credential: DefaultAzureCredential | None = None
        self._storage: ResumeStorage | None = None

        app_name = self.config.get("app", {}).get("name", "resume-processor")
        logger.info("Pipeline created", name=app_name)

    @staticmethod
    def _required_env(name: str) -> str:
        value = os.getenv(name)
        if not value or not value.strip():
            raise ConfigurationError(f"Required environment variable is not set: {name}")
        return value.strip()

    def _get_client(self) -> AzureOpenAI:
        """Create the Azure OpenAI client using API key or Entra ID."""
        if self._client is not None:
            return self._client

        model_config = self.config["model"]
        endpoint = self._required_env(model_config["endpoint_env"])
        api_key_env = model_config.get("api_key_env")
        api_key = os.getenv(api_key_env, "").strip() if api_key_env else ""

        common = {
            "azure_endpoint": endpoint,
            "api_version": model_config["api_version"],
        }

        if api_key:
            self._client = AzureOpenAI(api_key=api_key, **common)
        else:
            self._openai_credential = DefaultAzureCredential()
            token_provider = get_bearer_token_provider(
                self._openai_credential,
                "https://cognitiveservices.azure.com/.default",
            )
            self._client = AzureOpenAI(
                azure_ad_token_provider=token_provider,
                **common,
            )
        return self._client

    def _get_storage(self) -> ResumeStorage:
        """Create the Cosmos storage facade lazily."""
        if self._storage is None:
            cosmos_config = self.config["cosmos_db"]
            endpoint = self._required_env(cosmos_config["endpoint_env"])
            self._storage = ResumeStorage(endpoint, cosmos_config)
        return self._storage

    @property
    def deployment(self) -> str:
        deployment = self.config["model"].get("deployment", "").strip()
        if not deployment:
            raise ConfigurationError("model.deployment must be configured")
        return deployment

    async def process(self, resume_text: str) -> dict[str, Any]:
        """Run the in-memory processing pipeline."""
        if not resume_text or not resume_text.strip():
            raise ValueError("resume_text must not be empty")

        client = self._get_client()
        deployment = self.deployment
        normalized = resume_text.strip()

        logger.info("Starting pipeline", text_length=len(normalized))
        extracted_data = extract_resume_data(client, deployment, normalized)
        summary = generate_summary(client, deployment, extracted_data)
        sanitized_summary = remove_pii(client, deployment, summary)

        result = {
            **extracted_data,
            "summary": summary,
            "sanitized_summary": sanitized_summary,
        }
        logger.info("Pipeline complete")
        return result

    async def process_and_store(
        self,
        resume_id: str,
        resume_text: str,
        filename: str,
    ) -> dict[str, Any]:
        """Process one resume and store its processed document."""
        if not resume_id.strip():
            raise ValueError("resume_id must not be empty")
        if not filename.strip():
            raise ValueError("filename must not be empty")

        storage = self._get_storage()
        await storage.update_status(resume_id, "processing")

        try:
            processed_data = await self.process(resume_text)
            result = await storage.store(resume_id, filename, processed_data)
            await storage.update_status(resume_id, "completed")
            return result
        except Exception as exc:
            # Status persistence is best-effort here; preserve the original
            # processing exception if the status document does not exist.
            await storage.update_status(resume_id, "failed", error=str(exc))
            raise

    async def close(self) -> None:
        """Release owned Azure SDK resources."""
        if self._storage is not None:
            await self._storage.close()
            self._storage = None
        if self._client is not None:
            self._client.close()
            self._client = None
        if self._openai_credential is not None:
            self._openai_credential.close()
            self._openai_credential = None

    async def __aenter__(self) -> "ResumeProcessor":
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        await self.close()


def create_processor(config_path: str = "config/agent.toml") -> ResumeProcessor:
    """Create a configured resume processor."""
    return ResumeProcessor(config_path)
