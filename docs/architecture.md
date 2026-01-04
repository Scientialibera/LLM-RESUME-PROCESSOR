# Architecture

## Pipeline Pattern

This project uses a **deterministic pipeline** pattern, not an agent pattern.

### When to Use Each

| Pattern | Use Case | Example |
|---------|----------|---------|
| **Pipeline** | Fixed sequence of steps | Resume processing, ETL, document conversion |
| **Agent** | Dynamic decision-making | Chat assistants, autonomous problem-solving |

### Our Pipeline

\\\mermaid
flowchart TB
    subgraph Input
        A[Resume File]
    end
    
    subgraph Pipeline
        B[1. Extract Data] --> C[2. Summarize]
        C --> D[3. Remove PII]
        D --> E[4. Store]
    end
    
    subgraph Output
        F[(Cosmos DB)]
    end
    
    A --> B
    E --> F
\\\

## Data Flow

\\\
                    +------------------+
                    |   Resume Text    |
                    +--------+---------+
                             |
                             v
              +----------------------------+
              |   extract_resume_data()    |
              |   - GPT function calling   |
              |   - Structured output      |
              +-------------+--------------+
                            |
                            v
              +----------------------------+
              |   generate_summary()       |
              |   - 250 word max           |
              |   - Professional tone      |
              +-------------+--------------+
                            |
                            v
              +----------------------------+
              |   remove_pii()             |
              |   - Names -> [REDACTED]    |
              |   - Emails, phones, etc    |
              +-------------+--------------+
                            |
                            v
              +----------------------------+
              |   ResumeStorage.store()    |
              |   - Cosmos DB upsert       |
              |   - Partition by resume_id |
              +----------------------------+
\\\

## Component Responsibilities

### ResumeProcessor (processor.py)
- Orchestrates the pipeline
- Loads configuration from TOML
- Initializes Azure OpenAI client
- Calls each step in sequence

### Extractor (extractor.py)
- Uses GPT function calling with schema
- Returns structured dict: name, email, skills, experience, education

### Summarizer (summarizer.py)  
- Generates professional summary
- Configurable word limit

### PII Remover (pii_remover.py)
- Redacts: names, emails, phones, addresses, dates of birth
- Replaces with [REDACTED]

### Storage (storage.py)
- Async Cosmos DB operations
- Managed identity authentication
- Raw and processed containers

## Technology Stack

- **Python 3.11+**: Runtime
- **Azure OpenAI**: GPT-4o for extraction/summarization
- **Cosmos DB**: Document storage
- **FastAPI**: REST API
- **React**: Frontend UI
- **TOML**: Configuration format

## Security

- No hardcoded secrets
- Azure Managed Identity for auth
- PII automatically redacted before storage
