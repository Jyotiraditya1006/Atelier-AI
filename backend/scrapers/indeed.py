"""
indeed.py - Scraper for Indeed India job listings.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import re
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup

from .base import BaseScraper, JobListing

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fallback mock data
# ---------------------------------------------------------------------------
_MOCK_LISTINGS: list[dict] = [
    {
        "title": "Data Engineer",
        "company": "Accenture",
        "location": "Bangalore, Karnataka",
        "salary_range": "₹6,00,000 - ₹10,00,000/year",
        "url": "https://in.indeed.com/viewjob?jk=accenture_de_001",
        "description": (
            "Accenture is hiring a Data Engineer to design, build and maintain scalable data pipelines. "
            "Responsibilities include ingesting data from diverse sources, building ETL workflows with Apache Spark, "
            "maintaining data warehouses on Azure Synapse / BigQuery, and ensuring data quality. "
            "Required: 0–2 years experience, Python, SQL, Spark, cloud platforms (Azure/GCP). "
            "Preferred: Databricks, dbt, Kafka. CTC: ₹6–10 LPA."
        ),
        "job_type": "full-time",
        "posted_date": "1 day ago",
    },
    {
        "title": "Machine Learning Developer",
        "company": "Cognizant",
        "location": "Hyderabad, Telangana",
        "salary_range": "₹5,50,000 - ₹9,00,000/year",
        "url": "https://in.indeed.com/viewjob?jk=cognizant_ml_002",
        "description": (
            "Cognizant Technology Solutions is looking for a Machine Learning Developer. "
            "You will implement ML models for client projects in healthcare and retail domains. "
            "Responsibilities: EDA, feature engineering, model training with scikit-learn/TensorFlow, "
            "MLOps with MLflow, REST API development with FastAPI. "
            "Requirements: Python, SQL, ML fundamentals. CTC: ₹5.5–9 LPA."
        ),
        "job_type": "full-time",
        "posted_date": "2 days ago",
    },
    {
        "title": "Data Scientist",
        "company": "Tata Consultancy Services",
        "location": "Mumbai, Maharashtra",
        "salary_range": "₹7,00,000 - ₹12,00,000/year",
        "url": "https://in.indeed.com/viewjob?jk=tcs_ds_003",
        "description": (
            "TCS Digital is seeking a Data Scientist to work on enterprise AI solutions. "
            "You will participate in end-to-end ML lifecycle: data collection, model development, "
            "deployment, and monitoring. Domains include banking, insurance, and telecom. "
            "Requirements: Python, R, machine learning algorithms, strong statistics. "
            "Bonus: NLP, computer vision. CTC: ₹7–12 LPA."
        ),
        "job_type": "full-time",
        "posted_date": "3 days ago",
    },
    {
        "title": "Data Analyst",
        "company": "HCL Technologies",
        "location": "Noida, Uttar Pradesh",
        "salary_range": "₹4,00,000 - ₹7,00,000/year",
        "url": "https://in.indeed.com/viewjob?jk=hcl_da_004",
        "description": (
            "HCL Technologies is hiring a Data Analyst for its Analytics CoE. "
            "Responsibilities: data extraction using SQL, building reports in Power BI/Tableau, "
            "stakeholder communication, and finding actionable business insights. "
            "Requirements: SQL, Excel, Power BI or Tableau, basic Python/R. "
            "Any domain experience is a plus. CTC: ₹4–7 LPA."
        ),
        "job_type": "full-time",
        "posted_date": "4 days ago",
    },
    {
        "title": "AI Engineer",
        "company": "Capgemini",
        "location": "Pune, Maharashtra",
        "salary_range": "₹8,00,000 - ₹14,00,000/year",
        "url": "https://in.indeed.com/viewjob?jk=capgemini_ai_005",
        "description": (
            "Capgemini Applied Innovation Exchange is looking for an AI Engineer. "
            "You will design conversational AI and intelligent automation solutions for global clients. "
            "Responsibilities: LLM fine-tuning with OpenAI/HuggingFace, RAG pipelines, "
            "agent frameworks (LangChain), REST API development, cloud deployment on AWS. "
            "Requirements: Python, LLM experience, AWS basics. CTC: ₹8–14 LPA."
        ),
        "job_type": "full-time",
        "posted_date": "5 days ago",
    },
]

_BASE = "https://in.indeed.com"


class IndeedScraper(BaseScraper):
    """Scraper for in.indeed.com job listings."""

    platform_name = "indeed"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------
    async def search(
        self,
        query: str,
        location: str = "",
        limit: int = 20,
    ) -> list[JobListing]:
        logger.info("[indeed] Searching for '%s' in '%s'", query, location)
        try:
            listings = await self._scrape_search(query, location, limit)
            if listings:
                return listings[:limit]
        except Exception as exc:
            logger.warning("[indeed] Live scrape failed: %s — using mock data", exc)

        return self._mock_listings(limit)

    async def get_description(self, url: str) -> str:
        resp = await self._safe_get(url)
        if resp is None:
            return ""
        try:
            soup = BeautifulSoup(resp.text, "html.parser")
            desc = (
                soup.select_one("#jobDescriptionText")
                or soup.select_one(".jobsearch-jobDescriptionText")
                or soup.select_one('[data-testid="jobsearch-JobComponent-description"]')
            )
            return desc.get_text(separator="\n", strip=True) if desc else ""
        except Exception as exc:
            logger.warning("[indeed] get_description parse error: %s", exc)
            return ""

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    async def _scrape_search(self, query: str, location: str, limit: int) -> list[JobListing]:
        url = f"{_BASE}/jobs?q={quote_plus(query)}&l={quote_plus(location)}&fromage=14"
        resp = await self._safe_get(
            url,
            headers={
                **self._rotate_ua(),
                "Referer": "https://in.indeed.com/",
            },
        )
        if resp is None:
            raise RuntimeError("No response from Indeed")

        soup = BeautifulSoup(resp.text, "html.parser")

        # Try to parse embedded __NEXT_DATA__ JSON first
        listings = self._parse_next_data(resp.text, limit)
        if listings:
            return listings

        # Fallback to HTML card parsing
        return self._parse_html_cards(soup, limit)

    def _parse_next_data(self, html: str, limit: int) -> list[JobListing]:
        """Extract jobs from Next.js embedded JSON blob."""
        match = re.search(r'window\.__NEXT_DATA__\s*=\s*(\{.*?\})(?=</script>)', html, re.S)
        if not match:
            return []
        try:
            data = json.loads(match.group(1))
            # Traverse to job results (structure may vary)
            jobs_raw = (
                data.get("props", {})
                .get("pageProps", {})
                .get("jobResults", {})
                .get("results", [])
            )
            if not jobs_raw:
                return []
            listings = []
            for job in jobs_raw[:limit]:
                listings.append(
                    JobListing(
                        title=job.get("title", ""),
                        company=job.get("company", ""),
                        location=job.get("formattedLocation", ""),
                        platform=self.platform_name,
                        url=urljoin(_BASE, job.get("link", "")),
                        salary_range=job.get("salarySnippet", {}).get("text"),
                        job_type="full-time",
                        posted_date=job.get("formattedRelativeTime"),
                    )
                )
            return listings
        except Exception as exc:
            logger.debug("[indeed] __NEXT_DATA__ parse error: %s", exc)
            return []

    def _parse_html_cards(self, soup: BeautifulSoup, limit: int) -> list[JobListing]:
        cards = soup.select(".job_seen_beacon") or soup.select('[data-testid="slider_item"]')
        listings = []
        for card in cards[:limit]:
            try:
                title_el = card.select_one(".jobTitle span") or card.select_one('[data-testid="jobTitle"]')
                company_el = card.select_one(".companyName") or card.select_one('[data-testid="company-name"]')
                location_el = card.select_one(".companyLocation") or card.select_one('[data-testid="text-location"]')
                salary_el = card.select_one(".salary-snippet-container") or card.select_one(".metadata.salary-container")
                link_el = card.select_one("a.jcs-JobTitle") or card.select_one("a[data-jk]")

                href = ""
                if link_el:
                    href_raw = link_el.get("href", "")
                    href = urljoin(_BASE, href_raw)

                listings.append(
                    JobListing(
                        title=(title_el.get_text(strip=True) if title_el else ""),
                        company=(company_el.get_text(strip=True) if company_el else ""),
                        location=(location_el.get_text(strip=True) if location_el else ""),
                        platform=self.platform_name,
                        url=href,
                        salary_range=(salary_el.get_text(strip=True) if salary_el else None),
                        job_type="full-time",
                    )
                )
            except Exception as exc:
                logger.debug("[indeed] Card parse error: %s", exc)

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
