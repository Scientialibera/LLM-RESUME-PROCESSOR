"""Asynchronous Cosmos DB storage for processed resume data."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog
from azure.cosmos.aio import CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from azure.identity.aio import DefaultAzureCredential

logger = structlog.get_logger(__name__)


class ResumeStorage:
    """Cosmos DB storage facade for raw and processed resume documents."""

    def __init__(self, endpoint: str, config: dict[str, Any]) -> None:
        if not endpoint or not endpoint.strip():
            raise ValueError("Cosmos DB endpoint is required")

        self.endpoint = endpoint.strip()
        self.database_name = config.get("database", "resume-processor")
        self.raw_container = config.get("raw_container", "raw-resumes")
        self.processed_container = config.get("processed_container", "processed-resumes")
        self._credential: DefaultAzureCredential | None = None
        self._client: CosmosClient | None = None
        self._database = None

    async def _get_container(self, name: str):
        """Return a container client, initializing shared SDK clients lazily."""
        if self._client is None:
            self._credential = DefaultAzureCredential()
            self._client = CosmosClient(self.endpoint, credential=self._credential)
            self._database = self._client.get_database_client(self.database_name)
        return self._database.get_container_client(name)

    async def store(
        self,
        resume_id: str,
        filename: str,
        processed_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Upsert a processed resume document."""
        if not resume_id.strip():
            raise ValueError("resume_id must not be empty")
        if not filename.strip():
            raise ValueError("filename must not be empty")

        container = await self._get_container(self.processed_container)
        document = {
            "id": resume_id,
            "filename": filename,
            "upload_date": datetime.now(timezone.utc).isoformat(),
            "status": "completed",
            "processed_data": processed_data,
        }
        return await container.upsert_item(document)

    async def get(self, resume_id: str) -> dict[str, Any] | None:
        """Get a resume by ID from the processed or raw container."""
        if not resume_id.strip():
            raise ValueError("resume_id must not be empty")

        for container_name in (self.processed_container, self.raw_container):
            container = await self._get_container(container_name)
            try:
                return await container.read_item(resume_id, partition_key=resume_id)
            except CosmosResourceNotFoundError:
                continue
        return None

    async def list(
        self,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List recent processed resumes with an optional status filter."""
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")

        container = await self._get_container(self.processed_container)
        query = "SELECT * FROM c"
        parameters: list[dict[str, Any]] = []
        if status:
            query += " WHERE c.status = @status"
            parameters.append({"name": "@status", "value": status})
        query += f" ORDER BY c.upload_date DESC OFFSET 0 LIMIT {limit:d}"

        results: list[dict[str, Any]] = []
        async for item in container.query_items(query, parameters=parameters):
            results.append(item)
        return results

    async def update_status(
        self,
        resume_id: str,
        status: str,
        error: str | None = None,
    ) -> bool:
        """Update the raw resume status when the raw document exists."""
        if not resume_id.strip() or not status.strip():
            raise ValueError("resume_id and status must not be empty")

        container = await self._get_container(self.raw_container)
        try:
            document = await container.read_item(resume_id, partition_key=resume_id)
        except CosmosResourceNotFoundError:
            logger.info("Raw status document not found", resume_id=resume_id, status=status)
            return False

        document["status"] = status
        if error:
            document["error"] = error[:2000]
        elif "error" in document:
            document.pop("error")
        await container.upsert_item(document)
        return True

    async def delete(self, resume_id: str) -> None:
        """Delete a resume from both containers; missing records are ignored."""
        if not resume_id.strip():
            raise ValueError("resume_id must not be empty")

        for name in (self.raw_container, self.processed_container):
            container = await self._get_container(name)
            try:
                await container.delete_item(resume_id, partition_key=resume_id)
            except CosmosResourceNotFoundError:
                continue

    async def close(self) -> None:
        """Close Cosmos and credential clients."""
        if self._client is not None:
            await self._client.close()
            self._client = None
        if self._credential is not None:
            await self._credential.close()
            self._credential = None
        self._database = None

    async def __aenter__(self) -> "ResumeStorage":
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        await self.close()
