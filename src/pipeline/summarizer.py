"""
Resume Summarizer
Generates unbiased, extractive summaries.
"""

import json
from typing import Dict, Any
from openai import AzureOpenAI


def generate_summary(
    client: AzureOpenAI,
    deployment: str,
    resume_data: Dict[str, Any],
    max_words: int = 250
) -> str:
    """
    Generate an extractive summary of resume data.
    
    Args:
        client: Azure OpenAI client
        deployment: Model deployment name
        resume_data: Structured resume data
        max_words: Maximum word count
        
    Returns:
        Professional summary
    """
    prompt = f\"\"\"Summarize this resume using extractive summarization.

Guidelines:
- Use neutral pronouns (they/them)
- No filler words or padding
- Focus on qualifications and experience
- Maximum {max_words} words

Resume:
{json.dumps(resume_data, indent=2)}
\"\"\"
    
    response = client.chat.completions.create(
        model=deployment,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=500
    )
    
    return response.choices[0].message.content
