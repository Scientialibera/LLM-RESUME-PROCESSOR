"""
Resume Storage
Cosmos DB operations for resume data.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
import structlog
from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential

logger = structlog.get_logger(__name__)


class ResumeStorage:
    """Cosmos DB storage for resumes."""
    
    def __init__(self, endpoint: str, config: Dict[str, Any]):
        self.endpoint = endpoint
        self.database_name = config.get("database", "resume-processor")
        self.raw_container = config.get("raw_container", "raw-resumes")
        self.processed_container = config.get("processed_container", "processed-resumes")
        self._client: Optional[CosmosClient] = None
        self._database = None
    
    async def _get_container(self, name: str):
        """Get a container client."""
        if self._client is None:
            credential = DefaultAzureCredential()
            self._client = CosmosClient(self.endpoint, credential=credential)
            self._database = self._client.get_database_client(self.database_name)
        return self._database.get_container_client(name)
    
    async def store(
        self, 
        resume_id: str, 
        filename: str, 
        processed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Store processed resume."""
        container = await self._get_container(self.processed_container)
        
        doc = {
            "id": resume_id,
            "filename": filename,
            "upload_date": datetime.utcnow().isoformat(),
            "status": "completed",
            "processed_data": processed_data
        }
        
        return await container.upsert_item(doc)
    
    async def get(self, resume_id: str) -> Optional[Dict[str, Any]]:
        """Get resume by ID."""
        for container_name in [self.processed_container, self.raw_container]:
            try:
                container = await self._get_container(container_name)
                return await container.read_item(resume_id, partition_key=resume_id)
            except Exception:
                continue
        return None
    
    async def list(self, status: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """List resumes."""
        container = await self._get_container(self.processed_container)
        
        query = "SELECT * FROM c"
        params = []
        if status:
            query += " WHERE c.status = @status"
            params = [{"name": "@status", "value": status}]
        query += f" ORDER BY c.upload_date DESC OFFSET 0 LIMIT {limit}"
        
        results = []
        async for item in container.query_items(query, parameters=params):
            results.append(item)
        return results
    
    async def update_status(self, resume_id: str, status: str, error: str = None):
        """Update resume status."""
        try:
            container = await self._get_container(self.raw_container)
            doc = await container.read_item(resume_id, partition_key=resume_id)
            doc["status"] = status
            if error:
                doc["error"] = error
            await container.upsert_item(doc)
        except Exception as e:
            logger.warning("Status update failed", resume_id=resume_id, error=str(e))
    
    async def delete(self, resume_id: str):
        """Delete resume from all containers."""
        for name in [self.raw_container, self.processed_container]:
            try:
                container = await self._get_container(name)
                await container.delete_item(resume_id, partition_key=resume_id)
            except Exception:
                pass
    
    async def close(self):
        """Close client."""
        if self._client:
            await self._client.close()
