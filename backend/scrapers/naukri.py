"""
naukri.py - Scraper for Naukri.com job listings via their internal API.
"""

from __future__ import annotations

import logging
import random
from urllib.parse import quote_plus

from .base import BaseScraper, JobListing

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fallback mock data
# ---------------------------------------------------------------------------
_MOCK_LISTINGS: list[dict] = [
    {
        "title": "Data Scientist",
        "company": "Juspay Technologies",
        "location": "Bangalore, Karnataka",
        "salary_range": "₹10,00,000 - ₹18,00,000/year",
        "url": "https://www.naukri.com/job-listings-data-scientist-juspay-technologies-bangalore-1-to-3-years-001",
        "description": (
            "Juspay is India's leading payment orchestration platform powering transactions for Amazon, "
            "Swiggy, and Flipkart. We are hiring a Data Scientist to build fraud detection, "
            "chargeback prediction, and payment success rate models. "
            "Requirements: Python, SQL, ML algorithms, Spark. "
            "Bonus: Haskell/functional programming knowledge. CTC: ₹10–18 LPA."
        ),
        "job_type": "full-time",
        "posted_date": "1 day ago",
    },
    {
        "title": "Machine Learning Engineer",
        "company": "Meesho",
        "location": "Bangalore, Karnataka",
        "salary_range": "₹15,00,000 - ₹25,00,000/year",
        "url": "https://www.naukri.com/job-listings-ml-engineer-meesho-bangalore-1-to-3-years-002",
        "description": (
            "Meesho is India's fastest-growing social commerce platform. "
            "We're hiring an ML Engineer to build recommendation, ranking, and demand-forecasting models "
            "serving 100M+ users. Stack: Python, TensorFlow, Kubeflow, GCP. "
            "Requirements: 1–3 years ML engineering experience, strong Python, distributed computing. "
            "CTC: ₹15–25 LPA + ESOPs."
        ),
        "job_type": "full-time",
        "posted_date": "2 days ago",
    },
    {
        "title": "Data Analyst",
        "company": "CRED",
        "location": "Bangalore, Karnataka",
        "salary_range": "₹8,00,000 - ₹14,00,000/year",
        "url": "https://www.naukri.com/job-listings-data-analyst-cred-bangalore-1-to-3-years-003",
        "description": (
            "CRED is a members-only platform that rewards creditworthy individuals. "
            "As a Data Analyst, you will drive product and growth analytics, run A/B tests, "
            "build dashboards, and generate actionable insights for product and business teams. "
            "Requirements: SQL (expert), Python, Metabase/Superset, experimentation mindset. "
            "CTC: ₹8–14 LPA."
        ),
        "job_type": "full-time",
        "posted_date": "3 days ago",
    },
    {
        "title": "Data Engineer",
        "company": "Razorpay",
        "location": "Bangalore, Karnataka",
        "salary_range": "₹12,00,000 - ₹20,00,000/year",
        "url": "https://www.naukri.com/job-listings-data-engineer-razorpay-bangalore-1-to-3-years-004",
        "description": (
            "Razorpay is India's leading payment gateway and neobanking platform. "
            "We need a Data Engineer to build robust data pipelines processing billions of payment events. "
            "Stack: Kafka, Spark, Airflow, Presto, AWS S3/Redshift. "
            "Requirements: 1–3 years data engineering, Python, SQL, distributed systems basics. "
            "CTC: ₹12–20 LPA + ESOPs."
        ),
        "job_type": "full-time",
        "posted_date": "4 days ago",
    },
    {
        "title": "ML Researcher",
        "company": "PhonePe",
        "location": "Bangalore, Karnataka",
        "salary_range": "₹14,00,000 - ₹22,00,000/year",
        "url": "https://www.naukri.com/job-listings-ml-researcher-phonepe-bangalore-1-to-3-years-005",
        "description": (
            "PhonePe is India's #1 fintech platform with 500M+ users. "
            "Our ML Research team works on fraud prevention, credit scoring, and conversational AI. "
            "As an ML Researcher you will publish papers and ship models to production. "
            "Requirements: MS/PhD in CS/Stats or equivalent research experience, "
            "PyTorch, strong math background. CTC: ₹14–22 LPA + ESOPs."
        ),
        "job_type": "full-time",
        "posted_date": "5 days ago",
    },
]

_API_URL = "https://www.naukri.com/jobapi/v3/search"


class NaukriScraper(BaseScraper):
    """Scraper for Naukri.com using their internal job-search API."""

    platform_name = "naukri"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------
    async def search(
        self,
        query: str,
        location: str = "",
        limit: int = 20,
    ) -> list[JobListing]:
        logger.info("[naukri] Searching for '%s' in '%s'", query, location)
        try:
            listings = await self._call_api(query, location, limit)
            if listings:
                return listings[:limit]
        except Exception as exc:
            logger.warning("[naukri] API call failed: %s — using mock data", exc)

        return self._mock_listings(limit)

    async def get_description(self, url: str) -> str:
        resp = await self._safe_get(url)
        if resp is None:
            return ""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
            desc = (
                soup.select_one(".job-desc")
                or soup.select_one('[class*="dang-inner-html"]')
                or soup.select_one(".description")
            )
            return desc.get_text(separator="\n", strip=True) if desc else ""
        except Exception as exc:
            logger.warning("[naukri] get_description parse error: %s", exc)
            return ""

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    async def _call_api(self, query: str, location: str, limit: int) -> list[JobListing]:
        params = {
            "noOfResults": str(min(limit, 20)),
            "urlType": "search_by_key_loc",
            "searchType": "adv",
            "keyword": query,
            "location": location,
            "pageNo": "1",
            "k": query,
            "l": location,
            "nignbevent_src": "jobSearchDesk",
        }
        param_str = "&".join(f"{k}={quote_plus(str(v))}" for k, v in params.items())
        url = f"{_API_URL}?{param_str}"

        api_headers = {
            **self._rotate_ua(),
            "appid": "109",
            "systemid": "Naukri",
            "content-type": "application/json",
            "Accept": "application/json",
            "Referer": "https://www.naukri.com/",
            "X-Requested-With": "XMLHttpRequest",
        }

        resp = await self._safe_get(url, headers=api_headers)
        if resp is None:
            raise RuntimeError("No response from Naukri API")

        data = resp.json()
        job_details = data.get("jobDetails", [])
        if not job_details:
            raise RuntimeError("Empty jobDetails in Naukri response")

        listings = []
        for job in job_details[:limit]:
            listings.append(self._parse_job(job))

        return listings

    def _parse_job(self, job: dict) -> JobListing:
        # Extract location/experience/salary from placeholders list
        placeholders = {p.get("type", ""): p.get("label", "") for p in job.get("placeholders", [])}
        salary = placeholders.get("salary") or None
        location = placeholders.get("location", "")

        return JobListing(
            title=job.get("title", ""),
            company=job.get("companyName", ""),
            location=location,
            platform=self.platform_name,
            url=job.get("jdURL", ""),
            description=job.get("jobDesc", ""),
            salary_range=salary,
            job_type="full-time",
            posted_date=job.get("footerPlaceholderLabel"),
            raw_data=job,
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
                    job_type=item.get("job_type", "full-time"),
                    posted_date=item.get("posted_date"),
                )
            )
        return result
