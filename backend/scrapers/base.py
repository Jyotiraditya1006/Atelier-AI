"""
base.py - Base classes for all job scrapers.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class JobListing:
    """Canonical representation of a single job/internship listing."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    company: str = ""
    location: str = ""
    platform: str = ""
    url: str = ""
    description: str = ""
    salary_range: Optional[str] = None
    job_type: str = "full-time"          # full-time | internship | contract
    posted_date: Optional[str] = None
    raw_data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "platform": self.platform,
            "url": self.url,
            "description": self.description,
            "salary_range": self.salary_range,
            "job_type": self.job_type,
            "posted_date": self.posted_date,
        }


# ---------------------------------------------------------------------------
# Rotating user-agent pool
# ---------------------------------------------------------------------------
USER_AGENTS: list[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
]


class BaseScraper:
    """Abstract base class every platform scraper must implement."""

    platform_name: str = "base"

    def __init__(self, session: Optional[httpx.AsyncClient] = None):
        self.session = session or httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
            verify=False,          # avoids SSL errors on corporate networks
        )
        self._ua_index: int = 0
        self.headers = self._base_headers()

    # ------------------------------------------------------------------
    # Header helpers
    # ------------------------------------------------------------------
    def _base_headers(self) -> dict:
        return {
            "User-Agent": USER_AGENTS[0],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1",
        }

    def _rotate_ua(self) -> dict:
        """Return headers with the next user-agent in the pool."""
        self._ua_index = (self._ua_index + 1) % len(USER_AGENTS)
        return {**self.headers, "User-Agent": USER_AGENTS[self._ua_index]}

    # ------------------------------------------------------------------
    # Interface methods – must be overridden
    # ------------------------------------------------------------------
    async def search(
        self,
        query: str,
        location: str = "",
        limit: int = 20,
    ) -> list[JobListing]:
        """Search for jobs and return a list of JobListing objects."""
        raise NotImplementedError(f"{self.__class__.__name__}.search() not implemented")

    async def get_description(self, url: str) -> str:
        """Fetch and return the full job description for a given URL."""
        raise NotImplementedError(f"{self.__class__.__name__}.get_description() not implemented")

    # ------------------------------------------------------------------
    # Shared utility
    # ------------------------------------------------------------------
    async def _safe_get(self, url: str, **kwargs) -> Optional[httpx.Response]:
        """GET with error handling; returns None on failure."""
        try:
            req_headers = self._rotate_ua()
            if "headers" in kwargs:
                req_headers.update(kwargs.pop("headers"))
            resp = await self.session.get(url, headers=req_headers, **kwargs)
            resp.raise_for_status()
            return resp
        except httpx.HTTPStatusError as exc:
            logger.warning("[%s] HTTP %s for %s", self.platform_name, exc.response.status_code, url)
        except Exception as exc:
            logger.warning("[%s] Request failed for %s: %s", self.platform_name, url, exc)
        return None

    async def close(self):
        """Close the underlying HTTP session."""
        await self.session.aclose()
