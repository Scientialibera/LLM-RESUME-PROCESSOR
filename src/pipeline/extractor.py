"""
Resume Data Extractor
Extracts structured information using OpenAI function calling.
"""

import json
from typing import Dict, Any
from openai import AzureOpenAI

# Function schema for structured extraction
EXTRACTION_SCHEMA = {
    "name": "extract_resume",
    "description": "Extract structured data from resume. Use 'N/A' for missing fields.",
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
                "description": "Skills extracted as searchable keywords",
                "type": "array",
                "items": {"type": "string"}
            },
            "ai_generated_roles": {
                "description": "10 potential job roles based on experience",
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "required": ["personalInformation", "contactInformation", "education", 
                     "workExperience", "skills_keywords", "ai_generated_roles"]
    }
}


def extract_resume_data(
    client: AzureOpenAI, 
    deployment: str, 
    resume_text: str
) -> Dict[str, Any]:
    """
    Extract structured data from resume text.
    
    Args:
        client: Azure OpenAI client
        deployment: Model deployment name
        resume_text: Raw resume text
        
    Returns:
        Structured resume data
    """
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {
                "role": "system",
                "content": "Extract structured data from the resume. Use 'N/A' for missing fields."
            },
            {"role": "user", "content": f"Resume:\n{resume_text}"}
        ],
        tools=[{"type": "function", "function": EXTRACTION_SCHEMA}],
        tool_choice={"type": "function", "function": {"name": "extract_resume"}},
        temperature=0.3
    )
    
    tool_calls = response.choices[0].message.tool_calls
    if not tool_calls:
        raise ValueError("No extraction result returned")
    
    return json.loads(tool_calls[0].function.arguments)
