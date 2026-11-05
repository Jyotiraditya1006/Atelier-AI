"""
agents/orchestrator.py - Main conversational AI orchestrator (Alex the career coach).

Manages per-session conversation history, dispatches tool calls, and streams
Gemini responses token-by-token over a FastAPI WebSocket connection.
"""
import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import WebSocket

from database.models import get_db
from utils.gemini_client import GeminiClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt for the orchestrator persona "Alex"
# ---------------------------------------------------------------------------
ALEX_SYSTEM_PROMPT = """You are Alex, an expert AI career coach and job application assistant.

You're helping a fresh Data Science / ML graduate land their first job or internship.
You're warm, encouraging, strategic, and genuinely excited about their success.

Your personality:
- Speak naturally and conversationally, like a knowledgeable friend — not a corporate bot.
- Celebrate wins (even small ones) with genuine enthusiasm.
- Provide emotional support and reframe rejections as learning opportunities.
- Always be proactive: suggest the next logical step without waiting to be asked.
- Use emojis sparingly but naturally (1-2 per message max).

Your capabilities (tools you can call):
1. search_jobs(query, platforms)       – Search for relevant job postings
2. get_job_matches()                   – Retrieve top-scored job matches
3. draft_application(job_id)           – Generate tailored resume + cover letter for a job
4. get_application_status()            – Show current application tracker
5. update_profile(profile_data)        – Update the user's profile
6. analyze_resume(resume_text)         – Analyse an uploaded resume

Trigger rules:
- If user says "start", "find jobs", "search jobs", "look for jobs" → call search_jobs
- If user asks about applications, status, progress → call get_application_status
- If user asks to apply to a specific job → call draft_application
- If user uploads a resume or shares resume text → call analyze_resume
- Always confirm tool actions with a brief human-sounding explanation before showing results.

IMPORTANT: When you decide to call a tool, respond ONLY with a JSON object in this exact format:
{"tool": "<tool_name>", "args": {<args>}}
Otherwise respond with normal conversational text. Never mix tool JSON with prose in one response.
"""


