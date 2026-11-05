"""
agents/matcher_agent.py - Job-to-profile matching agent powered by Gemini.
"""
import logging
from typing import Optional

from utils.gemini_client import GeminiClient

logger = logging.getLogger(__name__)


class MatcherAgent:
    """
    Scores a job posting against a user profile using Gemini-assisted analysis.

    The scoring methodology weighs four dimensions:
      - Skill match       : overlap between job requirements and user skills
      - Experience match  : seniority alignment
      - Location match    : geography / remote preference alignment
      - Overall fit       : holistic AI-judged score (acts as tie-breaker)
    """

    def __init__(self) -> None:
        self.gemini = GeminiClient()
        logger.info("MatcherAgent initialised.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def score_job(self, job: dict, user_profile: dict) -> dict:
        """
        Score a single job posting against the user profile.

        Parameters
        ----------
        job:
            Job dict with at minimum: title, company, description, job_type,
            location (all strings).
        user_profile:
            User profile dict with: skills (list), experience_level (str),
            geographies (list), target_roles (list).

        Returns
        -------
        dict
            Keys:
              score (float 0-100), skill_match_pct (float), experience_match (bool),
              location_match (bool), reasoning (str), key_requirements (list[str]),
              salary_mentioned (str | None), job_type (str)
        """
        schema = {
            "score": "number (0-100)",
            "skill_match_pct": "number (0-100)",
            "experience_match": "boolean",
            "location_match": "boolean",
            "reasoning": "string (2-3 sentences explaining the score)",
            "key_requirements": ["list of key skill/requirement strings extracted from JD"],
            "salary_mentioned": "string or null",
            "job_type": "string",
        }

        prompt = self._build_scoring_prompt(job, user_profile)

        try:
            result = await self.gemini.generate_json(prompt, schema)
        except Exception as exc:
            logger.error(f"MatcherAgent.score_job failed: {exc}")
            result = {}

        # Normalise and guarantee all keys exist
        return {
            "score": self._clamp(result.get("score", 0.0)),
            "skill_match_pct": self._clamp(result.get("skill_match_pct", 0.0)),
            "experience_match": bool(result.get("experience_match", False)),
            "location_match": bool(result.get("location_match", False)),
            "reasoning": result.get("reasoning", "Unable to generate reasoning."),
            "key_requirements": result.get("key_requirements", []),
            "salary_mentioned": result.get("salary_mentioned"),
            "job_type": result.get("job_type", job.get("job_type", "unknown")),
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_scoring_prompt(self, job: dict, user_profile: dict) -> str:
        user_skills = ", ".join(user_profile.get("skills", [])) or "Not specified"
        user_exp = user_profile.get("experience_level", "fresher")
        user_geos = ", ".join(user_profile.get("geographies", [])) or "Any"
        target_roles = ", ".join(user_profile.get("target_roles", [])) or "Not specified"

        job_title = job.get("title", "Unknown")
        job_company = job.get("company", "Unknown")
        job_location = job.get("location", "Unknown")
        job_type = job.get("job_type", "unknown")
        job_desc = job.get("description", "")[:3000]  # cap to avoid token overflow

        return (
            "You are an expert technical recruiter and career advisor. "
            "Score the following job against the candidate profile on a scale of 0-100.\n\n"
            "--- CANDIDATE PROFILE ---\n"
            f"Experience Level : {user_exp}\n"
            f"Skills           : {user_skills}\n"
            f"Target Roles     : {target_roles}\n"
            f"Preferred Locations: {user_geos}\n\n"
            "--- JOB POSTING ---\n"
            f"Title    : {job_title}\n"
            f"Company  : {job_company}\n"
            f"Location : {job_location}\n"
            f"Type     : {job_type}\n"
            f"Description:\n{job_desc}\n\n"
            "Evaluate:\n"
            "1. skill_match_pct: What % of job requirements match candidate skills?\n"
            "2. experience_match: Does the seniority level match?\n"
            "3. location_match: Does job location match candidate geography preferences?\n"
            "4. score: Overall fit score (0-100). Weight skill_match_pct most heavily.\n"
            "5. key_requirements: Extract the top 5-8 technical/skill requirements.\n"
            "6. salary_mentioned: Extract salary/stipend if present, else null.\n"
            "7. reasoning: Brief explanation of the score."
        )

    @staticmethod
    def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
        try:
            return max(lo, min(hi, float(value)))
        except (TypeError, ValueError):
            return 0.0
