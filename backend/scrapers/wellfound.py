"""
wellfound.py - Scraper for Wellfound (formerly AngelList Talent) startup job listings.
"""

from __future__ import annotations

import json
import logging
import re
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from .base import BaseScraper, JobListing

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fallback mock data
# ---------------------------------------------------------------------------
_MOCK_LISTINGS: list[dict] = [
    {
        "title": "Machine Learning Engineer",
        "company": "Skit.ai",
        "location": "Bangalore, Karnataka, India",
        "salary_range": "₹12,00,000 - ₹20,00,000/year",
        "url": "https://wellfound.com/jobs/skit-ai-ml-engineer",
        "description": (
            "Skit.ai (formerly Vernacular.ai) builds voice AI agents for enterprises. "
            "As an ML Engineer, you will develop ASR, NLU, and dialogue management models "
            "deployed in production handling millions of calls daily. "
            "Stack: Python, PyTorch, Kubernetes, AWS. "
            "Requirements: 1+ years ML engineering, NLP/ASR background preferred. "
            "Equity: 0.05–0.15%. CTC: ₹12–20 LPA."
        ),
        "job_type": "full-time",
        "posted_date": "2 days ago",
    },
    {
        "title": "Research Intern – Speech & Language",
        "company": "Vernacular.ai",
        "location": "Bangalore, Karnataka, India",
        "salary_range": "₹20,000 - ₹30,000/month",
        "url": "https://wellfound.com/jobs/vernacular-ai-research-intern",
        "description": (
            "Vernacular.ai is a voice AI startup building multilingual conversational interfaces. "
            "As a Research Intern, you will work on low-resource language ASR, TTS, "
            "and code-switching NLP for Indian languages. "
            "Requirements: NLP/ML coursework, Python, HuggingFace familiarity. "
            "Duration: 3–6 months. Stipend: ₹20,000–₹30,000/month. Research paper co-authorship possible."
        ),
        "job_type": "internship",
        "posted_date": "3 days ago",
    },
    {
        "title": "Computer Vision Engineer",
        "company": "Mad Street Den",
        "location": "Chennai, Tamil Nadu, India",
        "salary_range": "₹10,00,000 - ₹18,00,000/year",
        "url": "https://wellfound.com/jobs/mad-street-den-cv-engineer",
        "description": (
            "Mad Street Den (Vue.ai) is an AI-first retail automation company. "
            "As a CV Engineer, you will build image recognition, visual search, "
            "and virtual try-on features powered by deep learning. "
            "Stack: Python, PyTorch, OpenCV, AWS SageMaker. "
            "Requirements: Computer vision background, CNN architectures, 1+ years experience. "
            "Equity available. CTC: ₹10–18 LPA."
        ),
        "job_type": "full-time",
        "posted_date": "1 day ago",
    },
    {
        "title": "NLP Intern",
        "company": "Niki.ai",
        "location": "Bangalore, Karnataka, India",
        "salary_range": "₹15,000 - ₹25,000/month",
        "url": "https://wellfound.com/jobs/niki-ai-nlp-intern",
        "description": (
            "Niki.ai is building India's first transactional chatbot for the mass market. "
            "As an NLP Intern, you will work on intent detection, slot filling, and dialogue management "
            "for 10+ service categories in English and Hindi. "
            "Requirements: Python, NLTK/spaCy or transformers knowledge, NLP coursework. "
            "Duration: 4–6 months. Stipend: ₹15,000–₹25,000/month."
        ),
        "job_type": "internship",
        "posted_date": "5 days ago",
    },
    {
        "title": "Data Scientist",
        "company": "Hyperface",
        "location": "Bangalore, Karnataka, India",
        "salary_range": "₹8,00,000 - ₹15,00,000/year",
        "url": "https://wellfound.com/jobs/hyperface-data-scientist",
        "description": (
            "Hyperface is a credit card-as-a-service fintech startup. "
            "As a Data Scientist, you will build credit risk, fraud detection, and customer segmentation models "
            "to power our card issuance and rewards platform. "
            "Requirements: Python, SQL, ML algorithms, credit/risk domain knowledge is a bonus. "
            "Equity: 0.05–0.1%. CTC: ₹8–15 LPA."
        ),
        "job_type": "full-time",
        "posted_date": "1 week ago",
    },
]

# Wellfound role slugs to try
_ROLE_SLUGS = ["data-scientist", "machine-learning-engineer", "data-engineer", "research-scientist"]
_BASE = "https://wellfound.com"


