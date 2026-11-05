"""
agents/tracker_agent.py - Application lifecycle tracking with Gemini-generated reports.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import List

from database.models import get_db
from utils.gemini_client import GeminiClient

logger = logging.getLogger(__name__)


class TrackerAgent:
    """
    Manages the full lifecycle of job applications stored in SQLite,
    and uses Gemini to generate human-readable weekly summary reports.
    """

    def __init__(self) -> None:
        self.gemini = GeminiClient()
        logger.info("TrackerAgent initialised.")

    # ------------------------------------------------------------------
    # Application creation
    # ------------------------------------------------------------------

    async def log_application(
        self,
        job_id: str,
        user_id: int,
        cover_letter: str = "",
        resume_path: str = "",
    ) -> str:
        """
        Create a new application record in the database.

        Parameters
        ----------
        job_id : str
            UUID of the job being applied to.
        user_id : int
            ID of the user applying.
        cover_letter : str
            Cover letter text to store.
        resume_path : str
            File path of the tailored resume (if any).

        Returns
        -------
        str
            The newly created application UUID.
        """
        application_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        async with get_db() as db:
            await db.execute(
                """
                INSERT INTO applications
                    (id, job_id, user_id, status, cover_letter_text,
                     tailored_resume_path, applied_at, last_updated)
                VALUES (?, ?, ?, 'applied', ?, ?, ?, ?)
                """,
                (application_id, job_id, user_id, cover_letter, resume_path, now, now),
            )
            # Mark the job as applied
            await db.execute(
                "UPDATE jobs SET status = 'applied' WHERE id = ?",
                (job_id,),
            )
            await db.commit()

        logger.info(f"Application {application_id} logged for job {job_id}.")
        return application_id

    # ------------------------------------------------------------------
    # Status management
    # ------------------------------------------------------------------

    async def update_status(self, application_id: str, new_status: str) -> bool:
        """
        Update the status of an existing application.

        Parameters
        ----------
        application_id : str
            UUID of the application to update.
        new_status : str
            One of: applied, in_review, interview, rejected, offer.

        Returns
        -------
        bool
            True if a row was updated, False otherwise.
        """
        valid_statuses = {"applied", "in_review", "interview", "rejected", "offer"}
        if new_status not in valid_statuses:
            logger.warning(f"Invalid status '{new_status}' for application {application_id}.")
            return False

        now = datetime.now(timezone.utc).isoformat()
        async with get_db() as db:
            cursor = await db.execute(
                "UPDATE applications SET status = ?, last_updated = ? WHERE id = ?",
                (new_status, now, application_id),
            )
            await db.commit()
            updated = cursor.rowcount > 0

        if updated:
            logger.info(f"Application {application_id} status → '{new_status}'.")
        else:
            logger.warning(f"Application {application_id} not found for status update.")
        return updated

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    async def get_all_applications(self, user_id: int) -> List[dict]:
        """
        Fetch all applications for a user, joined with job details.

        Parameters
        ----------
        user_id : int
            The user whose applications to retrieve.

        Returns
        -------
        list[dict]
            List of application dicts including job title, company, etc.
        """
        async with get_db() as db:
            cursor = await db.execute(
                """
                SELECT
                    a.id,
                    a.job_id,
                    a.user_id,
                    a.status,
                    a.cover_letter_text,
                    a.tailored_resume_path,
                    a.applied_at,
                    a.last_updated,
                    a.notes,
                    j.title        AS job_title,
                    j.company      AS job_company,
                    j.location     AS job_location,
                    j.platform     AS job_platform,
                    j.url          AS job_url,
                    j.match_score  AS job_match_score
                FROM applications a
                JOIN jobs j ON a.job_id = j.id
                WHERE a.user_id = ?
                ORDER BY a.applied_at DESC
                """,
                (user_id,),
            )
            rows = await cursor.fetchall()

        return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    async def generate_weekly_report(self, user_id: int) -> str:
        """
        Generate a Gemini-written, human-readable weekly applications summary.

        Parameters
        ----------
        user_id : int
            The user to generate the report for.

        Returns
        -------
        str
            Readable report text (Markdown-formatted).
        """
        applications = await self.get_all_applications(user_id)

        if not applications:
            return (
                "# Weekly Job Search Report\n\n"
                "No applications found yet. Start by asking me to search for jobs!\n"
            )

        # Build a concise summary table for the prompt
        lines = []
        for app in applications:
            lines.append(
                f"- {app['job_title']} @ {app['job_company']} | "
                f"Status: {app['status']} | Applied: {app.get('applied_at','')[:10]}"
            )
        summary_text = "\n".join(lines)

        # Counts by status
        from collections import Counter
        status_counts = Counter(a["status"] for a in applications)

        prompt = (
            "You are a career coach writing a friendly, motivating weekly job search "
            "progress report. Use Markdown formatting.\n\n"
            f"TOTAL APPLICATIONS: {len(applications)}\n"
            f"STATUS BREAKDOWN  : {dict(status_counts)}\n\n"
            f"APPLICATION LIST:\n{summary_text}\n\n"
            "Write a report with these sections:\n"
            "1. 📊 This Week at a Glance (key numbers)\n"
            "2. 🏆 Highlights (any interviews, offers, or strong matches)\n"
            "3. 💡 Observations & Patterns (what's working, what to improve)\n"
            "4. 🎯 Recommended Next Steps (3 concrete action items)\n"
            "5. 💪 Motivational closing (1-2 sentences, warm and genuine)\n\n"
            "Tone: Warm, honest, encouraging. No corporate fluff."
        )

        try:
            report = await self.gemini.generate(prompt)
            logger.info(f"Weekly report generated for user {user_id}.")
            return report.strip()
        except Exception as exc:
            logger.error(f"generate_weekly_report failed: {exc}")
            return (
                f"# Weekly Report\n\n"
                f"You have **{len(applications)}** total applications.\n\n"
                f"Status breakdown: {dict(status_counts)}\n"
            )
