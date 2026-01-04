"""
Resume Data Extractor Tool
Extracts structured information from resume text using OpenAI function calling.
"""

import json
from typing import Dict, Any
import structlog

logger = structlog.get_logger(__name__)

# OpenAI function schema for resume extraction
RESUME_EXTRACTION_FUNCTION = {
    "name": "submit_application",
    "description": "Extract structured data from resume. Use 'N/A' if information not found.",
    "parameters": {
        "type": "object",
        "properties": {
            "personalInformation": {
                "type": "object",
                "properties": {
                    "firstName": {"type": "string"},
                    "lastName": {"type": "string"},
                    "middleName": {"type": "string"},
                    "dateOfBirth": {"type": "string"}
                },
                "required": ["firstName", "lastName"]
            },
            "contactInformation": {
                "type": "object",
                "properties": {
                    "email": {"type": "string"},
                    "phone": {"type": "string"},
                    "address": {
                        "type": "object",
                        "properties": {
                            "street": {"type": "string"},
                            "city": {"type": "string"},
                            "state": {"type": "string"},
                            "zip": {"type": "string"}
                        }
                    }
                }
            },
            "education": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "institution": {"type": "string"},
                        "degree": {"type": "string"},
                        "fieldOfStudy": {"type": "string"},
                        "graduationDate": {"type": "string"}
                    }
                }
            },
            "workExperience": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "employer": {"type": "string"},
                        "position": {"type": "string"},
                        "startDate": {"type": "string"},
                        "endDate": {"type": "string"},
                        "responsibilities": {"type": "string"}
                    }
                }
            },
            "skills": {"type": "array", "items": {"type": "string"}},
            "skills_keywords": {
                "description": "Extract skills as keywords",
                "type": "array",
                "items": {"type": "string"}
            },
            "ai_generated_roles": {
                "description": "Generate 10 possible roles based on experience",
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "required": ["personalInformation", "contactInformation", "education", "workExperience", "skills_keywords", "ai_generated_roles"]
    }
}


class ResumeExtractor:
    """Tool for extracting structured data from resumes using OpenAI function calling."""
    
    def __init__(self, client, deployment: str):
        """
        Initialize the extractor.
        
        Args:
            client: Azure OpenAI client
            deployment: Model deployment name
        """
        self.client = client
        self.deployment = deployment
    
    async def extract(self, resume_text: str) -> Dict[str, Any]:
        """
        Extract structured data from resume text.
        
        Args:
            resume_text: Raw resume text content
            
        Returns:
            Dictionary with extracted resume data
        """
        logger.info("Extracting resume data", text_length=len(resume_text))
        
        messages = [
            {
                "role": "system",
                "content": "You are an AI Resume Extractor. Extract structured data from the resume using the provided function. Use 'N/A' for missing fields."
            },
            {"role": "user", "content": f"Resume:\n{resume_text}"}
        ]
        
        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=messages,
            tools=[{"type": "function", "function": RESUME_EXTRACTION_FUNCTION}],
            tool_choice={"type": "function", "function": {"name": "submit_application"}}
        )
        
        # Extract function call arguments
        tool_calls = response.choices[0].message.tool_calls
        if not tool_calls:
            raise ValueError("No function call returned from OpenAI")
        
        arguments_str = tool_calls[0].function.arguments
        extracted_data = json.loads(arguments_str)
        
        logger.info(
            "Resume data extracted",
            has_education=bool(extracted_data.get("education")),
            has_experience=bool(extracted_data.get("workExperience")),
            skills_count=len(extracted_data.get("skills_keywords", []))
        )
        
        return extracted_data
