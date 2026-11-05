"""
agents/writer_agent.py - Resume tailoring, cover letter, and cold email generation.
"""
import logging

from utils.gemini_client import GeminiClient

logger = logging.getLogger(__name__)


class WriterAgent:
    """
    AI writing agent that produces tailored resumes, cover letters, and cold
    emails personalised to a specific job posting and company.
    """

    def __init__(self) -> None:
        self.gemini = GeminiClient()
        self._system = (
            "You are an expert technical writer and career coach specialising in "
            "Data Science, Machine Learning, and Software Engineering roles. "
            "You write in a professional yet warm, human voice. You NEVER use "
            "generic filler phrases like 'I am writing to express my interest'. "
            "Every piece you write is specific, compelling, and tailored."
        )
        logger.info("WriterAgent initialised.")

    # ------------------------------------------------------------------
    # Resume tailoring
    # ------------------------------------------------------------------

    async def tailor_resume(self, user_profile: dict, job: dict) -> str:
        """
        Rewrite the user's resume to emphasise qualifications most relevant
        to the given job posting.

        Parameters
        ----------
        user_profile : dict
            Must contain 'resume_text' (str) and profile fields.
        job : dict
            Job posting dict with title, company, description.

        Returns
        -------
        str
            Tailored resume in plain text format.
        """
        resume_text = user_profile.get("resume_text", "")
        if not resume_text.strip():
            logger.warning("tailor_resume: no resume_text in user_profile.")
            return ""

        job_title = job.get("title", "the role")
        job_company = job.get("company", "the company")
        job_desc = job.get("description", "")[:2500]

        prompt = (
            f"You are rewriting a resume to maximise fit for this job posting.\n\n"
            f"JOB TITLE   : {job_title}\n"
            f"COMPANY     : {job_company}\n"
            f"JOB DESCRIPTION:\n{job_desc}\n\n"
            f"ORIGINAL RESUME:\n{resume_text[:4000]}\n\n"
            "Instructions:\n"
            "- Reorder bullet points so the most relevant experience/skills appear first.\n"
            "- Reword bullets using keywords from the job description (ATS optimisation).\n"
            "- Keep all factual information 100% accurate — do NOT invent experience.\n"
            "- Maintain the same section structure (Summary, Skills, Experience, Education, Projects).\n"
            "- Keep it to one page equivalent (≤600 words).\n"
            "- Output ONLY the final resume text, no commentary."
        )

        try:
            tailored = await self.gemini.generate(prompt, system=self._system)
            logger.info(f"Tailored resume generated for '{job_title}' at '{job_company}'.")
            return tailored.strip()
        except Exception as exc:
            logger.error(f"tailor_resume failed: {exc}")
            return resume_text  # fall back to original

    # ------------------------------------------------------------------
    # Cover letter
    # ------------------------------------------------------------------

    async def write_cover_letter(self, user_profile: dict, job: dict) -> str:
        """
        Write a compelling, personalised cover letter for the job.

        Structure: hook paragraph → relevant experience paragraph →
        enthusiasm/fit paragraph + closing.

        Parameters
        ----------
        user_profile : dict
            User profile with name, skills, work_experience, projects fields.
        job : dict
            Job posting dict with title, company, description.

        Returns
        -------
        str
            Full cover letter text, ready to send.
        """
        name = user_profile.get("name", "Candidate")
        skills = ", ".join(user_profile.get("skills", [])[:10])
        github_url = user_profile.get("github_url", "https://github.com/Jyotiraditya1006")
        linkedin_url = user_profile.get("linkedin_url", "https://www.linkedin.com/in/jyotiraditya-patil-73b394274/")
        projects = user_profile.get("projects", [])
        if isinstance(projects, str):
            import json as _json
            try:
                projects = _json.loads(projects)
            except Exception:
                projects = []

        proj_summary = "; ".join(
            f"{p.get('title','')} (Tech: {', '.join(p.get('tech_stack', []))}) - {p.get('description','')}"
            for p in projects[:3]
        ) or "VehicleIQ (Real-time telemetry & LSTM failure prediction), LSTM Time-Series Forecasting, Customer Churn Classification"

        experiences = user_profile.get("work_experience", [])
        exp_summary = "; ".join(
            f"{e.get('title','')} at {e.get('company','')} ({e.get('duration','')})"
            for e in experiences[:3]
        ) or "Final-year B.Tech CSE (AI & Machine Learning) student with strong real-world open-source and deployed ML projects"

        job_title = job.get("title", "the role")
        job_company = job.get("company", "your company")
        job_desc = job.get("description", "")[:2000]

        prompt = (
            f"Write a compelling, human cover letter from {name} applying for the position of "
            f"'{job_title}' at '{job_company}'.\n\n"
            f"CANDIDATE LINKEDIN  : {linkedin_url}\n"
            f"CANDIDATE GITHUB    : {github_url}\n"
            f"CANDIDATE SKILLS    : {skills}\n"
            f"CANDIDATE PROJECTS  : {proj_summary}\n"
            f"CANDIDATE BACKGROUND: {exp_summary}\n\n"
            f"JOB DESCRIPTION:\n{job_desc}\n\n"
            "Cover letter requirements:\n"
            "1. PARAGRAPH 1 (Hook): Open with a punchy, enthusiastic hook tailored directly to "
            "   what {job_company} is building or needs. Never start with 'I am writing to apply for'.\n"
            "2. PARAGRAPH 2 (Technical Evidence): Emphasise 1-2 of candidate's actual projects "
            "   (like VehicleIQ for predictive ML / LSTM telemetry or Customer Churn / RecruitIQ) "
            "   explaining the technical architecture, problem solved, and how it directly transfers to this role.\n"
            "3. PARAGRAPH 3 (Cultural Fit & Call to Action): Express authentic passion for {job_company}'s mission. "
            "   Invite them to check out the live repos on GitHub and propose a quick conversation.\n"
            "- Tone: Natural, confident, conversational, humble yet technically accomplished. Zero buzzword fluff.\n"
            "- Length: 250-320 words.\n"
            f"- Sign off: 'Warm regards,\\n{name}\\nLinkedIn: {linkedin_url} | GitHub: {github_url}'\n"
            "- Output ONLY the letter text, no subject line or commentary."
        )

        try:
            letter = await self.gemini.generate(prompt, system=self._system)
            logger.info(f"Cover letter generated for '{job_title}' at '{job_company}'.")
            return letter.strip()
        except Exception as exc:
            logger.error(f"write_cover_letter failed: {exc}")
            return f"Dear Hiring Team at {job_company},\n\nI am thrilled to apply for the {job_title} role. Having built real-time deep learning and predictive ML systems like VehicleIQ (OBD-II telemetry + TensorFlow LSTM) and AI recruitment matching tools on my GitHub ({github_url}), I would love to bring this hands-on engineering mindset to your team.\n\nWarm regards,\n{name}\nLinkedIn: {linkedin_url} | GitHub: {github_url}"

    # ------------------------------------------------------------------
    # Cold email
    # ------------------------------------------------------------------

    async def draft_cold_email(
        self,
        user_profile: dict,
        job: dict,
        recruiter_name: str = None,
    ) -> str:
        """
        Draft a short, compelling cold email to a recruiter.

        Parameters
        ----------
        user_profile : dict
            User profile dict.
        job : dict
            Job posting dict.
        recruiter_name : str, optional
            Recruiter's name for personalisation.

        Returns
        -------
        str
            Cold email text including subject line.
        """
        name = user_profile.get("name", "Candidate")
        skills = ", ".join(user_profile.get("skills", [])[:6])
        github_url = user_profile.get("github_url", "https://github.com/Jyotiraditya1006")
        linkedin_url = user_profile.get("linkedin_url", "https://www.linkedin.com/in/jyotiraditya-patil-73b394274/")
        job_title = job.get("title", "the open role")
        job_company = job.get("company", "your company")
        greeting = f"Hi {recruiter_name}" if recruiter_name else "Hi there"

        prompt = (
            f"Draft a short, high-impact cold email from {name} to a hiring lead or recruiter at '{job_company}' "
            f"regarding the '{job_title}' role.\n\n"
            f"CANDIDATE LINKEDIN : {linkedin_url}\n"
            f"CANDIDATE GITHUB   : {github_url}\n"
            f"CANDIDATE SKILLS   : {skills}\n"
            f"FLAGSHIP PROJECT   : VehicleIQ (Real-time telemetry stream failure prediction using LSTM & FastAPI) & RecruitIQ (Next.js AI recruitment tool)\n\n"
            "Requirements:\n"
            f"- Greeting: '{greeting},'\n"
            "- 3-4 sentences total (excluding subject line and sign-off).\n"
            "- Sentence 1: Enthusiastic, clear intro mentioning interest in {job_title}.\n"
            "- Sentence 2: Concrete differentiator mentioning hands-on work with predictive ML/LSTMs or telemetry from GitHub ({github_url}).\n"
            "- Sentence 3-4: Low-friction call to action (e.g. 'Would you be open to a 10-minute chat this week?').\n"
            f"- Subject line format: 'Subject: {job_title} | {name} – ML & Deep Learning projects'\n"
            f"- End with: 'Best regards,\\n{name}\\nLinkedIn: {linkedin_url} | GitHub: {github_url}'\n"
            "- Tone: Confident, respectful, concise, engineer-to-engineer. No generic corporate buzzwords.\n"
            "- Output ONLY the email (subject line + body), no extra commentary."
        )

        try:
            email = await self.gemini.generate(prompt, system=self._system)
            logger.info(f"Cold email drafted for '{job_title}' at '{job_company}'.")
            return email.strip()
        except Exception as exc:
            logger.error(f"draft_cold_email failed: {exc}")
            return (
                f"Subject: {job_title} – {name}\n\n"
                f"{greeting},\n\n"
                f"I'd love to discuss the {job_title} opportunity at {job_company}.\n\n"
                f"Best,\n{name}"
            )
