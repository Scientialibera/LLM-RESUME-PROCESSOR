"""
FastAPI application for resume processing.
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import structlog
import uuid
from datetime import datetime
from typing import List, Optional
import sys
import os

from backend.app.shared.config import get_settings
from backend.app.shared.schemas import (
    ResumeUploadResponse,
    ResumeListResponse,
    ResumeSearchRequest,
    ResumeSearchResult
)
from backend.app.clients import AzureOpenAIClient, CosmosDBClient
from backend.app.services.resume_processor import ResumeProcessor

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger(__name__)

# Global clients
aoai_client: Optional[AzureOpenAIClient] = None
cosmos_client: Optional[CosmosDBClient] = None
resume_processor: Optional[ResumeProcessor] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    global aoai_client, cosmos_client, resume_processor

    # Startup
    logger.info("Starting up application")
    settings = get_settings()

    # Initialize clients
    aoai_client = AzureOpenAIClient(settings.azure_openai)
    cosmos_client = CosmosDBClient(settings.cosmos_db)
    resume_processor = ResumeProcessor(aoai_client, cosmos_client)

    logger.info("Application started successfully")

    yield

    # Shutdown
    logger.info("Shutting down application")
    if aoai_client:
        await aoai_client.close()
    if cosmos_client:
        await cosmos_client.close()
    logger.info("Application shut down successfully")


# Create FastAPI app
settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_resume_processor() -> ResumeProcessor:
    """Dependency to get resume processor."""
    if resume_processor is None:
        raise HTTPException(status_code=500, detail="Resume processor not initialized")
    return resume_processor


def get_cosmos_client() -> CosmosDBClient:
    """Dependency to get Cosmos DB client."""
    if cosmos_client is None:
        raise HTTPException(status_code=500, detail="Cosmos DB client not initialized")
    return cosmos_client


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# Resume upload endpoint
@app.post(f"{settings.api_prefix}/resumes/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    processor: ResumeProcessor = Depends(get_resume_processor),
    cosmos: CosmosDBClient = Depends(get_cosmos_client)
):
    """
    Upload a resume file for processing.

    The resume will be stored in Cosmos DB and processed asynchronously.
    """
    logger.info("Received resume upload", filename=file.filename)

    try:
        # Read file content
        content = await file.read()
        resume_text = content.decode('utf-8')

        # Generate unique ID
        resume_id = str(uuid.uuid4())

        # Create document for raw resumes container
        resume_doc = {
            "id": resume_id,
            "filename": file.filename,
            "upload_date": datetime.utcnow().isoformat(),
            "status": "pending",
            "raw_text": resume_text
        }

        # Store in Cosmos DB
        await cosmos.create_item("raw-resumes", resume_doc)

        # Trigger processing in background
        background_tasks.add_task(processor.process_and_store, resume_id, "raw-resumes")

        logger.info("Resume uploaded successfully", resume_id=resume_id)

        return ResumeUploadResponse(
            id=resume_id,
            filename=file.filename,
            status="pending",
            message="Resume uploaded successfully and queued for processing"
        )

    except Exception as e:
        logger.error("Failed to upload resume", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to upload resume: {str(e)}")


# Get resume by ID
@app.get(f"{settings.api_prefix}/resumes/{{resume_id}}")
async def get_resume(
    resume_id: str,
    cosmos: CosmosDBClient = Depends(get_cosmos_client)
):
    """Get a resume by ID."""
    logger.info("Fetching resume", resume_id=resume_id)

    try:
        # Try processed container first
        resume = await cosmos.read_item("processed-resumes", resume_id, resume_id)

        if not resume:
            # Try raw container
            resume = await cosmos.read_item("raw-resumes", resume_id, resume_id)

        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")

        return resume

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch resume", resume_id=resume_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch resume: {str(e)}")


# List all resumes
@app.get(f"{settings.api_prefix}/resumes", response_model=ResumeListResponse)
async def list_resumes(
    status: Optional[str] = None,
    limit: int = 100,
    cosmos: CosmosDBClient = Depends(get_cosmos_client)
):
    """List all resumes with optional status filter."""
    logger.info("Listing resumes", status=status, limit=limit)

    try:
        # Query processed resumes
        query = "SELECT * FROM c"
        params = []

        if status:
            query += " WHERE c.status = @status"
            params = [{"name": "@status", "value": status}]

        query += f" ORDER BY c.upload_date DESC OFFSET 0 LIMIT {limit}"

        resumes = await cosmos.query_items("processed-resumes", query, params)

        # If no processed resumes, check raw container
        if not resumes:
            resumes = await cosmos.query_items("raw-resumes", query, params)

        return ResumeListResponse(
            resumes=resumes,
            total=len(resumes)
        )

    except Exception as e:
        logger.error("Failed to list resumes", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list resumes: {str(e)}")


# Process resume manually
@app.post(f"{settings.api_prefix}/resumes/{{resume_id}}/process")
async def process_resume(
    resume_id: str,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    processor: ResumeProcessor = Depends(get_resume_processor)
):
    """Manually trigger processing of a resume."""
    logger.info("Manual processing triggered", resume_id=resume_id)

    try:
        background_tasks.add_task(processor.process_and_store, resume_id, "raw-resumes")

        return {
            "message": "Processing started",
            "resume_id": resume_id
        }

    except Exception as e:
        logger.error("Failed to start processing", resume_id=resume_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to start processing: {str(e)}")


# Event Grid webhook endpoint
@app.post(f"{settings.api_prefix}/webhooks/eventgrid")
async def handle_eventgrid_webhook(
    request: Request,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    processor: ResumeProcessor = Depends(get_resume_processor)
):
    """
    Handle Event Grid webhook for new resume uploads.

    This endpoint is called automatically when a new document is created in the
    raw-resumes Cosmos DB container.
    """
    logger.info("Received Event Grid webhook")

    try:
        events = await request.json()

        # Handle validation handshake
        if isinstance(events, list) and len(events) > 0:
            event = events[0]

            # Subscription validation
            if event.get("eventType") == "Microsoft.EventGrid.SubscriptionValidationEvent":
                validation_code = event["data"]["validationCode"]
                logger.info("Event Grid subscription validation", code=validation_code)
                return {"validationResponse": validation_code}

        # Process events
        for event in events:
            event_type = event.get("eventType", "")

            # Check if it's a Cosmos DB change event
            if "Microsoft.DocumentDB" in event_type or "Microsoft.Storage" in event_type:
                data = event.get("data", {})

                # Extract resume ID from event data
                resume_id = None
                if "id" in data:
                    resume_id = data["id"]
                elif "url" in data:
                    # Extract from blob storage URL if needed
                    resume_id = data.get("url", "").split("/")[-1].split(".")[0]

                if resume_id:
                    logger.info("Processing resume from Event Grid", resume_id=resume_id)
                    background_tasks.add_task(
                        processor.process_and_store,
                        resume_id,
                        "raw-resumes"
                    )

        return {"status": "accepted"}

    except Exception as e:
        logger.error("Failed to handle Event Grid webhook", error=str(e))
        # Return 200 to prevent Event Grid retries for invalid payloads
        return JSONResponse(
            status_code=200,
            content={"status": "error", "message": str(e)}
        )


# Delete resume
@app.delete(f"{settings.api_prefix}/resumes/{{resume_id}}")
async def delete_resume(
    resume_id: str,
    cosmos: CosmosDBClient = Depends(get_cosmos_client)
):
    """Delete a resume by ID."""
    logger.info("Deleting resume", resume_id=resume_id)

    try:
        # Delete from both containers
        await cosmos.delete_item("raw-resumes", resume_id, resume_id)
        await cosmos.delete_item("processed-resumes", resume_id, resume_id)

        return {"message": "Resume deleted successfully", "resume_id": resume_id}

    except Exception as e:
        logger.error("Failed to delete resume", resume_id=resume_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to delete resume: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
