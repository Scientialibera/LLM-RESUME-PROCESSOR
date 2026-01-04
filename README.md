# LLM Resume Processor

Enterprise-grade resume processing **pipeline** built with Azure OpenAI and Cosmos DB.

>  **Architecture Note**: This is a **deterministic pipeline**, not an agentic system.
> Agents are for autonomous decision-making; this is a sequential workflow.

## Pipeline Flow

\\\
Resume Upload  Extract Data  Generate Summary  Remove PII  Store Results
\\\

\\\mermaid
graph LR
    A[ Resume Upload] --> B[ Extract Data]
    B --> C[ Summarize]
    C --> D[ Remove PII]
    D --> E[ Store to Cosmos DB]
\\\

## Quick Start

\\\ash
# Install
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your Azure credentials

# Run API
python -m uvicorn src.api.main:app --reload
\\\

## Project Structure

\\\
 config/
    agent.toml          # Pipeline configuration (TOML)
 src/
    api/                 # FastAPI endpoints
       main.py
    pipeline/            # Processing workflow
        processor.py     # Main pipeline orchestrator
        extractor.py     # Resume data extraction
        summarizer.py    # Summary generation
        pii_remover.py   # PII redaction
        storage.py       # Cosmos DB storage
 frontend/                # React UI
 requirements.txt
\\\

## Pipeline Steps

| Step | Function | Description |
|------|----------|-------------|
| 1 | \xtract_resume_data()\ | Structured extraction via GPT function calling |
| 2 | \generate_summary()\ | Professional summary (250 words max) |
| 3 | \emove_pii()\ | Redact names, emails, phones, addresses |
| 4 | \ResumeStorage.store()\ | Persist to Cosmos DB |

## Configuration

All settings in \config/agent.toml\:

\\\	oml
[app]
name = \"resume-processor\"

[model]
provider = \"azure_openai\"
deployment = \"gpt-4o\"

[cosmos_db]
database = \"resume-processor\"

[workflow]
steps = [\"extract\", \"summarize\", \"remove_pii\", \"store\"]
\\\

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| \/api/upload\ | POST | Upload resume for processing |
| \/api/resume/{id}\ | GET | Get processed resume |
| \/api/resumes\ | GET | List all processed resumes |

## Environment Variables

\\\
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
COSMOS_DB_ENDPOINT=https://your-cosmos.documents.azure.com:443/
\\\

## Why Not Agents?

This is a **fixed pipeline** with deterministic steps:

| Approach | When to Use |
|----------|-------------|
| **Pipeline**  | Fixed sequence, no decisions needed |
| **Agent** | Dynamic routing, tool selection, multi-turn reasoning |

Resume processing always runs the same steps in order  Pipeline wins.

## License

MIT
