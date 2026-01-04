"""
Resume Processor Agent - Orchestrator Main Module
Enterprise-grade AI-powered resume processing using Microsoft Agent Framework patterns.
"""

import os
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List

import tomli
import structlog
from azure.identity import DefaultAzureCredential
from openai import AzureOpenAI

from src.tools.resume.extractor import ResumeExtractor
from src.tools.resume.summarizer import ResumeSummarizer
from src.tools.resume.pii_remover import PIIRemover
from src.tools.resume.storage import ResumeStorage

logger = structlog.get_logger(__name__)


class AgentConfig:
    """Configuration loaded from agent.toml."""
    
    def __init__(self, config_path: str = "config/agent.toml"):
        with open(config_path, "rb") as f:
            self._config = tomli.load(f)
        
        self.agent = self._config.get("agent", {})
        self.model = self._config.get("model", {})
        self.tools = self._config.get("tools", [])
        self.workflows = self._config.get("workflows", [])
        self.cosmos_db = self._config.get("cosmos_db", {})
        
        # Load system prompt
        prompt_file = self._config.get("system_prompt", {}).get("file")
        if prompt_file and Path(prompt_file).exists():
            self.system_prompt = Path(prompt_file).read_text()
        else:
            self.system_prompt = "You are a helpful resume processing assistant."
    
    @property
    def name(self) -> str:
        return self.agent.get("name", "ResumeProcessorAgent")
    
    @property
    def version(self) -> str:
        return self.agent.get("version", "1.0.0")


class ResumeProcessorAgent:
    """
    Enterprise-grade Resume Processing Agent.
    
    Uses Microsoft Agent Framework patterns for tool orchestration
    and Azure OpenAI for intelligent processing.
    """
    
    def __init__(self, config_path: str = "config/agent.toml"):
        """Initialize the agent with configuration."""
        self.config = AgentConfig(config_path)
        self._client: Optional[AzureOpenAI] = None
        self._tools: Dict[str, Any] = {}
        self._initialized = False
        
        logger.info(
            "Agent created",
            name=self.config.name,
            version=self.config.version,
            tool_count=len(self.config.tools)
        )
    
    async def initialize(self):
        """Initialize Azure OpenAI client and tools."""
        if self._initialized:
            return
        
        # Initialize Azure OpenAI
        endpoint = os.getenv(self.config.model.get("endpoint_env", "AZURE_OPENAI_ENDPOINT"))
        api_key = os.getenv(self.config.model.get("api_key_env", "AZURE_OPENAI_API_KEY"))
        
        if endpoint and api_key:
            self._client = AzureOpenAI(
                azure_endpoint=endpoint,
                api_key=api_key,
                api_version=self.config.model.get("api_version", "2024-12-01-preview")
            )
        elif endpoint:
            # Use managed identity
            credential = DefaultAzureCredential()
            self._client = AzureOpenAI(
                azure_endpoint=endpoint,
                azure_ad_token_provider=lambda: credential.get_token(
                    "https://cognitiveservices.azure.com/.default"
                ).token,
                api_version=self.config.model.get("api_version", "2024-12-01-preview")
            )
        else:
            raise ValueError("AZURE_OPENAI_ENDPOINT environment variable required")
        
        # Initialize tools
        await self._load_tools()
        
        self._initialized = True
        logger.info("Agent initialized", tools_loaded=len(self._tools))
    
    async def _load_tools(self):
        """Load tools from configuration."""
        # Get Cosmos DB config
        cosmos_endpoint = os.getenv(self.config.cosmos_db.get("endpoint_env", "COSMOS_DB_ENDPOINT"))
        
        # Initialize tool instances
        self._tools["extract_resume_data"] = ResumeExtractor(self._client, self.config.model.get("deployment", "gpt-4o"))
        self._tools["generate_summary"] = ResumeSummarizer(self._client, self.config.model.get("deployment", "gpt-4o"))
        self._tools["remove_pii"] = PIIRemover(self._client, self.config.model.get("deployment", "gpt-4o"))
        self._tools["storage"] = ResumeStorage(cosmos_endpoint, self.config.cosmos_db)
        
        logger.info("Tools loaded", tools=list(self._tools.keys()))
    
    async def process_resume(self, resume_id: str, resume_text: str) -> Dict[str, Any]:
        """
        Process a resume through the complete pipeline.
        
        Args:
            resume_id: Unique identifier for the resume
            resume_text: Raw resume text content
            
        Returns:
            Processed resume data with extracted info, summary, and sanitized content
        """
        await self.initialize()
        
        logger.info("Processing resume", resume_id=resume_id, text_length=len(resume_text))
        
        try:
            # Step 1: Extract structured data
            extractor = self._tools["extract_resume_data"]
            extracted_data = await extractor.extract(resume_text)
            
            # Step 2: Generate summary
            summarizer = self._tools["generate_summary"]
            summary = await summarizer.summarize(extracted_data)
            
            # Step 3: Remove PII
            pii_remover = self._tools["remove_pii"]
            sanitized_summary = await pii_remover.remove(summary)
            
            # Combine results
            processed_data = {
                **extracted_data,
                "summary": summary,
                "sanitized_summary": sanitized_summary
            }
            
            logger.info("Resume processed successfully", resume_id=resume_id)
            return processed_data
            
        except Exception as e:
            logger.error("Resume processing failed", resume_id=resume_id, error=str(e))
            raise
    
    async def process_and_store(self, resume_id: str, raw_text: str, filename: str) -> Dict[str, Any]:
        """
        Process a resume and store results in Cosmos DB.
        
        Args:
            resume_id: Unique identifier
            raw_text: Raw resume text
            filename: Original filename
            
        Returns:
            Stored resume document
        """
        await self.initialize()
        
        storage = self._tools["storage"]
        
        # Update status to processing
        await storage.update_status(resume_id, "processing")
        
        try:
            # Process the resume
            processed_data = await self.process_resume(resume_id, raw_text)
            
            # Store processed result
            result = await storage.store(resume_id, filename, processed_data)
            
            # Update raw resume status
            await storage.update_status(resume_id, "completed")
            
            return result
            
        except Exception as e:
            await storage.update_status(resume_id, "failed", error=str(e))
            raise
    
    async def chat(self, message: str) -> str:
        """
        Send a message to the agent for processing.
        
        Args:
            message: User message
            
        Returns:
            Agent response
        """
        await self.initialize()
        
        response = self._client.chat.completions.create(
            model=self.config.model.get("deployment", "gpt-4o"),
            messages=[
                {"role": "system", "content": self.config.system_prompt},
                {"role": "user", "content": message}
            ],
            temperature=self.config.model.get("temperature", 0.3),
            max_tokens=self.config.model.get("max_tokens", 4096)
        )
        
        return response.choices[0].message.content
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get OpenAI-compatible tool definitions."""
        definitions = []
        for tool_config in self.config.tools:
            definitions.append({
                "type": "function",
                "function": {
                    "name": tool_config["name"],
                    "description": tool_config["description"],
                    "parameters": {"type": "object", "properties": {}}
                }
            })
        return definitions


# Convenience function for direct usage
async def create_agent(config_path: str = "config/agent.toml") -> ResumeProcessorAgent:
    """Create and initialize a ResumeProcessorAgent."""
    agent = ResumeProcessorAgent(config_path)
    await agent.initialize()
    return agent


if __name__ == "__main__":
    async def main():
        agent = await create_agent()
        response = await agent.chat("What can you help me with?")
        print(response)
    
    asyncio.run(main())
