import sys
import json
import logging
import asyncio
from typing import AsyncGenerator

# Fix for Playwright NotImplementedError on Windows under Uvicorn/FastAPI
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.config import settings
from app.schemas import StatusEvent, GenerationResult, ErrorResponse
from app.services.text_processor import process_text
from app.services.image_analyzer import analyze_image
from app.services.web_scraper import scrape_page
from app.services.prompt_engine import generate_master_prompt
from app.services.code_modifier import modify_page

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize a global semaphore to limit concurrent CRO generations.
# This is critical for free-tier servers with limited RAM (512MB)
# to prevent multiple Playwright/Chromium instances from crashing the server.
generation_semaphore = asyncio.Semaphore(1)

app = FastAPI(
    title="Troopod API",
    description="AI-powered Conversion Rate Optimization engine",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _sse_event(event: StatusEvent) -> str:
    """Format a StatusEvent as an SSE message string."""
    return f"data: {event.model_dump_json()}\n\n"


def _sse_error(stage: str, message: str) -> str:
    """Format an error as an SSE message string."""
    error = ErrorResponse(error="pipeline_error", detail=message, stage=stage)
    payload = {
        "stage": "error",
        "message": message,
        "progress": 0,
        "completed": False,
        "error": error.model_dump(),
    }
    return f"data: {json.dumps(payload)}\n\n"


async def _run_pipeline(
    text_input: str,
    image_bytes: bytes,
    mime_type: str,
    target_url: str,
) -> AsyncGenerator[str, None]:
    """
    Execute the CRO pipeline sequentially, yielding SSE events at each stage.

    Step 1: Text Processing
    Step 2: Image Analysis
    Step 3: Web Scraping
    Step 4a: Prompt Enhancement
    Step 4b: Code Modification
    """
    async with generation_semaphore:
        # --- Step 1: Text Requirement Processing ---
        yield _sse_event(StatusEvent(
            stage="extraction",
            message="Extracting requirements from your text input...",
            progress=5,
        ))

        try:
            text_requirements = await process_text(text_input)
        except Exception as exc:
            logger.error("Step 1 failed: %s", exc)
            yield _sse_error("extraction", f"Text processing failed: {exc}")
            return

        yield _sse_event(StatusEvent(
            stage="extraction",
            message=f"Extracted {len(text_requirements.exact_keywords)} keywords successfully.",
            progress=15,
        ))

    # --- Step 2: Image Creative Processing ---
    await asyncio.sleep(settings.PIPELINE_STEP_DELAY)
    yield _sse_event(StatusEvent(
        stage="analysis",
        message="Analyzing your ad creative with AI vision...",
        progress=20,
    ))

    try:
        image_analysis = await analyze_image(image_bytes, mime_type)
    except Exception as exc:
        logger.error("Step 2 failed: %s", exc)
        yield _sse_error("analysis", f"Image analysis failed: {exc}")
        return

    yield _sse_event(StatusEvent(
        stage="analysis",
        message=f"Identified product: {image_analysis.main_product}",
        progress=35,
    ))

    # --- Step 3: Web Page Scraping ---
    yield _sse_event(StatusEvent(
        stage="scraping",
        message="Scraping and capturing target webpage...",
        progress=40,
    ))

    try:
        scraped_page = await scrape_page(target_url)
    except Exception as exc:
        logger.error("Step 3 failed: %s", exc)
        yield _sse_error("scraping", f"Web scraping failed: {exc}")
        return

    yield _sse_event(StatusEvent(
        stage="scraping",
        message="Webpage captured successfully. Processing assets...",
        progress=55,
    ))

    # --- Step 4a: Prompt Enhancement ---
    await asyncio.sleep(settings.PIPELINE_STEP_DELAY)
    yield _sse_event(StatusEvent(
        stage="generation",
        message="Building CRO optimization strategy...",
        progress=60,
    ))

    try:
        master_prompt = await generate_master_prompt(
            text_requirements=text_requirements,
            image_analysis=image_analysis,
            accessibility_tree=scraped_page.accessibility_tree,
            visual_theme=scraped_page.visual_theme,
        )
    except Exception as exc:
        logger.error("Step 4a failed: %s", exc)
        yield _sse_error("generation", f"Prompt generation failed: {exc}")
        return

    yield _sse_event(StatusEvent(
        stage="generation",
        message="CRO strategy ready. Injecting optimizations...",
        progress=75,
    ))

    # --- Step 4b: Code Modification ---
    await asyncio.sleep(settings.PIPELINE_STEP_DELAY)
    try:
        modified_page = await modify_page(
            master_prompt=master_prompt,
            scraped_page=scraped_page,
        )
    except Exception as exc:
        logger.error("Step 4b failed: %s", exc)
        yield _sse_error("generation", f"Code modification failed: {exc}")
        return

    yield _sse_event(StatusEvent(
        stage="generation",
        message="CRO optimizations applied successfully.",
        progress=95,
    ))

    # --- Final Result ---
    result = GenerationResult(
        modified_html=modified_page.html,
        modified_css=modified_page.css,
        modified_js=modified_page.js,
    )

    final_payload = {
        "stage": "complete",
        "message": "All optimizations applied. Rendering preview.",
        "progress": 100,
        "completed": True,
        "result": result.model_dump(),
    }
    yield f"data: {json.dumps(final_payload)}\n\n"


@app.post("/api/generate")
async def generate_cro(
    image: UploadFile = File(..., description="Ad campaign creative (JPEG/PNG, max 5MB)"),
    url: str = Form(..., description="Target webpage URL"),
    text: str = Form(..., description="Plain text requirements for the CRO modifications"),
):
    """
    Main CRO generation endpoint.

    Accepts multipart form data with an image file, target URL, and text requirements.
    Returns a Server-Sent Events stream with real-time progress updates and the final
    modified webpage code.
    """
    # --- Validate image MIME type ---
    if image.content_type not in settings.ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image type: {image.content_type}. Allowed types: {settings.ALLOWED_MIME_TYPES}",
        )

    # --- Read and validate image size ---
    image_bytes = await image.read()
    if len(image_bytes) > settings.max_image_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"Image exceeds {settings.MAX_IMAGE_SIZE_MB}MB limit ({len(image_bytes)} bytes).",
        )

    # --- Validate URL ---
    if not url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=400,
            detail="URL must start with http:// or https://",
        )

    # --- Validate text ---
    if not text.strip():
        raise HTTPException(
            status_code=400,
            detail="Text requirements cannot be empty.",
        )

    logger.info("Starting CRO pipeline | URL: %s | Image: %s (%d bytes)", url, image.filename, len(image_bytes))

    return StreamingResponse(
        _run_pipeline(
            text_input=text.strip(),
            image_bytes=image_bytes,
            mime_type=image.content_type,
            target_url=url.strip(),
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "troopod-api"}
