"""
utils/gemini_client.py - Singleton Gemini API client with retry logic and streaming support.
"""
import asyncio
import json
import logging
from typing import AsyncGenerator, Optional

import google.generativeai as genai

from config import settings

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 1.0  # seconds


class GeminiClient:
    """
    Thread-safe singleton wrapper around the Google Generative AI SDK.

    Supports plain generation, streaming generation, and JSON-schema-constrained
    generation, all with exponential-backoff retry logic.
    """

    _instance: Optional["GeminiClient"] = None

    def __new__(cls) -> "GeminiClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self.has_key = bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your_gemini_api_key_here")
        if self.has_key:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self._model_name = "gemini-2.0-flash"
            logger.info(f"GeminiClient initialised with model '{self._model_name}'.")
        else:
            self._model_name = "demo-fallback"
            logger.warning("GEMINI_API_KEY not configured. Running with intelligent local response fallback.")
        self._initialized = True

    def _get_model(self, system: Optional[str] = None) -> Optional[genai.GenerativeModel]:
        """Return a GenerativeModel, optionally with a system instruction."""
        if not self.has_key:
            return None
        kwargs: dict = {"model_name": self._model_name}
        if system:
            kwargs["system_instruction"] = system
        return genai.GenerativeModel(**kwargs)

    async def generate(self, prompt: str, system: Optional[str] = None) -> str:
        """
        Generate a complete text response for *prompt*.
        Retries up to _MAX_RETRIES times with exponential back-off, or returns intelligent fallback.
        """
        if not self.has_key:
            return self._fallback_response(prompt)
        last_exc: Optional[Exception] = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                model = self._get_model(system)
                response = await asyncio.to_thread(model.generate_content, prompt)
                return response.text
            except Exception as exc:
                last_exc = exc
                delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    f"Gemini generate attempt {attempt}/{_MAX_RETRIES} failed: {exc}. "
                    f"Retrying in {delay:.1f}s…"
                )
                await asyncio.sleep(delay)
        raise RuntimeError(
            f"Gemini generate failed after {_MAX_RETRIES} attempts: {last_exc}"
        )

    async def stream_generate(
        self, prompt: str, system: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream text chunks for *prompt*.

        Yields individual text chunks as they arrive from the API.
        Retries the *entire* stream up to _MAX_RETRIES times on failure.
        """
        last_exc: Optional[Exception] = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                model = self._get_model(system)
                # SDK streaming must run in a thread since it's synchronous internally.
                response_stream = await asyncio.to_thread(
                    model.generate_content, prompt, stream=True
                )
                for chunk in response_stream:
                    if chunk.text:
                        yield chunk.text
                return  # success – exit retry loop
            except Exception as exc:
                last_exc = exc
                delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    f"Gemini stream attempt {attempt}/{_MAX_RETRIES} failed: {exc}. "
                    f"Retrying in {delay:.1f}s…"
                )
                await asyncio.sleep(delay)
        raise RuntimeError(
            f"Gemini stream_generate failed after {_MAX_RETRIES} attempts: {last_exc}"
        )

    async def generate_json(self, prompt: str, schema: Optional[dict] = None) -> dict:
        """
        Generate a response expected to be valid JSON.

        Appends a schema hint to the prompt when *schema* is provided, then
        parses and returns the JSON object.  Falls back to an empty dict on
        parse errors after exhausting retries.
        """
        schema_hint = ""
        if schema:
            schema_hint = (
                f"\n\nRespond ONLY with valid JSON matching this schema:\n"
                f"{json.dumps(schema, indent=2)}"
            )
        full_prompt = prompt + schema_hint + "\n\nOutput ONLY the raw JSON object, no markdown fences."

        raw = await self.generate(full_prompt)

        # Strip optional markdown code fences
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip().rstrip("`").strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.error(f"Failed to parse Gemini JSON response: {exc}\nRaw: {raw[:500]}")
            return {}

    def _fallback_response(self, prompt: str) -> str:
        """Intelligent, empathetic human-like response handler."""
        import re
        lower = prompt.lower()

        # Cover letter generation
        if "cover letter" in lower:
            return (
                "Dear Hiring Team,\n\n"
                "I am thrilled to submit my application. As a final-year B.Tech CSE (AI & Machine Learning) student with a passion for deploying reliable predictive systems, I have built real-world end-to-end architectures including VehicleIQ (processing OBD-II telemetry streams with TensorFlow LSTM models and FastAPI for real-time failure prediction) and full-stack AI recruitment platforms like RecruitIQ (live at recruit-iq-nu.vercel.app).\n\n"
                "My technical foundation centers around Python, PyTorch, TensorFlow, Scikit-Learn, and time-series forecasting. Whether training deep learning models or engineering performant REST APIs with Next.js dashboards, I focus on transforming complex data into robust, production-grade solutions. You can explore my full portfolio and open-source implementations at https://github.com/Jyotiraditya1006.\n\n"
                "I would love the opportunity to contribute this hands-on engineering mindset to your engineering team. Thank you for your time, and I look forward to connecting.\n\n"
                "Warm regards,\n"
                "Jyotiraditya Patil\n"
                "LinkedIn: https://www.linkedin.com/in/jyotiraditya-patil-73b394274/ | GitHub: https://github.com/Jyotiraditya1006 | Email: jyotiradityapatil106@gmail.com"
            )

        # Cold email outreach
        if "cold email" in lower:
            return (
                "Subject: Application & ML Projects — Jyotiraditya Patil\n\n"
                "Hi there,\n\n"
                "I came across the open role on your team and wanted to reach out directly. I am a final-year AI & Machine Learning engineer who has built real-world predictive ML systems—most notably VehicleIQ (OBD-II telemetry stream failure prediction with TensorFlow LSTM & FastAPI) and live web tools on GitHub (https://github.com/Jyotiraditya1006).\n\n"
                "Given your team's focus on scalable machine learning and data engineering, I would love to connect for 10 minutes to learn more about the challenges you're tackling and see if my background is a good fit.\n\n"
                "Best regards,\n"
                "Jyotiraditya Patil\n"
                "LinkedIn: https://www.linkedin.com/in/jyotiraditya-patil-73b394274/ | GitHub: https://github.com/Jyotiraditya1006"
            )

        # Tool calls
        if any(w in lower for w in ["find jobs", "search jobs", "look for jobs", "hunt for", "openings", "scout"]):
            return '{"tool": "search_jobs", "args": {"query": "Data Science / ML intern", "platforms": ["linkedin", "internshala", "naukri", "indeed", "wellfound"]}}'
        if any(w in lower for w in ["status", "how are my applications", "any update", "tracker"]):
            return '{"tool": "get_application_status", "args": {}}'
        if any(w in lower for w in ["recommend", "top matches", "best jobs", "what should i apply"]):
            return '{"tool": "get_job_matches", "args": {}}'
        if any(w in lower for w in ["start", "go", "let's do it", "ready", "begin"]):
            return '{"tool": "search_jobs", "args": {"query": "Data Science / Machine Learning intern", "platforms": ["linkedin", "internshala", "naukri", "indeed", "wellfound"]}}'

        # Conversational greetings
        if re.search(r'\b(hello|hi|hey|good morning|good evening|sup)\b', lower):
            return (
                "Hey there! Great to see you. How are you feeling about the job hunt today? "
                "I'm all set to run a search across LinkedIn, Internshala, and Naukri, "
                "or we can review and tailor your application materials. Just tell me what's on your mind!"
            )

        if any(w in lower for w in ["anxious", "nervous", "stressed", "tired", "hard"]):
            return (
                "I hear you completely. Breaking into Data Science & ML is definitely competitive, and it's totally normal to feel the pressure. "
                "The secret is consistency and targeted quality over spamming. We're going to tailor every single application so hiring managers actually notice you. "
                "Take a breath — you've got the skills, and I'm handling the heavy lifting. Want to look at a couple of high-match internships to get some momentum going?"
            )

        if any(w in lower for w in ["resume", "cv", "ats"]):
            return (
                "Your resume is your ticket to the interview room! You can drop your PDF or DOCX file right in the **Resume tab** (or attach it here in chat). "
                "I'll scan it for ATS keyword gaps, highlight your strongest ML projects, and ensure recruiters see your impact immediately. Want to upload it now?"
            )

        return (
            "I'm right with you! We can search fresh Data Science / ML openings across 5 major platforms, "
            "review your current applications, or craft personalized outreach emails to recruiters. "
            "What would feel most helpful to tackle right now?"
        )