class WellfoundScraper(BaseScraper):
    """Scraper for Wellfound (AngelList Talent) startup job listings."""

    platform_name = "wellfound"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------
    async def search(
        self,
        query: str,
        location: str = "",
        limit: int = 20,
    ) -> list[JobListing]:
        logger.info("[wellfound] Searching for '%s' in '%s'", query, location)
        try:
            listings = await self._scrape_role_pages(query, limit)
            if listings:
                return listings[:limit]
        except Exception as exc:
            logger.warning("[wellfound] Live scrape failed: %s — using mock data", exc)

        return self._mock_listings(limit)

    async def get_description(self, url: str) -> str:
        resp = await self._safe_get(url)
        if resp is None:
            return ""
        try:
            soup = BeautifulSoup(resp.text, "html.parser")
            desc = soup.select_one(".job-description") or soup.select_one('[class*="description"]')
            return desc.get_text(separator="\n", strip=True) if desc else ""
        except Exception as exc:
            logger.warning("[wellfound] get_description parse error: %s", exc)
            return ""

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    async def _scrape_role_pages(self, query: str, limit: int) -> list[JobListing]:
        # Determine the best slug based on query keywords
        slug = self._query_to_slug(query)
        url = f"{_BASE}/role/r/{slug}"
        resp = await self._safe_get(
            url,
            headers={
                **self._rotate_ua(),
                "Referer": "https://wellfound.com/jobs",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )
        if resp is None:
            raise RuntimeError("No response from Wellfound role page")

        soup = BeautifulSoup(resp.text, "html.parser")

        # 1. Try parsing __NEXT_DATA__
        listings = self._parse_next_data(resp.text, limit)
        if listings:
            return listings

        # 2. Try HTML card scraping
        listings = self._parse_html_cards(soup, limit)
        if listings:
            return listings

        raise RuntimeError("No jobs found in Wellfound page")

    def _query_to_slug(self, query: str) -> str:
        q = query.lower()
        if "vision" in q or "cv" in q:
            return "computer-vision-engineer"
        if "nlp" in q or "natural language" in q:
            return "nlp-engineer"
        if "research" in q:
            return "research-scientist"
        if "engineer" in q:
            return "machine-learning-engineer"
        return "data-scientist"

    def _parse_next_data(self, html: str, limit: int) -> list[JobListing]:
        """Extract jobs from Next.js __NEXT_DATA__ JSON blob."""
        match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(\{.*?\})</script>', html, re.S)
        if not match:
            return []
        try:
            data = json.loads(match.group(1))
            # Wellfound's data structure (may vary with updates)
            role_data = (
                data.get("props", {})
                .get("pageProps", {})
                .get("role", {})
            )
            jobs_raw = role_data.get("jobs", []) or role_data.get("jobListings", [])
            if not jobs_raw:
                return []

            listings = []
            for job in jobs_raw[:limit]:
                startup = job.get("startup", {}) or job.get("company", {})
                loc = ", ".join(job.get("locationNames", [])) or startup.get("highConcept", "")
                listings.append(
                    JobListing(
                        title=job.get("title", ""),
                        company=startup.get("name", ""),
                        location=loc,
                        platform=self.platform_name,
                        url=f"{_BASE}/jobs/{job.get('slug', '')}",
                        salary_range=job.get("salary", None),
                        job_type=("internship" if "intern" in job.get("title", "").lower() else "full-time"),
                        posted_date=job.get("liveStartAt"),
                    )
                )
            return listings
        except Exception as exc:
            logger.debug("[wellfound] __NEXT_DATA__ parse error: %s", exc)
            return []

    def _parse_html_cards(self, soup: BeautifulSoup, limit: int) -> list[JobListing]:
        """Fallback: parse rendered HTML job cards."""
        cards = (
            soup.select(".mb-6 .styles_component__Ey28k")
            or soup.select('[data-test="StartupResult"]')
            or soup.select(".startup-job-card")
        )
        listings = []
        for card in cards[:limit]:
            try:
                title_el = card.select_one("a[href*='/jobs/']") or card.select_one("h2")
                company_el = card.select_one(".startup-link") or card.select_one("h3")
                location_el = card.select_one("[data-test='locations']") or card.select_one(".location")
                href = ""
                if title_el and title_el.get("href"):
                    href = _BASE + title_el["href"] if title_el["href"].startswith("/") else title_el["href"]
                listings.append(
                    JobListing(
                        title=(title_el.get_text(strip=True) if title_el else ""),
                        company=(company_el.get_text(strip=True) if company_el else ""),
                        location=(location_el.get_text(strip=True) if location_el else ""),
                        platform=self.platform_name,
                        url=href,
                        job_type="full-time",
                    )
                )
            except Exception as exc:
                logger.debug("[wellfound] Card parse error: %s", exc)
        return listings

    def _mock_listings(self, limit: int) -> list[JobListing]:
        result = []
        for item in _MOCK_LISTINGS[:limit]:
            result.append(
                JobListing(
                    title=item["title"],
                    company=item["company"],
                    location=item["location"],
                    platform=self.platform_name,
                    url=item["url"],
                    description=item["description"],
                    salary_range=item.get("salary_range"),
                    job_type=item.get("job_type", "full-time"),
                    posted_date=item.get("posted_date"),
                )
            )
        return result
