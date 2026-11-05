"""
utils/resume_parser.py - PDF/DOCX text extraction and AI-powered profile extraction.
"""
import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from utils.gemini_client import GeminiClient

logger = logging.getLogger(__name__)


class ResumeParser:
    """
    Utility class for extracting text from resume files and deriving a
    structured user profile from that text using Gemini.
    """

    # ------------------------------------------------------------------
    # Text extraction helpers
    # ------------------------------------------------------------------

    async def parse_pdf(self, file_path: str) -> str:
        """
        Extract all text from a PDF file using pypdf.

        Parameters
        ----------
        file_path:
            Absolute or relative path to the PDF file.

        Returns
        -------
        str
            Concatenated page text, separated by newlines.
        """
        def _extract() -> str:
            try:
                from pypdf import PdfReader  # type: ignore
            except ImportError:
                raise ImportError(
                    "pypdf is required: install it with 'pip install pypdf'"
                )
            reader = PdfReader(file_path)
            pages = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
            return "\n".join(pages)

        try:
            text = await asyncio.to_thread(_extract)
            logger.info(f"Extracted {len(text)} characters from PDF: {file_path}")
            return text
        except Exception as exc:
            logger.error(f"PDF parsing failed for '{file_path}': {exc}")
            return ""

    async def parse_docx(self, file_path: str) -> str:
        """
        Extract all paragraph text from a DOCX file using python-docx.

        Parameters
        ----------
        file_path:
            Absolute or relative path to the DOCX file.

        Returns
        -------
        str
            Paragraph text joined by newlines.
        """
        def _extract() -> str:
            try:
                import docx  # type: ignore  # python-docx
            except ImportError:
                raise ImportError(
                    "python-docx is required: install it with 'pip install python-docx'"
                )
            doc = docx.Document(file_path)
            return "\n".join(para.text for para in doc.paragraphs if para.text.strip())

        try:
            text = await asyncio.to_thread(_extract)
            logger.info(f"Extracted {len(text)} characters from DOCX: {file_path}")
            return text
        except Exception as exc:
            logger.error(f"DOCX parsing failed for '{file_path}': {exc}")
            return ""

    # ------------------------------------------------------------------
    # AI-powered profile extraction
    # ------------------------------------------------------------------

    async def extract_profile_from_resume(
        self, resume_text: str, gemini_client: "GeminiClient"
    ) -> dict:
        """
        Use Gemini to derive a structured user profile from raw resume text.

        Parameters
        ----------
        resume_text:
            Plain-text content of the resume.
        gemini_client:
            An initialised :class:`GeminiClient` instance.

        Returns
        -------
        dict
            Keys: name, email, phone, skills, education, work_experience, projects,
            linkedin_url, location, experience_level, target_roles.
        """
        if not resume_text.strip():
            logger.warning("extract_profile_from_resume called with empty text.")
            return {}

        schema = {
            "name": "string",
            "email": "string",
            "phone": "string",
            "location": "string",
            "linkedin_url": "string",
            "experience_level": "string (fresher | junior | mid | senior)",
            "skills": ["list of skill strings"],
            "target_roles": ["list of likely role titles"],
            "education": [
                {
                    "degree": "string",
                    "institution": "string",
                    "year": "string",
                    "gpa": "string (optional)",
                }
            ],
            "work_experience": [
                {
                    "title": "string",
                    "company": "string",
                    "duration": "string",
                    "highlights": ["bullet strings"],
                }
            ],
            "projects": [
                {
                    "name": "string",
                    "description": "string",
                    "tech_stack": ["strings"],
                }
            ],
        }

        prompt = (
            "You are an expert resume parser. Extract all structured information from "
            "the following resume text. Infer 'experience_level' as one of: "
            "fresher, junior, mid, senior. Infer 'target_roles' from the resume's "
            "objective/summary or the nature of past experience. "
            "Be thorough and accurate.\n\n"
            f"RESUME TEXT:\n{resume_text[:8000]}"  # cap to avoid token overflow
        )

        result = await gemini_client.generate_json(prompt, schema)

        # Ensure list fields always exist
        for list_field in ("skills", "target_roles", "education", "work_experience", "projects"):
            if list_field not in result or not isinstance(result[list_field], list):
                result[list_field] = []

        logger.info(
            f"Profile extracted: name={result.get('name')}, "
            f"skills_count={len(result.get('skills', []))}"
        )
        return result
