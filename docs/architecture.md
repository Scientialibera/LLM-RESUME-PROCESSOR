# Architecture Documentation

Detailed architecture diagrams for the Resume Processor Agent.

## High-Level Architecture

```mermaid
graph TB
    subgraph Clients
        Web[Web Browser]
        Mobile[Mobile App]
        CLI[CLI Tool]
    end
    
    subgraph Presentation
        React[React Frontend<br/>Vite + TailwindCSS]
    end
    
    subgraph API Layer
        FastAPI[FastAPI Server<br/>Python 3.11+]
        Swagger[OpenAPI/Swagger]
    end
    
    subgraph Agent Framework
        Agent[ResumeProcessorAgent]
        Config[agent.toml<br/>Configuration]
        Prompt[System Prompt]
        
        subgraph Tool Registry
            T1[ResumeExtractor]
            T2[ResumeSummarizer]
            T3[PIIRemover]
            T4[ResumeStorage]
        end
        
        subgraph Workflows
            W1[process_resume<br/>Sequential Pipeline]
        end
    end
    
    subgraph Azure Platform
        AOAI[Azure OpenAI<br/>GPT-4o]
        Cosmos[(Azure Cosmos DB<br/>NoSQL)]
        EventGrid[Azure Event Grid]
        Identity[Managed Identity]
    end
    
    Web --> React
    Mobile --> FastAPI
    CLI --> FastAPI
    React --> FastAPI
    FastAPI --> Swagger
    FastAPI --> Agent
    
    Agent --> Config
    Agent --> Prompt
    Agent --> T1 & T2 & T3 & T4
    Agent --> W1
    
    T1 & T2 & T3 --> AOAI
    T4 --> Cosmos
    Cosmos --> EventGrid
    EventGrid --> FastAPI
    
    FastAPI --> Identity
    Identity --> AOAI
    Identity --> Cosmos
    
    style Agent fill:#0078D4,color:#fff
    style AOAI fill:#00A36C,color:#fff
    style Cosmos fill:#00A36C,color:#fff
    style EventGrid fill:#00A36C,color:#fff
```

## Tool Architecture

```mermaid
classDiagram
    class ResumeProcessorAgent {
        +config: AgentConfig
        +_client: AzureOpenAI
        +_tools: Dict
        +initialize()
        +process_resume()
        +process_and_store()
        +chat()
    }
    
    class AgentConfig {
        +agent: dict
        +model: dict
        +tools: list
        +workflows: list
        +system_prompt: str
    }
    
    class ResumeExtractor {
        +client: AzureOpenAI
        +deployment: str
        +extract(resume_text) Dict
    }
    
    class ResumeSummarizer {
        +client: AzureOpenAI
        +deployment: str
        +summarize(data, max_length) str
    }
    
    class PIIRemover {
        +client: AzureOpenAI
        +deployment: str
        +remove(text) str
    }
    
    class ResumeStorage {
        +endpoint: str
        +database_name: str
        +store(id, filename, data) Dict
        +get(id) Dict
        +list(status, limit) List
        +delete(id)
    }
    
    ResumeProcessorAgent --> AgentConfig
    ResumeProcessorAgent --> ResumeExtractor
    ResumeProcessorAgent --> ResumeSummarizer
    ResumeProcessorAgent --> PIIRemover
    ResumeProcessorAgent --> ResumeStorage
```

## Data Flow

```mermaid
flowchart LR
    subgraph Input
        PDF[PDF/DOCX/TXT]
    end
    
    subgraph Processing
        Parse[Text Extraction]
        Extract[AI Extraction<br/>Function Calling]
        Summary[Summary Generation]
        PII[PII Removal]
    end
    
    subgraph Output
        Raw[(Raw Container)]
        Processed[(Processed Container)]
        API[API Response]
    end
    
    PDF --> Parse
    Parse --> Raw
    Parse --> Extract
    Extract --> Summary
    Summary --> PII
    PII --> Processed
    Processed --> API
    
    style Extract fill:#0078D4,color:#fff
    style Summary fill:#0078D4,color:#fff
    style PII fill:#0078D4,color:#fff
```

## Extracted Data Schema

```mermaid
erDiagram
    RESUME {
        string id PK
        string filename
        datetime upload_date
        string status
        json processed_data
    }
    
    PROCESSED_DATA {
        json personalInformation
        json contactInformation
        array education
        array workExperience
        array skills
        array skills_keywords
        array ai_generated_roles
        string summary
        string sanitized_summary
    }
    
    PERSONAL_INFO {
        string firstName
        string lastName
        string middleName
        string dateOfBirth
    }
    
    EDUCATION {
        string institution
        string degree
        string fieldOfStudy
        string graduationDate
    }
    
    WORK_EXPERIENCE {
        string employer
        string position
        string startDate
        string endDate
        string responsibilities
    }
    
    RESUME ||--|| PROCESSED_DATA : contains
    PROCESSED_DATA ||--|| PERSONAL_INFO : has
    PROCESSED_DATA ||--o{ EDUCATION : includes
    PROCESSED_DATA ||--o{ WORK_EXPERIENCE : includes
```

## Event-Driven Processing

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI
    participant Cosmos as Cosmos DB
    participant EventGrid as Event Grid
    participant Agent as ResumeProcessorAgent
    participant AOAI as Azure OpenAI
    
    Client->>API: POST /resumes/upload
    API->>Cosmos: Insert raw resume
    API-->>Client: 202 Accepted (pending)
    
    Cosmos->>EventGrid: Change feed event
    EventGrid->>API: POST /webhooks/eventgrid
    
    API->>Agent: process_and_store(id)
    
    loop For each tool
        Agent->>AOAI: Chat completion
        AOAI-->>Agent: Tool result
    end
    
    Agent->>Cosmos: Upsert processed resume
    Agent-->>API: Processing complete
    
    Note over Client,API: Client polls for status
    Client->>API: GET /resumes/{id}
    API->>Cosmos: Read document
    Cosmos-->>API: Processed resume
    API-->>Client: 200 OK (completed)
```

## Deployment Architecture

```mermaid
graph TB
    subgraph Azure Region
        subgraph Container Apps Environment
            API[Container App<br/>resume-api]
            Frontend[Static Web App<br/>resume-frontend]
        end
        
        subgraph Azure Services
            AOAI[Azure OpenAI]
            Cosmos[(Cosmos DB)]
            ACR[Container Registry]
            KeyVault[Key Vault]
        end
        
        subgraph Networking
            FrontDoor[Azure Front Door]
            VNet[Virtual Network]
        end
    end
    
    Users[Users] --> FrontDoor
    FrontDoor --> Frontend
    FrontDoor --> API
    
    API --> VNet
    VNet --> AOAI
    VNet --> Cosmos
    
    API --> KeyVault
    ACR --> API
    
    style API fill:#0078D4,color:#fff
    style AOAI fill:#00A36C,color:#fff
    style Cosmos fill:#00A36C,color:#fff
```
