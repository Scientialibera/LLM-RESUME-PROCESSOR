"""
Resume Processing Pipeline
Sequential workflow for extracting, summarizing, and sanitizing resumes.
"""

import os
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path

import tomli
import structlog
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential

from src.pipeline.extractor import extract_resume_data
from src.pipeline.summarizer import generate_summary
from src.pipeline.pii_remover import remove_pii
from src.pipeline.storage import ResumeStorage

logger = structlog.get_logger(__name__)


class ResumeProcessor:
    """
    Sequential pipeline for processing resumes.
    
    Pipeline: Extract -> Summarize -> Remove PII -> Store
    """
    
    def __init__(self, config_path: str = "config/agent.toml"):
        """Load configuration and initialize clients."""
        with open(config_path, "rb") as f:
            self.config = tomli.load(f)
        
        self._client: Optional[AzureOpenAI] = None
        self._storage: Optional[ResumeStorage] = None
        self._initialized = False
        
        logger.info("Pipeline created", name=self.config["app"]["name"])
    
    def _get_client(self) -> AzureOpenAI:
        """Get or create Azure OpenAI client."""
        if self._client is None:
            model_config = self.config["model"]
            endpoint = os.getenv(model_config["endpoint_env"])
            api_key = os.getenv(model_config.get("api_key_env", ""))
            
            if api_key:
                self._client = AzureOpenAI(
                    azure_endpoint=endpoint,
                    api_key=api_key,
                    api_version=model_config["api_version"]
                )
            else:
                credential = DefaultAzureCredential()
                self._client = AzureOpenAI(
                    azure_endpoint=endpoint,
                    azure_ad_token_provider=lambda: credential.get_token(
                        "https://cognitiveservices.azure.com/.default"
                    ).token,
                    api_version=model_config["api_version"]
                )
        return self._client
    
    def _get_storage(self) -> ResumeStorage:
        """Get or create storage client."""
        if self._storage is None:
            cosmos_config = self.config["cosmos_db"]
            endpoint = os.getenv(cosmos_config["endpoint_env"])
            self._storage = ResumeStorage(endpoint, cosmos_config)
        return self._storage
    
    @property
    def deployment(self) -> str:
        return self.config["model"]["deployment"]
    
    async def process(self, resume_text: str) -> Dict[str, Any]:
        """
        Run the complete processing pipeline.
        
        Args:
            resume_text: Raw resume text
            
        Returns:
            Processed resume data with extracted info, summary, and sanitized content
        """
        client = self._get_client()
        deployment = self.deployment
        
        logger.info("Starting pipeline", text_length=len(resume_text))
        
        # Step 1: Extract structured data
        logger.info("Step 1/3: Extracting data")
        extracted_data = extract_resume_data(client, deployment, resume_text)
        
        # Step 2: Generate summary
        logger.info("Step 2/3: Generating summary")
        summary = generate_summary(client, deployment, extracted_data)
        
        # Step 3: Remove PII from summary
        logger.info("Step 3/3: Removing PII")
        sanitized_summary = remove_pii(client, deployment, summary)
        
        # Combine results
        result = {
            **extracted_data,
            "summary": summary,
            "sanitized_summary": sanitized_summary
        }
        
        logger.info("Pipeline complete")
        return result
    
    async def process_and_store(
        self, 
        resume_id: str, 
        resume_text: str, 
        filename: str
    ) -> Dict[str, Any]:
        """
        Process resume and store in Cosmos DB.
        
        Args:
            resume_id: Unique identifier
            resume_text: Raw resume text
            filename: Original filename
            
        Returns:
            Stored document
        """
        storage = self._get_storage()
        
        # Update status
        await storage.update_status(resume_id, "processing")
        
        try:
            # Run pipeline
            processed_data = await self.process(resume_text)
            
            # Store result
            result = await storage.store(resume_id, filename, processed_data)
            await storage.update_status(resume_id, "completed")
            
            return result
            
        except Exception as e:
            await storage.update_status(resume_id, "failed", error=str(e))
            raise
    
    async def close(self):
        """Clean up resources."""
        if self._storage:
            await self._storage.close()


# Simple functional interface
def create_processor(config_path: str = "config/agent.toml") -> ResumeProcessor:
    """Create a resume processor instance."""
    return ResumeProcessor(config_path)
