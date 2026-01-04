"""
Resume Storage Tool
Manages resume data in Azure Cosmos DB.
"""

import os
from datetime import datetime
from typing import Dict, Any, List, Optional
import structlog
from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential

logger = structlog.get_logger(__name__)


class ResumeStorage:
    """Tool for storing and retrieving resumes from Cosmos DB."""
    
    def __init__(self, endpoint: str, config: Dict[str, Any]):
        """
        Initialize the storage client.
        
        Args:
            endpoint: Cosmos DB endpoint URL
            config: Configuration dictionary with database/container names
        """
        self.endpoint = endpoint
        self.database_name = config.get("database", "resume-processor")
        self.raw_container = config.get("raw_container", "raw-resumes")
        self.processed_container = config.get("processed_container", "processed-resumes")
        self._client: Optional[CosmosClient] = None
        self._database = None
    
    async def _get_client(self):
        """Get or create Cosmos DB client."""
        if self._client is None:
            credential = DefaultAzureCredential()
            self._client = CosmosClient(self.endpoint, credential=credential)
            self._database = self._client.get_database_client(self.database_name)
        return self._client
    
    async def _get_container(self, name: str):
        """Get a container client."""
        await self._get_client()
        return self._database.get_container_client(name)
    
    async def store(self, resume_id: str, filename: str, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store processed resume data.
        
        Args:
            resume_id: Unique resume identifier
            filename: Original filename
            processed_data: Processed resume data
            
        Returns:
            Stored document
        """
        logger.info("Storing processed resume", resume_id=resume_id)
        
        container = await self._get_container(self.processed_container)
        
        document = {
            "id": resume_id,
            "filename": filename,
            "upload_date": datetime.utcnow().isoformat(),
            "status": "completed",
            "processed_data": processed_data
        }
        
        result = await container.upsert_item(document)
        
        logger.info("Resume stored successfully", resume_id=resume_id)
        return result
    
    async def get(self, resume_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a resume by ID.
        
        Args:
            resume_id: Resume identifier
            
        Returns:
            Resume document or None if not found
        """
        logger.info("Fetching resume", resume_id=resume_id)
        
        # Try processed container first
        try:
            container = await self._get_container(self.processed_container)
            return await container.read_item(resume_id, partition_key=resume_id)
        except Exception:
            pass
        
        # Try raw container
        try:
            container = await self._get_container(self.raw_container)
            return await container.read_item(resume_id, partition_key=resume_id)
        except Exception:
            return None
    
    async def list(self, status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        List resumes with optional status filter.
        
        Args:
            status: Optional status filter
            limit: Maximum results to return
            
        Returns:
            List of resume documents
        """
        logger.info("Listing resumes", status=status, limit=limit)
        
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
    
    async def update_status(self, resume_id: str, status: str, error: Optional[str] = None):
        """
        Update resume processing status.
        
        Args:
            resume_id: Resume identifier
            status: New status value
            error: Optional error message
        """
        logger.info("Updating status", resume_id=resume_id, status=status)
        
        container = await self._get_container(self.raw_container)
        
        try:
            doc = await container.read_item(resume_id, partition_key=resume_id)
            doc["status"] = status
            if error:
                doc["error"] = error
            await container.upsert_item(doc)
        except Exception as e:
            logger.warning("Could not update status", resume_id=resume_id, error=str(e))
    
    async def delete(self, resume_id: str):
        """
        Delete a resume from all containers.
        
        Args:
            resume_id: Resume identifier
        """
        logger.info("Deleting resume", resume_id=resume_id)
        
        for container_name in [self.raw_container, self.processed_container]:
            try:
                container = await self._get_container(container_name)
                await container.delete_item(resume_id, partition_key=resume_id)
            except Exception:
                pass
    
    async def close(self):
        """Close the Cosmos DB client."""
        if self._client:
            await self._client.close()
            self._client = None
