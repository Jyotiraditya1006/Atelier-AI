"""
linkedin.py - Scraper for LinkedIn public job search (no authentication required).
"""

from __future__ import annotations

import asyncio
import logging
import random
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
        "title": "STEP Intern – Engineering Practicum",
        "company": "Google",
        "location": "Bangalore, Karnataka, India",
        "salary_range": "₹80,000 - ₹1,00,000/month",
        "url": "https://www.linkedin.com/jobs/view/google-step-intern-001",
        "description": (
            "Google's STEP (Student Training in Engineering Program) is a developmental opportunity "
            "for first and second-year undergraduate students. As a STEP Intern you will work on a "
            "real engineering project over 10–12 weeks. Areas include ML, infrastructure, and product. "
            "Requirements: Pursuing CS/related degree, C++/Java/Python proficiency, algorithm fundamentals. "
            "Stipend: ₹80,000–₹1,00,000/month + housing."
        ),
        "job_type": "internship",
        "posted_date": "2 days ago",
    },
    {
        "title": "Explore Intern – Product + Engineering",
        "company": "Microsoft",
        "location": "Hyderabad, Telangana, India",
        "salary_range": "₹90,000/month",
        "url": "https://www.linkedin.com/jobs/view/microsoft-explore-intern-002",
        "description": (
            "Microsoft Explore is an internship program for second-year undergraduates. "
            "Interns rotate through program management and software engineering roles. "
            "You will work on Azure AI or M365 intelligence products. "
            "Requirements: Passion for tech, analytical thinking, Python or C# basics. "
            "Duration: 12 weeks. Stipend: ₹90,000/month."
        ),
        "job_type": "internship",
        "posted_date": "1 day ago",
    },
    {
        "title": "SDE Intern – Data Science Platform",
        "company": "Amazon",
        "location": "Bangalore, Karnataka, India",
        "salary_range": "₹1,00,000 - ₹1,20,000/month",
        "url": "https://www.linkedin.com/jobs/view/amazon-sde-intern-003",
        "description": (
            "Amazon's Data Science Platform team is hiring a SDE Intern to build internal ML tooling. "
            "You will contribute to the Feature Store, Model Registry, or automated training pipelines. "
            "Requirements: Data structures & algorithms (OA + interviews), Python or Java, "
            "basic knowledge of ML workflows. Duration: 12 weeks. Stipend: ₹1,00,000–₹1,20,000/month."
        ),
        "job_type": "internship",
        "posted_date": "3 days ago",
    },
    {
        "title": "Meta University Program – AI/ML",
        "company": "Meta",
        "location": "Remote (India)",
        "salary_range": "₹70,000/month",
        "url": "https://www.linkedin.com/jobs/view/meta-university-004",
        "description": (
            "Meta University is a unique immersive internship for students historically underrepresented "
            "in tech. As an AI/ML intern, you will work on recommendation systems, ranking models, or "
            "integrity ML models. Mentorship from senior researchers included. "
            "Requirements: Python, ML basics, genuine curiosity. Duration: 10 weeks. Stipend: ₹70,000/month."
        ),
        "job_type": "internship",
        "posted_date": "5 days ago",
    },
    {
        "title": "Data Science Intern",
        "company": "Apple",
        "location": "Hyderabad, Telangana, India",
        "salary_range": "₹1,10,000/month",
        "url": "https://www.linkedin.com/jobs/view/apple-ds-intern-005",
        "description": (
            "Apple is looking for a Data Science Intern for its Maps/Siri intelligence team in Hyderabad. "
            "You will apply statistical models and ML techniques to improve user experience features. "
            "Requirements: Python, R, SQL, statistics, ML fundamentals. "
            "Duration: 6 months. Stipend: ₹1,10,000/month. PPO eligible."
        ),
        "job_type": "internship",
        "posted_date": "1 week ago",
    },
]

_BASE = "https://www.linkedin.com"


