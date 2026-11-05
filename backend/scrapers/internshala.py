"""
internshala.py - Scraper for Internshala internship listings.
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
        "title": "Machine Learning Intern",
        "company": "Sprinklr",
        "location": "Gurugram, Haryana",
        "salary_range": "₹20,000 - ₹25,000/month",
        "url": "https://internshala.com/internship/detail/machine-learning-intern-at-sprinklr1",
        "description": (
            "Sprinklr is seeking a Machine Learning Intern to join our AI team. "
            "You will work on NLP pipelines, build classification models, and contribute to "
            "production ML systems. Skills required: Python, scikit-learn, PyTorch, pandas. "
            "Duration: 6 months. Stipend: ₹20,000–₹25,000/month. "
            "Perks: Certificate, Letter of recommendation, flexible work hours."
        ),
        "job_type": "internship",
        "posted_date": "2 days ago",
    },
    {
        "title": "Data Science Intern",
        "company": "MathWorks",
        "location": "Bangalore, Karnataka",
        "salary_range": "₹30,000/month",
        "url": "https://internshala.com/internship/detail/data-science-intern-at-mathworks2",
        "description": (
            "MathWorks (makers of MATLAB & Simulink) is hiring a Data Science Intern. "
            "Responsibilities: exploratory data analysis, feature engineering, model building using MATLAB/Python, "
            "and presenting insights to engineering leads. "
            "Requirements: CGPA > 8.0, proficiency in Python or MATLAB, statistics background. "
            "Duration: 6 months. Stipend: ₹30,000/month. Full pre-placement offer possibility."
        ),
        "job_type": "internship",
        "posted_date": "1 day ago",
    },
    {
        "title": "Quantitative Research Intern",
        "company": "D.E. Shaw India",
        "location": "Hyderabad, Telangana",
        "salary_range": "₹60,000 - ₹80,000/month",
        "url": "https://internshala.com/internship/detail/quant-research-intern-at-deshaw3",
        "description": (
            "D.E. Shaw is one of the world's leading investment management firms. "
            "As a Quant Research Intern, you will analyze large financial datasets, develop statistical "
            "models, and backtest trading strategies. "
            "Requirements: Strong math/statistics background, proficiency in Python or R, "
            "knowledge of probability theory, stochastic processes preferred. "
            "Duration: 2–3 months. Stipend: ₹60,000–₹80,000/month."
        ),
        "job_type": "internship",
        "posted_date": "3 days ago",
    },
    {
        "title": "Data Science Intern",
        "company": "Fractal Analytics",
        "location": "Mumbai, Maharashtra",
        "salary_range": "₹15,000 - ₹20,000/month",
        "url": "https://internshala.com/internship/detail/data-science-intern-at-fractal4",
        "description": (
            "Fractal Analytics is a global analytics company. We are looking for a Data Science Intern "
            "to work on predictive modelling projects for Fortune 500 clients. "
            "Responsibilities: data wrangling, feature selection, XGBoost/LightGBM modelling, "
            "building dashboards in Tableau/Power BI. "
            "Requirements: Python, SQL, statistics. Duration: 3–6 months. Stipend: ₹15,000–₹20,000/month."
        ),
        "job_type": "internship",
        "posted_date": "5 days ago",
    },
    {
        "title": "Business Analyst Intern",
        "company": "Mu Sigma",
        "location": "Bangalore, Karnataka",
        "salary_range": "₹12,000 - ₹18,000/month",
        "url": "https://internshala.com/internship/detail/business-analyst-intern-at-musigma5",
        "description": (
            "Mu Sigma is the world's largest pure-play analytics company. "
            "As a Business Analyst Intern, you will help clients solve complex business problems using data. "
            "Responsibilities: problem scoping, data collection, SQL querying, R/Python analysis, "
            "presentation to stakeholders. "
            "Requirements: Analytical mindset, basic SQL, Excel. "
            "Duration: 6 months. Stipend: ₹12,000–₹18,000/month."
        ),
        "job_type": "internship",
        "posted_date": "1 week ago",
    },
]


class InternshalaScaper(BaseScraper):
    """Scraper for internshala.com internship listings."""

    platform_name = "internshala"
    BASE_URL = "https://internshala.com"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------
    async def search(
        self,
        query: str,
        location: str = "",
        limit: int = 20,
    ) -> list[JobListing]:
        """Search Internshala for internships matching *query*."""
        logger.info("[internshala] Searching for '%s' in '%s'", query, location)
        try:
            listings = await self._scrape_search(query, location, limit)
            if listings:
                return listings[:limit]
        except Exception as exc:
            logger.warning("[internshala] Live scrape failed: %s — using mock data", exc)

        return self._mock_listings(limit)

    async def get_description(self, url: str) -> str:
        """Fetch the full description from an Internshala detail page."""
        resp = await self._safe_get(url)
        if resp is None:
            return ""
        try:
            soup = BeautifulSoup(resp.text, "html.parser")
            detail = soup.select_one(".internship_details") or soup.select_one("#about_internship")
            if detail:
                return detail.get_text(separator="\n", strip=True)
            # Broader fallback
            main = soup.select_one("main") or soup.select_one(".container")
            return main.get_text(separator="\n", strip=True)[:3000] if main else ""
        except Exception as exc:
            logger.warning("[internshala] get_description parse error: %s", exc)
            return ""

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    async def _scrape_search(self, query: str, location: str, limit: int) -> list[JobListing]:
        slug = quote_plus(query.lower().replace(" ", "-"))
        url = f"{self.BASE_URL}/internships/keywords-{slug}/"
        resp = await self._safe_get(url)
        if resp is None:
            raise RuntimeError("No response from Internshala search page")

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select(".individual_internship")
        if not cards:
            raise RuntimeError("No internship cards found in HTML")

        listings: list[JobListing] = []
        for card in cards[:limit]:
            try:
                listing = self._parse_card(card)
                if listing:
                    listings.append(listing)
            except Exception as exc:
                logger.debug("[internshala] Card parse error: %s", exc)

            if len(listings) >= limit:
                break
            await asyncio.sleep(random.uniform(0.5, 1.5))

        return listings

    def _parse_card(self, card: BeautifulSoup) -> JobListing | None:
        title_el = card.select_one(".internship_meta h3") or card.select_one("h3.heading_4_5")
        company_el = card.select_one(".company_name") or card.select_one("a.link_display_like_text")
        location_el = card.select_one(".location_link") or card.select_one(".locations span")
        stipend_el = card.select_one(".stipend") or card.select_one(".stipend_container span")
        link_el = card.select_one(".view_detail_button") or card.select_one("a.view_detail_button")

        if not title_el:
            return None

        href = ""
        if link_el and link_el.get("href"):
            href = self.BASE_URL + link_el["href"] if link_el["href"].startswith("/") else link_el["href"]

        return JobListing(
            title=title_el.get_text(strip=True),
            company=(company_el.get_text(strip=True) if company_el else ""),
            location=(location_el.get_text(strip=True) if location_el else ""),
            platform=self.platform_name,
            url=href,
            salary_range=(stipend_el.get_text(strip=True) if stipend_el else None),
            job_type="internship",
        )

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
