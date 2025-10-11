# Resume Processor - Enterprise Grade Application

An enterprise-grade resume processing application powered by Azure OpenAI, Cosmos DB, and Event Grid. This system automatically extracts structured information from resumes, generates professional summaries, removes PII, and suggests potential roles using AI.

## Architecture

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│  React Frontend │─────▶│  FastAPI Backend │─────▶│  Azure OpenAI   │
│   (Vite + React)│      │   (Python 3.11+) │      │  (GPT-4 + Ada)  │
└─────────────────┘      └──────────────────┘      └─────────────────┘
                                  │
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
            ┌───────▼────────┐         ┌───────▼────────┐
            │   Cosmos DB    │         │  Event Grid    │
            │ (2 Containers) │◀────────│  (Webhooks)    │
            └────────────────┘         └────────────────┘
```

## Features

- **Resume Upload & Processing**: Upload resumes in TXT, PDF, DOC, or DOCX formats
- **AI-Powered Extraction**: Extract structured data (personal info, education, experience, skills)
- **Summary Generation**: Create unbiased, extractive summaries of resumes
- **PII Removal**: Automatically remove personally identifiable information
- **Role Suggestions**: AI generates 10 potential job roles based on experience
- **Real-time Dashboard**: Monitor processing status with auto-refresh
- **Event-Driven Architecture**: Automatic processing via Event Grid webhooks
- **Azure Managed Identity**: Secure, keyless authentication to Azure services

## Project Structure

```
LLM-RESUME-PROCESSOR/
├── backend/
│   ├── app/
│   │   ├── api/                    # API endpoints
│   │   ├── services/               # Business logic
│   │   │   └── resume_processor.py # Core processing service
│   │   └── main.py                 # FastAPI application
│   └── requirements.txt            # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/             # React components
│   │   ├── pages/                  # Page components
│   │   │   ├── Dashboard.jsx       # Resume list and management
│   │   │   ├── UploadResume.jsx    # Upload interface
│   │   │   └── ResumeDetail.jsx    # Detailed resume view
│   │   ├── services/
│   │   │   └── api.js              # API client
│   │   └── App.jsx                 # Main app component
│   ├── package.json                # Node dependencies
│   └── vite.config.js              # Vite configuration
├── shared/
│   ├── config.py                   # Configuration settings
│   └── schemas.py                  # Pydantic models
├── deployment/
│   └── Deploy-AzureResources.ps1   # PowerShell deployment script
├── aoai_client.py                  # Azure OpenAI client
├── cosmos_client.py                # Cosmos DB client
├── .env.example                    # Environment template
└── README.md
```

## Prerequisites

### Required Software
- **Python**: 3.11 or higher
- **Node.js**: 18.x or higher
- **PowerShell**: 7.0 or higher (for deployment)
- **Azure CLI**: Latest version
- **Git**: For version control

### Azure Resources
The deployment script will create:
- Azure OpenAI Service (GPT-4 + text-embedding-ada-002)
- Cosmos DB account with 2 containers
- Event Grid System Topic
- Required IAM roles

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd LLM-RESUME-PROCESSOR
```

### 2. Deploy Azure Resources

```powershell
# Login to Azure
Connect-AzAccount

# Run deployment script
cd deployment
.\Deploy-AzureResources.ps1 -ResourceGroupName "rg-resume-processor" -Location "eastus"
```

The script will:
- Create all required Azure resources
- Deploy OpenAI models
- Create Cosmos DB containers
- Set up Event Grid topic
- Generate a `.env` file with endpoints

### 3. Configure Environment

Copy the generated `.env` file to the root directory, or create from the example:

```bash
cp .env.example .env
```

Edit `.env` with your Azure resource endpoints (already populated by deployment script).

### 4. Setup Backend

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the API
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

API Documentation: `http://localhost:8000/docs`

### 5. Setup Frontend

```bash
# Navigate to frontend directory
cd frontend

# Create .env file
cp .env.example .env

# Install dependencies
npm install

# Run development server
npm run dev
```

The frontend will be available at `http://localhost:5173`

## API Endpoints

### Resume Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/resumes/upload` | Upload a new resume |
| `GET` | `/api/v1/resumes` | List all resumes (with optional status filter) |
| `GET` | `/api/v1/resumes/{id}` | Get resume by ID |
| `POST` | `/api/v1/resumes/{id}/process` | Manually trigger processing |
| `DELETE` | `/api/v1/resumes/{id}` | Delete a resume |

### Webhooks

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/webhooks/eventgrid` | Event Grid webhook for auto-processing |

### Health Check

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check endpoint |

## Event Grid Integration

### Automatic Processing Flow

1. **Resume Upload**: User uploads resume via frontend
2. **Storage**: Resume stored in `raw-resumes` Cosmos DB container
3. **Event Trigger**: Cosmos DB change triggers Event Grid event
4. **Webhook**: Event Grid calls API webhook endpoint
5. **Processing**: Backend extracts data, generates summary, removes PII
6. **Storage**: Processed data stored in `processed-resumes` container

### Configure Event Grid Subscription

After deploying the API:

```powershell
# Get your API webhook URL
$webhookUrl = "https://your-api-url.com/api/v1/webhooks/eventgrid"

