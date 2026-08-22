"""PII reduction helpers for generated resume summaries.

The deterministic pass removes common high-confidence identifiers before the
text is sent to the model for broader contextual redaction. This is a defence
in depth measure, not a guarantee that all PII has been removed.
"""

from __future__ import annotations

import re

from openai import AzureOpenAI

_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)")
_DOB = re.compile(
    r"\b(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b"
)


def _pre_redact(text: str) -> str:
    redacted = _EMAIL.sub("[EMAIL]", text)
    redacted = _PHONE.sub("[PHONE]", redacted)
    return _DOB.sub("[DATE]", redacted)


def remove_pii(client: AzureOpenAI, deployment: str, text: str) -> str:
    """Reduce PII in text using deterministic and contextual redaction.

    The output must still be treated as potentially sensitive. Downstream
    systems should apply their own privacy controls before release or logging.
    """
    if not text or not text.strip():
        return ""
    if not deployment.strip():
        raise ValueError("deployment must not be empty")

    pre_redacted = _pre_redact(text.strip())
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {
                "role": "system",
                "content": (
                    "Redact personally identifiable information from the supplied text. "
                    "Replace person names with [NAME], email addresses with [EMAIL], "
                    "phone numbers with [PHONE], street/postal addresses with [ADDRESS] "
                    "and dates of birth with [DOB]. Preserve professional experience, "
                    "skills and factual meaning. Do not add new information."
                ),
            },
            {"role": "user", "content": pre_redacted},
        ],
        temperature=0,
    )

    result = response.choices[0].message.content
    if not result:
        raise ValueError("PII reduction returned no content")

    # Run deterministic patterns again in case the model reproduced an identifier.
    return re.sub(r"\s+", " ", _pre_redact(result)).strip()