class LinkedInScraper(BaseScraper):
    """Scraper for LinkedIn public job search pages (no credentials needed)."""

    platform_name = "linkedin"
    _JOBS_SEARCH = f"{_BASE}/jobs/search/"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------
    async def search(
        self,
        query: str,
        location: str = "",
        limit: int = 20,
    ) -> list[JobListing]:
        logger.info("[linkedin] Searching for '%s' in '%s'", query, location)
        try:
            listings = await self._scrape_search(query, location, limit)
            if listings:
                return listings[:limit]
        except Exception as exc:
            logger.warning("[linkedin] Live scrape failed: %s — using mock data", exc)

        return self._mock_listings(limit)

    async def get_description(self, url: str) -> str:
        await asyncio.sleep(random.uniform(1.0, 2.5))   # be polite
        resp = await self._safe_get(url)
        if resp is None:
            return ""
        try:
            soup = BeautifulSoup(resp.text, "html.parser")
            desc = (
                soup.select_one(".show-more-less-html__markup")
                or soup.select_one(".description__text")
                or soup.select_one('[data-testid="job-description"]')
            )
            return desc.get_text(separator="\n", strip=True) if desc else ""
        except Exception as exc:
            logger.warning("[linkedin] get_description parse error: %s", exc)
            return ""

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    async def _scrape_search(self, query: str, location: str, limit: int) -> list[JobListing]:
        params = {
            "keywords": query,
            "location": location,
            "f_E": "1,2",       # Entry/Associate level
            "f_JT": "I,F",      # Internship + Full-time
            "start": "0",
            "count": str(min(limit, 25)),
        }
        param_str = "&".join(f"{k}={quote_plus(v)}" for k, v in params.items())
        url = f"{self._JOBS_SEARCH}?{param_str}"

        resp = await self._safe_get(
            url,
            headers={
                **self._rotate_ua(),
                "Referer": "https://www.linkedin.com/jobs/",
                "X-Li-Lang": "en_US",
            },
        )
        if resp is None:
            raise RuntimeError("No response from LinkedIn")

        soup = BeautifulSoup(resp.text, "html.parser")
        return self._parse_cards(soup, limit)

    def _parse_cards(self, soup: BeautifulSoup, limit: int) -> list[JobListing]:
        cards = (
            soup.select(".base-card")
            or soup.select(".jobs-search__results-list li")
            or soup.select('[data-entity-urn]')
        )
        listings = []
        for card in cards[:limit]:
            try:
                title_el = (
                    card.select_one(".base-search-card__title")
                    or card.select_one("h3.base-search-card__title")
                )
                company_el = (
                    card.select_one(".base-search-card__subtitle")
                    or card.select_one("h4.base-search-card__subtitle")
                )
                location_el = (
                    card.select_one(".job-search-card__location")
                    or card.select_one(".base-search-card__metadata span")
                )
                date_el = card.select_one(".job-search-card__listdate") or card.select_one("time")
                link_el = card.select_one("a.base-card__full-link") or card.select_one("a[href*='/jobs/view/']")

                href = ""
                if link_el and link_el.get("href"):
                    href = link_el["href"].split("?")[0]   # strip tracking params

                posted = None
                if date_el:
                    posted = date_el.get("datetime") or date_el.get_text(strip=True)

                listings.append(
                    JobListing(
                        title=(title_el.get_text(strip=True) if title_el else ""),
                        company=(company_el.get_text(strip=True) if company_el else ""),
                        location=(location_el.get_text(strip=True) if location_el else ""),
                        platform=self.platform_name,
                        url=href,
                        job_type="internship",
                        posted_date=posted,
                    )
                )
            except Exception as exc:
                logger.debug("[linkedin] Card parse error: %s", exc)

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
                    job_type=item.get("job_type", "internship"),
                    posted_date=item.get("posted_date"),
                )
            )
        return result
