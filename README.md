# LLM Resume Processor

Deterministic resume-processing pipeline built around Azure OpenAI and Azure Cosmos DB. The workflow extracts structured resume data, generates a professional summary, reduces personally identifiable information in that summary and can persist the processed result.

This is a fixed application workflow rather than an autonomous agent. Processing order is controlled by application code.

## Pipeline

```text
resume text
    |
    v
structured extraction
    |
    v
summary generation
    |
    v
PII reduction
    |
    v
optional Cosmos DB persistence
```

Core implementation:

```text
src/pipeline/
  extractor.py       structured extraction
  summarizer.py      summary generation
  pii_remover.py     deterministic + model-assisted PII reduction
  storage.py         asynchronous Cosmos DB access
  processor.py       orchestration and client lifecycle
config/
  agent.toml         pipeline and Azure resource configuration
```

## Privacy boundary

Resume data is sensitive. The PII stage is a reduction mechanism, not a compliance guarantee. It performs deterministic redaction for common email, phone and date patterns before and after contextual model-based redaction, but downstream systems must still treat the result as potentially sensitive.

Do not use `sanitized_summary` as the only control before public release, analytics export or logging. Apply the organization's privacy review, retention policy, access controls and data-loss-prevention controls independently.

## Local setup

Python 3.11 or later is required.

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -e ".[dev]"
cp .env.example .env
```

Configure the Azure endpoints/deployments referenced by `config/agent.toml`. Microsoft Entra ID / managed identity is preferred; an API-key environment variable is supported when configured explicitly.

## Programmatic use

```python
import asyncio

from src.pipeline.processor import ResumeProcessor


async def main() -> None:
    async with ResumeProcessor("config/agent.toml") as processor:
        result = await processor.process("resume text")
        print(result["sanitized_summary"])


asyncio.run(main())
```

Use `process_and_store(...)` when Cosmos persistence is required.

## Operational requirements

- Keep raw resumes and processed documents behind least-privilege access controls.
- Use managed identity where the hosting platform supports it.
- Do not log resume bodies, generated summaries or extracted personal fields.
- Configure retention and deletion rules for both raw and processed containers.
- Validate uploaded file type and size before extracting text in an API/UI layer.
- Apply malware scanning to untrusted uploads before content processing.
- Treat model outputs as untrusted application data and validate structured results before downstream use.
- Monitor model/API failures separately from document-level validation failures.

## Development

```bash
ruff check src tests
pytest
```

The project does not include CI/CD in this repository. Deployment-specific identity, networking, secret management and observability should be defined by the owning platform environment.
