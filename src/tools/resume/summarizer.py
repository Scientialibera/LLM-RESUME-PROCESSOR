"""
Resume Summarizer Tool
Generates unbiased, extractive summaries of resumes.
"""

import json
from typing import Dict, Any
import structlog

logger = structlog.get_logger(__name__)


class ResumeSummarizer:
    """Tool for generating professional resume summaries."""
    
    def __init__(self, client, deployment: str):
        """
        Initialize the summarizer.
        
        Args:
            client: Azure OpenAI client
            deployment: Model deployment name
        """
        self.client = client
        self.deployment = deployment
    
    async def summarize(self, resume_data: Dict[str, Any], max_length: int = 250) -> str:
        """
        Generate an extractive summary of resume data.
        
        Args:
            resume_data: Structured resume data from extraction
            max_length: Maximum word count for summary
            
        Returns:
            Professional summary string
        """
        logger.info("Generating resume summary", max_length=max_length)
        
        prompt = f\"\"\"Summarize the following resume using extractive summarization to remain unbiased.

Guidelines:
- Use neutral pronouns (they/them)
- No padding language or filler words
- Focus on qualifications, skills, and experience
- Maximum {max_length} words

Resume Data:
{json.dumps(resume_data, indent=2)}
\"\"\"
        
        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=500
        )
        
        summary = response.choices[0].message.content
        
        logger.info("Summary generated", word_count=len(summary.split()))
        
        return summary
