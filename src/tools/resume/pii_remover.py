"""
PII Remover Tool
Removes personally identifiable information from text using AI.
"""

import re
import structlog

logger = structlog.get_logger(__name__)


class PIIRemover:
    """Tool for removing PII from text content."""
    
    def __init__(self, client, deployment: str):
        """
        Initialize the PII remover.
        
        Args:
            client: Azure OpenAI client
            deployment: Model deployment name
        """
        self.client = client
        self.deployment = deployment
    
    async def remove(self, text: str) -> str:
        """
        Remove personally identifiable information from text.
        
        Args:
            text: Input text containing potential PII
            
        Returns:
            Sanitized text with PII redacted
        """
        logger.info("Removing PII", text_length=len(text))
        
        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=[
                {
                    "role": "system",
                    "content": \"\"\"You are a PII and bias removal expert. Remove all personally identifiable information from the text:

- Replace names with [NAME]
- Replace emails with [EMAIL]
- Replace phone numbers with [PHONE]
- Replace addresses with [ADDRESS]
- Replace dates of birth with [DOB]
- Replace gender-specific pronouns with neutral alternatives
- Use bracket notation [REDACTED] for other sensitive info

Preserve the meaning and professional content of the text.\"\"\"
                },
                {"role": "user", "content": text}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        sanitized = response.choices[0].message.content
        
        # Clean up extra whitespace
        sanitized = re.sub(r'\n+', ' ', sanitized).strip()
        
        logger.info(
            "PII removed",
            original_length=len(text),
            sanitized_length=len(sanitized)
        )
        
        return sanitized
