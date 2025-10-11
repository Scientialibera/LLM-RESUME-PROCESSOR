"""
Resume processing service using Azure OpenAI.
"""

import json
import re
from typing import Dict, Any, List
import structlog

from backend.app.shared.schemas import RESUME_EXTRACTION_FUNCTION

logger = structlog.get_logger(__name__)


class ResumeProcessor:
    """Service for processing resumes with Azure OpenAI."""

    def __init__(self, aoai_client, cosmos_client):
        """Initialize the resume processor."""
        self.aoai_client = aoai_client
        self.cosmos_client = cosmos_client

    async def extract_resume_data(self, resume_text: str) -> Dict[str, Any]:
        """Extract structured data from resume text using OpenAI function calling."""
        logger.info("Extracting resume data", text_length=len(resume_text))

        messages = [
            {
                "role": "system",
                "content": """You are an AI NLP Resume Extractor to JSON. Your job is to fill the required fields on the function submit_application with information from provided Resume. Fields that require AI generation are indicated with GenAI and are REQUIRED. For example, you might need to extract skills as keywords based on the full Resume."""
            },
            {"role": "user", "content": f"Resume:\n{resume_text}"}
        ]

        response = await self.aoai_client.create_chat_completion(
            messages=messages,
            tools=[{"type": "function", "function": RESUME_EXTRACTION_FUNCTION}],
            tool_choice={"type": "function", "function": {"name": "submit_application"}}
        )

        # Extract function call arguments
        tool_calls = response["choices"][0]["message"].get("tool_calls")
        if not tool_calls:
            raise ValueError("No function call returned from OpenAI")

        arguments_str = tool_calls[0]["function"]["arguments"]
        extracted_data = json.loads(arguments_str)

        logger.info("Successfully extracted resume data",
                   has_education=bool(extracted_data.get("education")),
                   has_experience=bool(extracted_data.get("workExperience")))

        return extracted_data

    async def generate_summary(self, resume_data: Dict[str, Any], max_length: int = 250) -> str:
        """Generate an extractive summary of the resume."""
        logger.info("Generating resume summary", max_length=max_length)

        summary_prompt = f"""Summarize the following Resume using extractive summarization to remain unbiased.
Use neutral pronouns, do not use padding language. The length must be of {max_length} words.

Resume Data:
{json.dumps(resume_data, indent=2)}
"""

        messages = [
            {"role": "user", "content": summary_prompt}
        ]

        response = await self.aoai_client.create_chat_completion(
            messages=messages,
            temperature=0.5,
            max_tokens=500
        )

        summary = response["choices"][0]["message"]["content"]
        logger.info("Generated summary", length=len(summary))

        return summary

    async def remove_pii(self, text: str) -> str:
        """Remove personally identifiable information from text."""
        logger.info("Removing PII from text", text_length=len(text))

        messages = [
            {
                "role": "system",
                "content": "You are an expert PII and Bias remover bot. Remove any personally identifiable information and gender pronouns from the following text. Adopt the [] bracket removal style."
            },
            {"role": "user", "content": text}
        ]

        response = await self.aoai_client.create_chat_completion(
            messages=messages,
            temperature=0.3,
            max_tokens=1000
        )

        sanitized_text = response["choices"][0]["message"]["content"]
        logger.info("Removed PII from text",
                   original_length=len(text),
                   sanitized_length=len(sanitized_text))

        return sanitized_text

    def clean_text(self, text: str) -> str:
        """Clean text by removing extra whitespace and newlines."""
        return re.sub(r'\n+', ' ', text).strip()

    async def process_resume(self, resume_id: str, resume_text: str) -> Dict[str, Any]:
        """
        Complete resume processing pipeline.

        Args:
            resume_id: Unique identifier for the resume
            resume_text: Raw resume text

        Returns:
            Processed resume data with extracted information and summaries
        """
        logger.info("Starting resume processing", resume_id=resume_id)

        try:
            # Step 1: Extract structured data
            extracted_data = await self.extract_resume_data(resume_text)

            # Step 2: Generate summary
            summary = await self.generate_summary(extracted_data)

            # Step 3: Remove PII from summary
            sanitized_summary = await self.remove_pii(summary)

            # Step 4: Clean the sanitized summary
            cleaned_summary = self.clean_text(sanitized_summary)

            # Combine all data
            processed_data = {
                **extracted_data,
                "summary": summary,
                "sanitized_summary": cleaned_summary
            }

            logger.info("Successfully processed resume",
                       resume_id=resume_id,
                       has_summary=bool(summary))

            return processed_data

        except Exception as e:
            logger.error("Failed to process resume",
                        resume_id=resume_id,
                        error=str(e))
            raise

    async def process_and_store(self, resume_id: str, container_name: str = "raw-resumes"):
        """
        Process a resume from Cosmos DB and store results.

        Args:
            resume_id: ID of the resume in the raw-resumes container
            container_name: Source container name
        """
        logger.info("Processing and storing resume",
                   resume_id=resume_id,
                   container=container_name)

        try:
            # Get raw resume from Cosmos DB
            raw_resume = await self.cosmos_client.read_item(
                container_name=container_name,
                item_id=resume_id,
                partition_key=resume_id
            )

            if not raw_resume:
                raise ValueError(f"Resume {resume_id} not found in container {container_name}")

            # Update status to processing
            raw_resume["status"] = "processing"
            await self.cosmos_client.upsert_item(container_name, raw_resume)

            # Process the resume
            resume_text = raw_resume.get("raw_text", "")
            processed_data = await self.process_resume(resume_id, resume_text)

            # Store in processed container
            processed_resume = {
                "id": resume_id,
                "filename": raw_resume.get("filename"),
                "upload_date": raw_resume.get("upload_date"),
                "status": "completed",
                "processed_data": processed_data
            }

            await self.cosmos_client.upsert_item(
                "processed-resumes",
                processed_resume
            )

            # Update raw resume status
            raw_resume["status"] = "completed"
            await self.cosmos_client.upsert_item(container_name, raw_resume)

            logger.info("Successfully processed and stored resume", resume_id=resume_id)

            return processed_resume

        except Exception as e:
            logger.error("Failed to process and store resume",
                        resume_id=resume_id,
                        error=str(e))

            # Update status to failed
            try:
                raw_resume["status"] = "failed"
                raw_resume["error"] = str(e)
                await self.cosmos_client.upsert_item(container_name, raw_resume)
            except:
                pass

            raise
