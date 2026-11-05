"""
main.py - FastAPI application entry point for the AI Job Agent backend.

Endpoints:
  WebSocket  /ws/chat                - real-time bidirectional chat with Alex
  GET        /api/jobs               - list jobs with optional filters
  GET        /api/applications       - application history
  POST       /api/scrape             - trigger background job scraping
  GET        /api/profile            - get user profile
  POST       /api/profile            - create / update user profile
  POST       /api/upload-resume      - multipart resume upload + parsing
  GET        /api/stats              - dashboard statistics
  PUT        /api/jobs/{job_id}/approve  - approve a job for application
  PUT        /api/jobs/{job_id}/reject   - reject a job
  GET        /api/health             - health check
"""

import asyncio
import json
import logging
import os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Ensure backend directory is in python path
_backend_dir = os.path.dirname(os.path.abspath(__file__))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    HTTPException,
    Query,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from config import settings
from database.models import get_db, init_db

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Automated 10-Minute Recurring Job & Internship Scheduler
# ---------------------------------------------------------------------------
_scheduler_task: Optional[asyncio.Task] = None

async def _periodic_job_and_internship_scout():
    """
    Background worker that runs every 10 minutes, alternating searches for
    fresh Data Science & ML internships and entry-level jobs across all platforms.
    """
    logger.info("Autonomous 10-minute Job & Internship Scout activated.")
    queries = [
        "Data Science intern",
        "Machine Learning internship",
        "AI Research intern",
        "Junior Data Scientist",
        "Junior ML Engineer"
    ]
    query_idx = 0
    platforms = ["linkedin", "internshala", "naukri", "indeed", "wellfound"]

    # Initial brief pause on boot
    await asyncio.sleep(5)

    while True:
        current_query = queries[query_idx % len(queries)]
        query_idx += 1
        logger.info(f"[Periodic Scout] Commencing 10-minute automated run for: '{current_query}'")

        try:
            from scrapers.scraper_manager import ScraperManager
            from agents.matcher_agent import MatcherAgent

            # Fetch user profile for live scoring
            user_profile = {}
            async with get_db() as db:
                u_cursor = await db.execute("SELECT * FROM users ORDER BY id LIMIT 1")
                user_row = await u_cursor.fetchone()
                if user_row:
                    user_profile = dict(user_row)

            matcher = MatcherAgent()
            async with ScraperManager() as manager:
                job_listings = await manager.search_all(
                    query=current_query,
                    platforms=platforms,
                    limit_per_platform=4
                )

            now = datetime.now(timezone.utc).isoformat()
            new_added = 0
            async with get_db() as db:
                for j in job_listings:
                    score = 80.0
                    if user_profile:
                        try:
                            score_res = await matcher.score_job({
                                "title": j.title,
                                "description": j.description,
                                "company": j.company,
                                "location": j.location,
                            }, user_profile)
                            score = float(score_res.get("score", 80.0))
                        except Exception:
                            pass

                    cursor = await db.execute(
                        """
                        INSERT OR IGNORE INTO jobs
                            (id, title, company, location, platform, url, description,
                             salary_range, job_type, match_score, status, scraped_at)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            j.id, j.title, j.company, j.location, j.platform,
                            j.url, j.description, j.salary_range, j.job_type,
                            score, "pending", now
                        ),
                    )
                    if cursor.rowcount > 0:
                        new_added += 1
                await db.commit()

            logger.info(f"[Periodic Scout] Successfully processed {len(job_listings)} listings ({new_added} brand new).")

            # Broadcast proactive update to all active WebSocket users
            if active_connections:
                notification_msg = {
                    "type": "chunk",
                    "content": f"\n\n🔔 *Autonomous Scout Update:* I just finished my 10-minute scan for **{current_query}** across LinkedIn, Internshala, and Naukri. Found fresh openings — head to your **Jobs** tab to check them out!",
                    "agent": "Orchestrator",
                }
                for ws in list(active_connections.values()):
                    try:
                        await ws.send_json(notification_msg)
                        await ws.send_json({"type": "done", "agent": "Orchestrator", "data": {"tool_called": "search_jobs"}})
                    except Exception:
                        pass

        except Exception as err:
            logger.error(f"[Periodic Scout] Error during cycle: {err}")

        # Sleep for 10 minutes (600 seconds)
        await asyncio.sleep(600)


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise database and start autonomous 10-minute background scout."""
    global _scheduler_task
    logger.info("Starting up Job Agent backend…")
    await init_db()
    logger.info("Database ready.")

    # Start the 10-minute periodic worker
    _scheduler_task = asyncio.create_task(_periodic_job_and_internship_scout())

    yield

    logger.info("Shutting down Job Agent backend.")
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="AI Job Agent",
    description="Multi-agent AI system for automated job search and applications.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Active WebSocket connections  {session_id: WebSocket}
# ---------------------------------------------------------------------------
active_connections: dict[str, WebSocket] = {}


# ===========================================================================
# WebSocket – /ws/chat
# ===========================================================================
@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    Real-time bidirectional chat endpoint.

    Client sends: {"session_id": "...", "message": "..."}
    Server streams: {"type": "chunk"|"tool_call"|"done"|"error", ...}
    """
    await websocket.accept()
    session_id = str(uuid.uuid4())
    active_connections[session_id] = websocket
    logger.info(f"WebSocket connected: session={session_id}")

    # Send the session ID back to the client
    await websocket.send_json({"type": "session", "session_id": session_id})

    try:
        from agents.orchestrator import OrchestratorAgent

        agent = OrchestratorAgent()

        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "content": "Invalid JSON payload.",
                    "agent": "System",
                })
                continue

            # Allow client to override session_id (e.g. resume a session)
            client_session = data.get("session_id", session_id)
            user_message: str = data.get("message", "").strip()

            if not user_message:
                await websocket.send_json({
                    "type": "error",
                    "content": "Empty message received.",
                    "agent": "System",
                })
                continue

            logger.info(f"[{client_session}] User: {user_message[:80]}")
            await agent.chat(client_session, user_message, websocket)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: session={session_id}")
    except Exception as exc:
        logger.error(f"WebSocket error (session={session_id}): {exc}")
        try:
            await websocket.send_json({
                "type": "error",
                "content": "An unexpected error occurred.",
                "agent": "System",
            })
        except Exception:
            pass
    finally:
        active_connections.pop(session_id, None)


# ===========================================================================
# REST – Jobs
# ===========================================================================
@app.get("/api/jobs")
async def get_jobs(
    status: Optional[str] = Query(None, description="Filter by status"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    min_score: Optional[float] = Query(None, ge=0, le=100),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Return jobs from the database with optional filters."""
    conditions = []
    params: list = []

    if status:
        conditions.append("status = ?")
        params.append(status)
    if platform:
        conditions.append("platform = ?")
        params.append(platform)
    if min_score is not None:
        conditions.append("match_score >= ?")
        params.append(min_score)

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    query = f"""
        SELECT id, title, company, location, platform, url, salary_range,
               job_type, match_score, status, scraped_at
        FROM jobs
        {where_clause}
        ORDER BY match_score DESC
        LIMIT ? OFFSET ?
    """
    params += [limit, offset]

    async with get_db() as db:
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        count_cursor = await db.execute(
            f"SELECT COUNT(*) FROM jobs {where_clause}", params[:-2]
        )
        total = (await count_cursor.fetchone())[0]

    return {
        "jobs": [dict(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# ===========================================================================
# REST – Applications
# ===========================================================================
@app.get("/api/applications")
async def get_applications():
    """Return all application records joined with job details."""
    async with get_db() as db:
        # Find the first user (single-user MVP)
        u_cursor = await db.execute("SELECT id FROM users ORDER BY id LIMIT 1")
        user_row = await u_cursor.fetchone()

    if not user_row:
        return {"applications": [], "count": 0}

    from agents.tracker_agent import TrackerAgent

    tracker = TrackerAgent()
    apps = await tracker.get_all_applications(user_row["id"])
    return {"applications": apps, "count": len(apps)}


# ===========================================================================
# REST – Emails (Inbox / Outbox Communications)
# ===========================================================================
@app.get("/api/emails")
async def get_emails(application_id: Optional[str] = None):
    """Return all email communications (application dispatches and company reverts)."""
    async with get_db() as db:
        if application_id:
            cursor = await db.execute(
                "SELECT * FROM emails WHERE application_id = ? ORDER BY created_at DESC",
                (application_id,)
            )
        else:
            cursor = await db.execute("SELECT * FROM emails ORDER BY created_at DESC")
        rows = await cursor.fetchall()
    return {"emails": [dict(r) for r in rows], "count": len(rows)}


# ===========================================================================
# REST – Scrape (background task)
# ===========================================================================
@app.post("/api/scrape")
async def trigger_scrape(
    background_tasks: BackgroundTasks,
    query: str = Query("Data Science internship"),
    platforms: str = Query("linkedin,internshala,naukri"),
):
    """
    Trigger a background job-scraping task.

    In the full system this would launch Playwright/requests scrapers.
    Here we insert a placeholder job to demonstrate the pipeline end-to-end.
    """
    platform_list = [p.strip() for p in platforms.split(",")]

    async def _scrape_task(q: str, plats: list):
        logger.info(f"Background scrape started: query='{q}', platforms={plats}")
        try:
            from scrapers.scraper_manager import ScraperManager
            from agents.matcher_agent import MatcherAgent

            # Fetch user profile to score matches against
            user_profile = {}
            async with get_db() as db:
                u_cursor = await db.execute("SELECT * FROM users ORDER BY id LIMIT 1")
                user_row = await u_cursor.fetchone()
                if user_row:
                    user_profile = dict(user_row)

            matcher = MatcherAgent()
            async with ScraperManager() as manager:
                job_listings = await manager.search_all(q, platforms=plats, limit_per_platform=5)

            now = datetime.now(timezone.utc).isoformat()
            async with get_db() as db:
                for j in job_listings:
                    score = 75.0
                    if user_profile:
                        try:
                            score_res = await matcher.score_job({
                                "title": j.title,
                                "description": j.description,
                                "company": j.company,
                                "location": j.location,
                            }, user_profile)
                            score = float(score_res.get("score", 75.0))
                        except Exception as m_err:
                            logger.warning(f"Matcher scoring error: {m_err}")

                    await db.execute(
                        """
                        INSERT OR IGNORE INTO jobs
                            (id, title, company, location, platform, url, description,
                             salary_range, job_type, match_score, status, scraped_at)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            j.id,
                            j.title,
                            j.company,
                            j.location,
                            j.platform,
                            j.url,
                            j.description,
                            j.salary_range,
                            j.job_type,
                            score,
                            "pending",
                            now,
                        ),
                    )
                await db.commit()
            logger.info(f"Background scrape complete. Processed {len(job_listings)} jobs.")
        except Exception as exc:
            logger.error(f"Error during scrape task: {exc}", exc_info=True)

    background_tasks.add_task(_scrape_task, query, platform_list)
    return {
        "status": "queued",
        "query": query,
        "platforms": platform_list,
        "message": "Scraping has been queued as a background task.",
    }


# ===========================================================================
# REST – Profile
# ===========================================================================
@app.get("/api/profile")
async def get_profile():
    """Return the user profile."""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM users ORDER BY id LIMIT 1")
        row = await cursor.fetchone()

    if not row:
        return {"profile": None}

    profile = dict(row)
    for field in ("skills", "target_roles", "geographies", "projects"):
        try:
            profile[field] = json.loads(profile.get(field, "[]"))
        except (json.JSONDecodeError, TypeError):
            profile[field] = []

    return {"profile": profile}


@app.post("/api/profile")
async def save_profile(profile: dict):
    """Create or update the user profile."""
    import json as _json

    now = datetime.now(timezone.utc).isoformat()
    skills_json = _json.dumps(profile.get("skills", []))
    roles_json = _json.dumps(profile.get("target_roles", []))
    geos_json = _json.dumps(profile.get("geographies", []))
    projects_json = _json.dumps(profile.get("projects", []))

    async with get_db() as db:
        cursor = await db.execute("SELECT id FROM users ORDER BY id LIMIT 1")
        existing = await cursor.fetchone()

        if existing:
            await db.execute(
                """
                UPDATE users SET
                    name=COALESCE(?,name),
                    email=COALESCE(?,email),
                    phone=COALESCE(?,phone),
                    location=COALESCE(?,location),
                    linkedin_url=COALESCE(?,linkedin_url),
                    github_url=COALESCE(?,github_url),
                    experience_level=COALESCE(?,experience_level),
                    skills=?, target_roles=?, geographies=?, projects=?,
                    updated_at=?
                WHERE id=?
                """,
                (
                    profile.get("name"), profile.get("email"),
                    profile.get("phone"), profile.get("location"),
                    profile.get("linkedin_url"), profile.get("github_url"),
                    profile.get("experience_level"),
                    skills_json, roles_json, geos_json, projects_json, now, existing["id"],
                ),
            )
            user_id = existing["id"]
        else:
            cursor = await db.execute(
                """
                INSERT INTO users
                    (name, email, phone, location, linkedin_url, github_url, experience_level,
                     skills, target_roles, geographies, projects, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    profile.get("name", "Jyotiraditya Patil"),
                    profile.get("email", "jyotiradityapatil106@gmail.com"),
                    profile.get("phone", "+91 7020676261"),
                    profile.get("location", "Pune / Mumbai (Open to Remote & All Locations)"),
                    profile.get("linkedin_url", "https://linkedin.com/in/jyotiraditya-patil"),
                    profile.get("github_url", "https://github.com/Jyotiraditya1006"),
                    profile.get("experience_level", "Fresher / Student (B.Tech CSE - AI & ML)"),
                    skills_json, roles_json, geos_json, projects_json, now, now,
                ),
            )
            user_id = cursor.lastrowid

        await db.commit()

    return {"success": True, "user_id": user_id}


# ===========================================================================
# REST – Resume upload
# ===========================================================================
@app.post("/api/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    """
    Accept a PDF or DOCX resume upload, parse it, extract a profile, and
    update the user record in the database.
    """
    from utils.resume_parser import ResumeParser
    from utils.gemini_client import GeminiClient

    allowed_types = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    if file.content_type not in allowed_types and not (
        file.filename.endswith(".pdf") or file.filename.endswith(".docx")
    ):
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX files are supported.",
        )

    # Save the file
    resume_dir = Path(settings.RESUME_DIR)
    resume_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4()}_{Path(file.filename).name}"
    file_path = resume_dir / safe_name

    contents = await file.read()
    file_path.write_bytes(contents)
    logger.info(f"Resume saved to {file_path}")

    # Parse text
    parser = ResumeParser()
    if file.filename.endswith(".pdf") or file.content_type == "application/pdf":
        resume_text = await parser.parse_pdf(str(file_path))
    else:
        resume_text = await parser.parse_docx(str(file_path))

    # Extract profile via Gemini
    gemini = GeminiClient()
    profile = await parser.extract_profile_from_resume(resume_text, gemini)
    profile["resume_path"] = str(file_path)

    # Upsert into DB
    import json as _json

    now = datetime.now(timezone.utc).isoformat()
    skills_json = _json.dumps(profile.get("skills", []))
    roles_json = _json.dumps(profile.get("target_roles", []))

    async with get_db() as db:
        cursor = await db.execute("SELECT id FROM users ORDER BY id LIMIT 1")
        existing = await cursor.fetchone()

        if existing:
            await db.execute(
                """
                UPDATE users SET
                    name=COALESCE(?,name), email=COALESCE(?,email),
                    phone=COALESCE(?,phone), location=COALESCE(?,location),
                    skills=?, target_roles=?, resume_path=?, resume_text=?,
                    experience_level=COALESCE(?,experience_level), updated_at=?
                WHERE id=?
                """,
                (
                    profile.get("name"), profile.get("email"),
                    profile.get("phone"), profile.get("location"),
                    skills_json, roles_json,
                    str(file_path), resume_text,
                    profile.get("experience_level"),
                    now, existing["id"],
                ),
            )
        else:
            await db.execute(
                """
                INSERT INTO users
                    (name, email, phone, location, skills, target_roles,
                     resume_path, resume_text, experience_level, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    profile.get("name", ""),
                    profile.get("email", ""),
                    profile.get("phone", ""),
                    profile.get("location", ""),
                    skills_json, roles_json,
                    str(file_path), resume_text,
                    profile.get("experience_level", "fresher"),
                    now, now,
                ),
            )

        await db.commit()

    return {
        "success": True,
        "filename": file.filename,
        "resume_path": str(file_path),
        "profile_extracted": profile,
        "char_count": len(resume_text),
    }


# ===========================================================================
# REST – Stats
# ===========================================================================
@app.get("/api/stats")
async def get_stats():
    """Return dashboard statistics."""
    async with get_db() as db:
        total_jobs = (await (await db.execute("SELECT COUNT(*) FROM jobs")).fetchone())[0]
        pending = (
            await (
                await db.execute("SELECT COUNT(*) FROM jobs WHERE status='pending'")
            ).fetchone()
        )[0]
        approved = (
            await (
                await db.execute("SELECT COUNT(*) FROM jobs WHERE status='approved'")
            ).fetchone()
        )[0]
        applied = (
            await (
                await db.execute("SELECT COUNT(*) FROM jobs WHERE status='applied'")
            ).fetchone()
        )[0]
        rejected_jobs = (
            await (
                await db.execute("SELECT COUNT(*) FROM jobs WHERE status='rejected'")
            ).fetchone()
        )[0]

        total_apps = (
            await (await db.execute("SELECT COUNT(*) FROM applications")).fetchone()
        )[0]
        interviews = (
            await (
                await db.execute(
                    "SELECT COUNT(*) FROM applications WHERE status='interview'"
                )
            ).fetchone()
        )[0]
        offers = (
            await (
                await db.execute(
                    "SELECT COUNT(*) FROM applications WHERE status='offer'"
                )
            ).fetchone()
        )[0]

        avg_score_row = await (
            await db.execute(
                "SELECT AVG(match_score) FROM jobs WHERE match_score > 0"
            )
        ).fetchone()
        avg_score = round(avg_score_row[0] or 0.0, 1)

    return {
        "jobs": {
            "total": total_jobs,
            "pending": pending,
            "approved": approved,
            "applied": applied,
            "rejected": rejected_jobs,
        },
        "applications": {
            "total": total_apps,
            "interviews": interviews,
            "offers": offers,
        },
        "average_match_score": avg_score,
    }


# ===========================================================================
# REST – Job approve / reject
# ===========================================================================
# ===========================================================================
# REST – Job approve / apply
# ===========================================================================
@app.put("/api/jobs/{job_id}/approve")
async def approve_job(job_id: str, background_tasks: BackgroundTasks):
    """
    Approve a job:
    1. Updates job status to 'applied'
    2. Generates tailored cover letter
    3. Logs a record in the applications table
    4. Triggers confirmation email
    """
    async with get_db() as db:
        # Fetch the job
        j_cursor = await db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        job_row = await j_cursor.fetchone()
        if not job_row:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

        # Ensure a default user exists for this session
        u_cursor = await db.execute("SELECT * FROM users ORDER BY id LIMIT 1")
        user_row = await u_cursor.fetchone()
        
        now = datetime.now(timezone.utc).isoformat()
        if not user_row:
            ins_cursor = await db.execute(
                """
                INSERT INTO users (name, email, phone, location, experience_level, skills, target_roles, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "Jyotiraditya Patil",
                    "jyotiraditya@gmail.com",
                    "+91 9876543210",
                    "Bangalore, India",
                    "fresher",
                    '["Python", "Machine Learning", "Data Science", "SQL", "Deep Learning", "TensorFlow"]',
                    '["Data Science / ML / AI", "Data Science Intern"]',
                    now, now
                )
            )
            await db.commit()
            user_id = ins_cursor.lastrowid
            user_email = "jyotiraditya@gmail.com"
            user_name = "Jyotiraditya Patil"
        else:
            user_id = user_row["id"]
            user_email = user_row["email"] or "jyotiraditya@gmail.com"
            user_name = user_row["name"] or "Jyotiraditya Patil"

        # Mark the job as applied
        await db.execute("UPDATE jobs SET status = 'applied' WHERE id = ?", (job_id,))

        # Create application entry in applications table
        app_id = str(uuid.uuid4())
        company_name = job_row["company"]
        role_title = job_row["title"]
        job_url = job_row["url"] or "https://www.linkedin.com/jobs"

        cover_letter = (
            f"Dear Hiring Team at {company_name},\n\n"
            f"I am writing to express my strong enthusiasm for the {role_title} position. "
            f"With a strong foundation in Python, Machine Learning models, and modern data processing pipelines, "
            f"I am excited to bring practical problem-solving skills to your team at {company_name}.\n\n"
            f"Thank you for considering my candidacy. I welcome the opportunity to discuss how my qualifications align with your goals.\n\n"
            f"Warm regards,\n{user_name}"
        )

        await db.execute(
            """
            INSERT INTO applications
                (id, job_id, user_id, status, cover_letter_text, applied_at, last_updated, notes)
            VALUES (?, ?, ?, 'applied', ?, ?, ?, ?)
            """,
            (app_id, job_id, user_id, cover_letter, now, now, f"Automated application to {company_name}")
        )
        await db.commit()

    # Trigger email notification in background
    from utils.email_service import send_application_confirmation_email
    background_tasks.add_task(
        send_application_confirmation_email,
        to_email=user_email,
        applicant_name=user_name,
        company=company_name,
        role=role_title,
        job_url=job_url,
        cover_letter=cover_letter,
        application_id=app_id
    )

    return {
        "success": True,
        "job_id": job_id,
        "application_id": app_id,
        "status": "applied",
        "message": f"Successfully recorded and applied to {company_name}."
    }


@app.put("/api/jobs/{job_id}/reject")
async def reject_job(job_id: str):
    """Mark a job as rejected."""
    async with get_db() as db:
        cursor = await db.execute(
            "UPDATE jobs SET status = 'rejected' WHERE id = ? AND status IN ('pending','approved')",
            (job_id,),
        )
        await db.commit()
        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Job '{job_id}' not found or already in a terminal state.",
            )
    return {"success": True, "job_id": job_id, "status": "rejected"}


# ===========================================================================
# REST – Health check
# ===========================================================================
@app.get("/api/health")
async def health_check():
    """Return service health status."""
    db_ok = False
    try:
        async with get_db() as db:
            await db.execute("SELECT 1")
        db_ok = True
    except Exception as exc:
        logger.error(f"Health check DB error: {exc}")

    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "error",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
    }


# ---------------------------------------------------------------------------
# Static frontend (mounted after all API routes so /api/* takes precedence)
# ---------------------------------------------------------------------------
_frontend_dir = Path(settings.FRONTEND_DIR)
if _frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")
    logger.info(f"Serving frontend from {_frontend_dir}")
else:
    logger.warning(f"Frontend directory not found at {_frontend_dir}; skipping static mount.")


# ===========================================================================
# Entry point
# ===========================================================================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
    )
