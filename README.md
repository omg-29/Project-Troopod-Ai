# Troopod -- AI-Powered Conversion Rate Optimization

Troopod dynamically personalizes landing pages to match ad campaigns using AI. Upload an ad creative, provide a target URL and requirements, and Troopod generates a CRO-optimized version of the page with modifications that feel organic to the existing design.

---

## Architecture

```text
Frontend (React + Vite + Tailwind CSS)
    |
    | POST /api/generate (multipart/form-data)
    | Response: Server-Sent Events stream
    v
Backend (FastAPI + Uvicorn)
    |
    |-- Step 1: Text Processor ---------> Gemini AI (structured JSON)
    |-- Step 2: Image Analyzer ---------> Gemini Vision (structured JSON)
    |-- Step 3: Web Scraper ------------> Playwright (headless Chromium)
    |-- Step 3.5: Content Optimizer ----> Cleans/minifies HTML, CSS & JS
    |-- Step 4a: Prompt Enhancement ----> Gemini AI (Master Prompt)
    |-- Step 4b: Code Modifier ---------> Gemini AI (Structured JSON Ops)
    |-- Step 4c: DOM Applicator --------> Surgical BeautifulSoup patches
    |
    v
Frontend: Secure iframe preview (srcDoc + sandbox)
```

---

## Prerequisites

- **Python** 3.12+ (tested with 3.14)
- **Node.js** 18+ and npm
- **Google Gemini API Key** (for AI processing)
- **Playwright Chromium** browser (installed via Playwright CLI)

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | Yes | -- | Google Gemini API key |
| `PRIMARY_MODEL` | No | `gemini-2.5-flash` | Primary Gemini model |
| `FALLBACK_MODEL` | No | `gemini-2.5-flash-lite` | Fallback model upon rate limit |

### Frontend (`frontend/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `VITE_API_URL` | No | `http://localhost:8000` | Backend API URL |

---

## Setup & Run

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright Chromium browser
playwright install chromium

# Configure environment
cp .env.example .env
# Edit .env and set your GEMINI_API_KEY

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env

# Start dev server
npm run dev
```

The frontend runs at `http://localhost:5173` and proxies API requests to `http://localhost:8000`.

---

## Technical Highlights

- **Content Optimization:** Raw web pages are sent through a character-limiter that strips non-visual `data-*` attributes, base64 blobs, analytics scripts, and comments. This reduces token payloads by ~80%, eliminating generation timeouts and drastically saving costs.
- **Smart Path Rewriting:** Transforms all relative URLs across CSS stylesheets and HTML into absolute paths, preventing `404 Not Found` errors when rendering the foreign webpage locally.
- **Organic Code Modification Directive:** AI is strictly prompted to inject modifications that respect the legacy DOM structure, inheriting original global typography CSS rather than brute-forcing new designs.
- **Surgical DOM Patching:** Instead of regenerating entire HTML documents (which hits token limits), Troopod uses a diff-based approach where Gemini returns structured JSON operations applied surgically via BeautifulSoup. This allows for processing pages up to 500K+ characters.
- **Self-Healing Selector Retry:** If the AI produces invalid CSS selectors, the system automatically builds a "correction context" and triggers a fast retry, allowing the agent to self-heal and find the correct DOM elements.
- **Windows asyncio Isolation:** Playwright is safely quarantined into a secondary background thread (`asyncio.to_thread`) bridging headless-browser compatibility with Uvicorn’s ProactorEventLoop on Windows.

---

## API Reference

### POST `/api/generate`

Accepts `multipart/form-data`:

| Field | Type | Description |
|---|---|---|
| `image` | File | Ad campaign creative (JPEG/PNG, max 5MB) |
| `url` | String | Target webpage URL |
| `text` | String | Plain text CRO requirements |

Returns `text/event-stream` (SSE) with events:

```json
data: {"stage": "extraction", "message": "...", "progress": 10, "completed": false}
data: {"stage": "analysis", "message": "...", "progress": 30, "completed": false}
data: {"stage": "scraping", "message": "...", "progress": 50, "completed": false}
data: {"stage": "generation", "message": "...", "progress": 75, "completed": false}
data: {"stage": "complete", "message": "...", "progress": 100, "completed": true, "result": {...}}
```

---

## Project Structure

```text
Troopod/
|-- README.md
|-- backend/
|   |-- app/
|       |-- main.py              # FastAPI app, SSE endpoint
|       |-- config.py            # Environment settings
|       |-- schemas.py           # Pydantic models
|       |-- services/
|       |   |-- ai_client.py     # Gemini wrapper (primary + fallback logic)
|       |   |-- text_processor.py
|       |   |-- image_analyzer.py
|       |   |-- web_scraper.py   # Playwright + Sync Thread Isolation
|       |   |-- prompt_engine.py
|       |   |-- code_modifier.py
|       |-- utils/
|           |-- content_optimizer.py # HTML/CSS/JS minimizer & tracker stripper
|           |-- dom_applicator.py    # Surgical BeautifulSoup DOM patcher
|           |-- url_rewriter.py      # Relative to absolute path rewriter for HTML/CSS
|           |-- json_repair.py       # JSON validation + AI repair
|           |-- sanitizer.py         # Markdown code fence stripper
|-- frontend/
    |-- ...
```

---

## Deployment

Troopod is optimized for one-click deployment via **Render Blueprints** using a reliable Docker-based backend.

### 1. Push to GitHub
Initialize your repository and push the entire codebase:
```bash
git init
git add .
git commit -m "Production ready: Dockerized Backend"
git remote add origin YOUR_REPO_URL
git push -u origin main
```

### 2. Launch on Render
1. Go to your [Render Dashboard](https://render.com).
2. Click **New +** -> **Blueprint**.
3. Connect your GitHub repository.
4. Render will detect `render.yaml` and configure:
   - **`troopod-backend`**: A Docker-based service hosting the FastAPI engine and Playwright.
   - **`troopod-frontend`**: A Static Site service hosting the React UI.

### 3. Essential Environment Setup
Once the blueprint is created, go to the **Environment** settings for `troopod-backend` and set:

- **`GEMINI_API_KEY`**: (Required) your Google Gemini API key.
- **`CORS_ORIGINS`**: (Important) Copy your frontend's live URL (e.g., `https://troopod-frontend.onrender.com`) and add it here. This allows the UI to talk to the backend.

### Why Docker?
Troopod uses Docker specifically to bundle **Playwright Chromium** with all its native Linux library dependencies. This guarantees that web scraping works flawlessly in the cloud without "Missing shared library" errors common in standard Python environments.

---

## Troubleshooting

1. **`NotImplementedError` during scraping**: Caused by Uvicorn event loop policies on Windows. Ensuring OS-aware loop policy in `main.py` solves this for production.
2. **`Failed to Fetch` in Production**:
   - **Check API URL**: Open your browser console (F12). If you see `[Troopod] Initializing generation | Target API: http://localhost:8000`, it means your frontend is still trying to talk to your local machine. You **must** manually set `VITE_API_URL` to your backend's public URL in the Render dashboard.
   - **Check CORS**: If the URL is correct but still failing, ensure the `CORS_ORIGINS` variable in your **Backend** settings on Render matches your **Frontend** URL exactly.
3. **Blank White Page**: Usually caused by absolute path resolution. Ensure the latest `vite.config.js` with `base: './'` is deployed.
2. **`503 / 429 API Capacity` errors**: Google's free-tier APIs occasionally block heavy HTML generation requests. Troopod's `ai_client` employs an automated exponential backoff mechanism and will automatically switch to your configured `FALLBACK_MODEL` to retry. Ensure your API Key originates from a project matching your desired Models list.
3. **Missing CSS Base64 / Fonts on Preview**: Verify `url_rewriter.py` successfully intercepted the stylesheet download; Troopod automatically anchors relative CSS fonts against their native source server.
4. **Playwright browser not found**: Run `npx playwright install chromium` or `playwright install chromium` inside your activated directory.