# Create Event Grid subscription
az eventgrid system-topic event-subscription create \
  --name resume-processor-subscription \
  --resource-group rg-resume-processor \
  --system-topic-name evgt-resume-processor \
  --endpoint $webhookUrl \
  --endpoint-type webhook \
  --included-event-types Microsoft.DocumentDB.DatabaseAccountsCreated
```

## Data Flow

### Resume Processing Pipeline

```
1. Upload Resume (TXT/PDF/DOC/DOCX)
           │
           ▼
2. Store in raw-resumes container
           │
           ▼
3. Extract structured data with OpenAI function calling
   - Personal Information
   - Contact Information
   - Education
   - Work Experience
   - Skills
           │
           ▼
4. Generate AI-powered summary (extractive, unbiased)
           │
           ▼
5. Remove PII using OpenAI
           │
           ▼
6. Generate keyword skills and suggested roles
           │
           ▼
7. Store in processed-resumes container
```

## Cosmos DB Schema

### raw-resumes Container

```json
{
  "id": "uuid",
  "filename": "string",
  "upload_date": "datetime",
  "status": "pending|processing|completed|failed",
  "raw_text": "string",
  "error": "string (optional)"
}
```

### processed-resumes Container

```json
{
  "id": "uuid",
  "filename": "string",
  "upload_date": "datetime",
  "status": "completed",
  "processed_data": {
    "personalInformation": {...},
    "contactInformation": {...},
    "education": [...],
    "workExperience": [...],
    "skills": [...],
    "skills_keywords": [...],
    "ai_generated_roles": [...],
    "summary": "string",
    "sanitized_summary": "string"
  }
}
```

## Security

### Managed Identity

The application uses **Azure Managed Identity** for secure, keyless authentication to:
- Azure OpenAI Service
- Cosmos DB
- Blob Storage (if configured)

### Required IAM Roles

The deployment script automatically assigns:
- **Cognitive Services OpenAI User** - For Azure OpenAI access
- **Cosmos DB Data Contributor** - For Cosmos DB read/write
- **EventGrid Data Sender** - For Event Grid publishing

### PII Protection

- All summaries are processed through PII removal
- Sensitive information is redacted using `[REDACTED]` style
- Original data is stored separately for authorized access

## Development

### Backend Development

```bash
# Install dev dependencies
pip install pytest pytest-asyncio black flake8

# Run tests
pytest

# Format code
black .

# Lint code
flake8 .
```

### Frontend Development

```bash
# Install dev dependencies
npm install --save-dev

# Run linter
npm run lint

# Build for production
npm run build

# Preview production build
npm run preview
```

## Deployment

### Backend Deployment (Azure Container Apps)

```powershell
# Build and push Docker image
docker build -t resume-api:latest ./backend
docker tag resume-api:latest <your-registry>.azurecr.io/resume-api:latest
docker push <your-registry>.azurecr.io/resume-api:latest

# Deploy to Container Apps
az containerapp create \
  --name ca-resume-api \
  --resource-group rg-resume-processor \
  --image <your-registry>.azurecr.io/resume-api:latest \
  --environment cae-resume-processor \
  --ingress external \
  --target-port 8000
```

### Frontend Deployment (Azure Static Web Apps)

```bash
# Build frontend
cd frontend
npm run build

# Deploy to Azure Static Web Apps
az staticwebapp create \
  --name swa-resume-frontend \
  --resource-group rg-resume-processor \
  --source ./dist \
  --location eastus
```

## Troubleshooting

### Common Issues

**Issue**: `Azure AD token expired`
- **Solution**: The application automatically refreshes tokens. If issues persist, restart the API.

**Issue**: `Cosmos DB connection failed`
- **Solution**: Verify Managed Identity has proper RBAC roles on Cosmos DB

**Issue**: `Event Grid webhook not triggering`
- **Solution**: Check Event Grid subscription is active and webhook URL is accessible

**Issue**: `OpenAI rate limiting`
- **Solution**: Increase deployment capacity or implement retry logic with exponential backoff

### Logs

View structured logs with:

```bash
# Backend logs
tail -f backend/logs/app.log

# Or use Azure Monitor if deployed
az monitor app-insights query \
  --app <app-insights-name> \
  --analytics-query "traces | where timestamp > ago(1h)"
```

## Performance

### Optimization Tips

1. **Cosmos DB**: Use appropriate partition keys for query patterns
2. **OpenAI**: Batch requests when possible to reduce latency
3. **Caching**: Implement Redis for frequently accessed resumes
4. **CDN**: Use Azure CDN for frontend static assets

### Expected Performance

- Resume processing: 10-30 seconds per resume
- API response time: <500ms for read operations
- Concurrent uploads: 100+ (with proper scaling)

## License

MIT License - See LICENSE file for details

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Support

For issues and questions:
- Create an issue in the repository
- Contact: your-email@example.com

## Acknowledgments

- Azure OpenAI for powerful language models
- FastAPI for the excellent web framework
- React and Vite for modern frontend development
