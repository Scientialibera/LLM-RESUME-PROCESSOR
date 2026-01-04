"""
PII Remover
Removes personally identifiable information from text.
"""

import re
from openai import AzureOpenAI


def remove_pii(client: AzureOpenAI, deployment: str, text: str) -> str:
    """
    Remove personally identifiable information from text.
    
    Args:
        client: Azure OpenAI client
        deployment: Model deployment name
        text: Input text with potential PII
        
    Returns:
        Sanitized text
    """
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {
                "role": "system",
                "content": \"\"\"Remove all PII from the text:
- Names -> [NAME]
- Emails -> [EMAIL]  
- Phone numbers -> [PHONE]
- Addresses -> [ADDRESS]
- Dates of birth -> [DOB]
- Replace gendered pronouns with neutral ones

Preserve professional content.\"\"\"
            },
            {"role": "user", "content": text}
        ],
        temperature=0.3,
        max_tokens=1000
    )
    
    result = response.choices[0].message.content
    
    # Clean whitespace
    return re.sub(r'\n+', ' ', result).strip()
