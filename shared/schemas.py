"""
Data models and schemas for resume processing.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class Address(BaseModel):
    """Address information."""
    street: str
    city: str
    state: str
    zip: str


class ContactInformation(BaseModel):
    """Contact information."""
    email: str
    phone: str
    address: Address


class PersonalInformation(BaseModel):
    """Personal information."""
    firstName: str
    lastName: str
    middleName: Optional[str] = "N/A"
    dateOfBirth: Optional[str] = "N/A"


class Education(BaseModel):
    """Education entry."""
    institution: str
    degree: str
    fieldOfStudy: Optional[str] = "N/A"
    graduationDate: str


class WorkExperience(BaseModel):
    """Work experience entry."""
    employer: str
    position: str
    startDate: str
    endDate: Optional[str] = "Present"
    responsibilities: Optional[str] = "N/A"


class Reference(BaseModel):
    """Reference information."""
    name: str
    relationship: str
    contact: dict


class ProcessedResume(BaseModel):
    """Complete processed resume data."""
    personalInformation: PersonalInformation
    contactInformation: ContactInformation
    education: List[Education]
    workExperience: List[WorkExperience]
    skills: List[str]
    skills_keywords: List[str]
    ai_generated_roles: List[str]
    references: Optional[List[Reference]] = []
    summary: Optional[str] = None
    sanitized_summary: Optional[str] = None


class ResumeDocument(BaseModel):
    """Resume document stored in Cosmos DB."""
    id: str
    filename: str
    upload_date: datetime = Field(default_factory=datetime.utcnow)
    status: str = "pending"  # pending, processing, completed, failed
    raw_text: Optional[str] = None
    processed_data: Optional[ProcessedResume] = None
    error: Optional[str] = None


class ResumeUploadResponse(BaseModel):
    """Response for resume upload."""
    id: str
    filename: str
    status: str
    message: str


class ResumeListResponse(BaseModel):
    """Response for listing resumes."""
    resumes: List[dict]
    total: int


class ResumeSearchRequest(BaseModel):
    """Request for searching resumes."""
    query: str
    top_k: int = 5


class ResumeSearchResult(BaseModel):
    """Search result for a resume."""
    id: str
    name: str
    summary: str
    score: float


# OpenAI function schema for resume extraction
RESUME_EXTRACTION_FUNCTION = {
    "name": "submit_application",
    "description": "Use to submit a job application. Fill with 'N/A' if information not found in Applicant Resume.",
    "parameters": {
        "type": "object",
        "properties": {
            "personalInformation": {
                "type": "object",
                "properties": {
                    "firstName": {"type": "string"},
                    "lastName": {"type": "string"},
                    "middleName": {"type": "string"},
                    "dateOfBirth": {"type": "string", "format": "date"}
                },
                "required": ["firstName", "lastName"]
            },
            "contactInformation": {
                "type": "object",
                "properties": {
                    "email": {"type": "string", "format": "email"},
                    "phone": {"type": "string"},
                    "address": {
                        "type": "object",
                        "properties": {
                            "street": {"type": "string"},
                            "city": {"type": "string"},
                            "state": {"type": "string"},
                            "zip": {"type": "string"}
                        },
                        "required": ["street", "city", "state", "zip"]
                    }
                },
                "required": ["email", "phone", "address"]
            },
            "education": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "institution": {"type": "string"},
                        "degree": {"type": "string"},
                        "fieldOfStudy": {"type": "string"},
                        "graduationDate": {"type": "string", "format": "date"}
                    },
                    "required": ["institution", "degree", "graduationDate"]
                }
            },
            "workExperience": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "employer": {"type": "string"},
                        "position": {"type": "string"},
                        "startDate": {"type": "string", "format": "date"},
                        "endDate": {"type": "string", "format": "date"},
                        "responsibilities": {"type": "string"}
                    },
                    "required": ["employer", "position", "startDate"]
                }
            },
            "skills": {
                "type": "array",
                "items": {"type": "string"}
            },
            "skills_keywords": {
                "description": "REQUIRED GenAI Field - if Skills not keywords, insert array of keyword skills separated by comma",
                "type": "array",
                "items": {"type": "string"}
            },
            "ai_generated_roles": {
                "description": "REQUIRED GenAI Field - generate a list of 10 possible roles person could do based on experience and skills",
                "type": "array",
                "items": {"type": "string"}
            },
            "references": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "relationship": {"type": "string"},
                        "contact": {
                            "type": "object",
                            "properties": {
                                "email": {"type": "string", "format": "email"},
                                "phone": {"type": "string"}
                            },
                            "required": ["email", "phone"]
                        }
                    },
                    "required": ["name", "relationship", "contact"]
                }
            }
        },
        "required": ["personalInformation", "contactInformation", "education", "workExperience", "skills_keywords", "ai_generated_roles"]
    }
}