class OrchestratorAgent:
    """
    Stateful conversational agent that:
    - Maintains per-session chat history in memory and SQLite.
    - Decides whether to respond conversationally or invoke a tool.
    - Streams Gemini responses to the WebSocket client.
    - Delegates tool execution to specialist agents.
    """

    def __init__(self) -> None:
        self.gemini = GeminiClient()
        # session_id -> List[{"role": str, "parts": [str]}]
        self._history: Dict[str, List[Dict[str, Any]]] = {}
        logger.info("OrchestratorAgent initialised.")

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def chat(
        self,
        session_id: str,
        user_message: str,
        websocket: WebSocket,
    ) -> None:
        """
        Process a user message and stream the response to the WebSocket.

        Protocol:
          {"type": "chunk",     "content": "...", "agent": "Orchestrator"}  – streamed text
          {"type": "tool_call", "tool":    "...", "agent": "Orchestrator"}  – tool invoked
          {"type": "done",      "agent":   "Orchestrator", "data": {...}}   – completion
          {"type": "error",     "content": "...", "agent": "Orchestrator"}  – on failure
        """
        # Initialise history for new sessions
        if session_id not in self._history:
            self._history[session_id] = []

        # Persist user message
        await self._save_message(session_id, "user", user_message)
        self._history[session_id].append({"role": "user", "content": user_message})

        # Build the full prompt including history context
        full_prompt = self._build_prompt(session_id, user_message)

        try:
            # --- First pass: collect full response to detect tool calls ---
            full_response = await self.gemini.generate(full_prompt, system=ALEX_SYSTEM_PROMPT)
            full_response = full_response.strip()

            # --- Detect tool call ---
            tool_result_data: Dict[str, Any] = {}
            tool_called: Optional[str] = None

            if full_response.startswith("{") and '"tool"' in full_response:
                tool_called, tool_result_data = await self._handle_tool_call(
                    full_response, session_id, websocket
                )
                # Generate a follow-up human response based on tool results
                full_response = await self._generate_tool_followup(
                    session_id, tool_called, tool_result_data, user_message
                )

            # --- Stream the final text response ---
            await self._stream_text(full_response, websocket)

            # Persist assistant message
            await self._save_message(session_id, "assistant", full_response, "Orchestrator")
            self._history[session_id].append(
                {"role": "assistant", "content": full_response}
            )

            # Send completion signal
            await websocket.send_json({
                "type": "done",
                "agent": "Orchestrator",
                "data": {
                    "tool_called": tool_called,
                    "tool_data": tool_result_data,
                },
            })

        except Exception as exc:
            logger.error(f"OrchestratorAgent.chat error (session={session_id}): {exc}")
            try:
                await websocket.send_json({
                    "type": "error",
                    "content": "I ran into a problem. Please try again in a moment.",
                    "agent": "Orchestrator",
                })
            except Exception:
                pass  # WebSocket may already be closed

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    def _build_prompt(self, session_id: str, user_message: str) -> str:
        """Build a prompt that includes recent conversation history."""
        history = self._history.get(session_id, [])
        # Keep last 10 turns to stay within token limits
        recent = history[-20:]

        history_text = ""
        for turn in recent[:-1]:  # exclude the message we just appended
            role_label = "User" if turn["role"] == "user" else "Alex"
            history_text += f"{role_label}: {turn['content']}\n"

        return (
            f"{history_text}"
            f"User: {user_message}\n"
            "Alex:"
        )

    # ------------------------------------------------------------------
    # Text streaming helper
    # ------------------------------------------------------------------

    async def _stream_text(self, text: str, websocket: WebSocket) -> None:
        """Simulate streaming by sending the response in word-sized chunks."""
        words = text.split(" ")
        buffer = ""
        for i, word in enumerate(words):
            buffer += word + (" " if i < len(words) - 1 else "")
            # Send every ~5 words as a chunk
            if (i + 1) % 5 == 0 or i == len(words) - 1:
                await websocket.send_json({
                    "type": "chunk",
                    "content": buffer,
                    "agent": "Orchestrator",
                })
                buffer = ""
                await asyncio.sleep(0.02)  # small delay for natural streaming feel

    # ------------------------------------------------------------------
    # Tool dispatch
    # ------------------------------------------------------------------

    async def _handle_tool_call(
        self,
        raw_json: str,
        session_id: str,
        websocket: WebSocket,
    ) -> tuple[str, Dict[str, Any]]:
        """
        Parse the tool JSON, notify the client, and execute the tool.

        Returns (tool_name, result_data).
        """
        try:
            parsed = json.loads(raw_json)
        except json.JSONDecodeError:
            # Try to extract JSON substring
            start = raw_json.find("{")
            end = raw_json.rfind("}") + 1
            parsed = json.loads(raw_json[start:end])

        tool_name: str = parsed.get("tool", "unknown")
        tool_args: dict = parsed.get("args", {})

        # Notify client
        await websocket.send_json({
            "type": "tool_call",
            "tool": tool_name,
            "agent": "Orchestrator",
        })

        result = await self._execute_tool(tool_name, tool_args, session_id)
        return tool_name, result

    async def _execute_tool(
        self,
        tool_name: str,
        args: dict,
        session_id: str,
    ) -> Dict[str, Any]:
        """Route tool name to the appropriate handler."""
        handlers = {
            "search_jobs": self._tool_search_jobs,
            "get_job_matches": self._tool_get_job_matches,
            "draft_application": self._tool_draft_application,
            "get_application_status": self._tool_get_application_status,
            "update_profile": self._tool_update_profile,
            "analyze_resume": self._tool_analyze_resume,
        }
        handler = handlers.get(tool_name)
        if handler is None:
            logger.warning(f"Unknown tool requested: '{tool_name}'")
            return {"error": f"Unknown tool: {tool_name}"}
        try:
            return await handler(args, session_id)
        except Exception as exc:
            logger.error(f"Tool '{tool_name}' execution failed: {exc}")
            return {"error": str(exc)}

    # ------------------------------------------------------------------
    # Individual tool implementations
    # ------------------------------------------------------------------

    async def _tool_search_jobs(self, args: dict, session_id: str) -> dict:
        """Trigger job scraping and return populated listings status."""
        query = args.get("query", "Data Science internship")
        platforms = args.get("platforms", ["linkedin", "internshala", "naukri", "indeed", "wellfound"])
        logger.info(f"Tool search_jobs: query='{query}', platforms={platforms}")
        count = 0
        try:
            from scrapers.scraper_manager import ScraperManager
            async with ScraperManager() as manager:
                job_listings = await manager.search_all(query, platforms=platforms, limit_per_platform=3)
            
            now = datetime.now(timezone.utc).isoformat()
            async with get_db() as db:
                for j in job_listings:
                    await db.execute(
                        """
                        INSERT OR IGNORE INTO jobs
                            (id, title, company, location, platform, url, description,
                             salary_range, job_type, match_score, status, scraped_at)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            j.id, j.title, j.company, j.location, j.platform,
                            j.url, j.description, j.salary_range, j.job_type,
                            85.0, "pending", now
                        )
                    )
                await db.commit()
            count = len(job_listings)
        except Exception as err:
            logger.error(f"Error in _tool_search_jobs: {err}")

        return {
            "status": "completed",
            "query": query,
            "jobs_found": count,
            "platforms": platforms,
            "message": f"Successfully scraped {count} relevant jobs across selected platforms! I have added them to your Jobs dashboard."
        }

    async def _tool_get_job_matches(self, args: dict, session_id: str) -> dict:
        """Return top 10 pending jobs ordered by match_score."""
        async with get_db() as db:
            cursor = await db.execute(
                """
                SELECT id, title, company, location, platform, url,
                       match_score, status, job_type, salary_range
                FROM jobs
                WHERE status = 'pending'
                ORDER BY match_score DESC
                LIMIT 10
                """
            )
            rows = await cursor.fetchall()
        jobs = [dict(row) for row in rows]
        return {"jobs": jobs, "count": len(jobs)}

    async def _tool_draft_application(self, args: dict, session_id: str) -> dict:
        """Generate a tailored cover letter and resume for a specific job."""
        from agents.writer_agent import WriterAgent
        from agents.tracker_agent import TrackerAgent

        job_id: str = args.get("job_id", "")
        if not job_id:
            return {"error": "job_id is required"}

        async with get_db() as db:
            cursor = await db.execute(
                "SELECT * FROM jobs WHERE id = ?", (job_id,)
            )
            job_row = await cursor.fetchone()
            user_cursor = await db.execute(
                "SELECT * FROM users ORDER BY id LIMIT 1"
            )
            user_row = await user_cursor.fetchone()

        if not job_row:
            return {"error": f"Job {job_id} not found in database."}
        if not user_row:
            return {"error": "No user profile found. Please create your profile first."}

        job = dict(job_row)
        user = dict(user_row)

        import json as _json
        user["skills"] = _json.loads(user.get("skills", "[]"))
        user["target_roles"] = _json.loads(user.get("target_roles", "[]"))

        writer = WriterAgent()
        cover_letter = await writer.write_cover_letter(user, job)
        tailored_resume = await writer.tailor_resume(user, job)

        tracker = TrackerAgent()
        application_id = await tracker.log_application(
            job_id=job_id,
            user_id=user["id"],
            cover_letter=cover_letter,
        )

        return {
            "application_id": application_id,
            "job_title": job.get("title"),
            "company": job.get("company"),
            "cover_letter": cover_letter,
            "tailored_resume": tailored_resume,
        }

    async def _tool_get_application_status(self, args: dict, session_id: str) -> dict:
        """Return all applications for the first user (single-user MVP)."""
        from agents.tracker_agent import TrackerAgent

        async with get_db() as db:
            cursor = await db.execute("SELECT id FROM users ORDER BY id LIMIT 1")
            row = await cursor.fetchone()

        if not row:
            return {"applications": [], "message": "No user profile found."}

        tracker = TrackerAgent()
        applications = await tracker.get_all_applications(row["id"])
        return {"applications": applications, "count": len(applications)}

    async def _tool_update_profile(self, args: dict, session_id: str) -> dict:
        """Upsert user profile fields supplied in args."""
        profile_data: dict = args.get("profile_data", args)
        import json as _json

        async with get_db() as db:
            # Check if user exists
            cursor = await db.execute("SELECT id FROM users ORDER BY id LIMIT 1")
            row = await cursor.fetchone()

            skills_json = _json.dumps(profile_data.get("skills", []))
            roles_json = _json.dumps(profile_data.get("target_roles", []))
            geos_json = _json.dumps(profile_data.get("geographies", []))
            now = datetime.now(timezone.utc).isoformat()

            if row:
                await db.execute(
                    """
                    UPDATE users SET
                        name=COALESCE(?,name), email=COALESCE(?,email),
                        phone=COALESCE(?,phone), location=COALESCE(?,location),
                        experience_level=COALESCE(?,experience_level),
                        skills=?, target_roles=?, geographies=?, updated_at=?
                    WHERE id=?
                    """,
                    (
                        profile_data.get("name"), profile_data.get("email"),
                        profile_data.get("phone"), profile_data.get("location"),
                        profile_data.get("experience_level"),
                        skills_json, roles_json, geos_json, now, row["id"],
                    ),
                )
                user_id = row["id"]
            else:
                cursor = await db.execute(
                    """
                    INSERT INTO users (name, email, phone, location, experience_level,
                                       skills, target_roles, geographies, created_at, updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        profile_data.get("name", ""), profile_data.get("email", ""),
                        profile_data.get("phone", ""), profile_data.get("location", ""),
                        profile_data.get("experience_level", "fresher"),
                        skills_json, roles_json, geos_json, now, now,
                    ),
                )
                user_id = cursor.lastrowid

            await db.commit()

        return {"success": True, "user_id": user_id}

    async def _tool_analyze_resume(self, args: dict, session_id: str) -> dict:
        """Extract profile from raw resume text and upsert into the users table."""
        from utils.resume_parser import ResumeParser

        resume_text: str = args.get("resume_text", "")
        if not resume_text.strip():
            return {"error": "resume_text is required"}

        parser = ResumeParser()
        profile = await parser.extract_profile_from_resume(resume_text, self.gemini)

        # Persist to DB via update_profile tool
        await self._tool_update_profile(profile, session_id)

        return {"profile": profile, "message": "Resume analysed and profile updated."}

    # ------------------------------------------------------------------
    # Follow-up generation after tool execution
    # ------------------------------------------------------------------

    async def _generate_tool_followup(
        self,
        session_id: str,
        tool_name: str,
        tool_data: dict,
        original_message: str,
    ) -> str:
        """Ask Gemini to formulate a natural-language response based on tool output."""
        data_summary = json.dumps(tool_data, indent=2)[:2000]  # cap size

        prompt = (
            f"The user said: \"{original_message}\"\n\n"
            f"You (Alex) called the tool '{tool_name}' and got this result:\n"
            f"{data_summary}\n\n"
            "Now write a warm, conversational reply to the user summarising what happened "
            "and suggesting the next step. Sound like Alex the career coach, not a system log. "
            "Keep it concise (2-4 sentences)."
        )

        try:
            return await self.gemini.generate(prompt, system=ALEX_SYSTEM_PROMPT)
        except Exception as exc:
            logger.error(f"_generate_tool_followup failed: {exc}")
            return "Done! Let me know what you'd like to do next."

    # ------------------------------------------------------------------
    # DB persistence
    # ------------------------------------------------------------------

    async def _save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        agent_name: str = "User",
    ) -> None:
        """Persist a conversation message to the agent_messages table."""
        try:
            async with get_db() as db:
                await db.execute(
                    """
                    INSERT INTO agent_messages (session_id, role, agent_name, content)
                    VALUES (?, ?, ?, ?)
                    """,
                    (session_id, role, agent_name, content),
                )
                await db.commit()
        except Exception as exc:
            logger.error(f"Failed to save message to DB: {exc}")
