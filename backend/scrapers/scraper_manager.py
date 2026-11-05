"""
scraper_manager.py - Coordinates all platform scrapers concurrently.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import httpx

from .base import BaseScraper, JobListing
from .internshala import InternshalaScaper
from .indeed import IndeedScraper
from .linkedin import LinkedInScraper
from .naukri import NaukriScraper
from .wellfound import WellfoundScraper

logger = logging.getLogger(__name__)

PLATFORM_MAP: dict[str, type[BaseScraper]] = {
    "internshala": InternshalaScaper,
    "indeed": IndeedScraper,
    "linkedin": LinkedInScraper,
    "naukri": NaukriScraper,
    "wellfound": WellfoundScraper,
}


class ScraperManager:
    """
    Orchestrates all job-platform scrapers.

    Usage::

        async with ScraperManager() as manager:
            jobs = await manager.search_all("data scientist", location="Bangalore")
    """

    def __init__(self):
        # Shared HTTP session for all scrapers (reduces connection overhead)
        self._session: Optional[httpx.AsyncClient] = None
        self.scrapers: dict[str, BaseScraper] = {}

    # ------------------------------------------------------------------
    # Context-manager support
    # ------------------------------------------------------------------
    async def __aenter__(self) -> "ScraperManager":
        self._session = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
            verify=False,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
        for name, cls in PLATFORM_MAP.items():
            self.scrapers[name] = cls(session=self._session)
        return self

    async def __aexit__(self, *_) -> None:
        if self._session:
            await self._session.aclose()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def search_all(
        self,
        query: str,
        location: str = "",
        platforms: Optional[list[str]] = None,
        limit_per_platform: int = 10,
    ) -> list[JobListing]:
        """
        Run all (or specified) scrapers concurrently and return merged, deduplicated results.

        Args:
            query: Job search query string.
            location: Optional location filter.
            platforms: List of platform keys to search. Defaults to all.
            limit_per_platform: Max results per platform.

        Returns:
            Deduplicated list of JobListing objects sorted by platform.
        """
        active_platforms = platforms or list(PLATFORM_MAP.keys())
        logger.info(
            "[manager] Searching '%s' across platforms: %s",
            query,
            active_platforms,
        )

        # Build tasks
        tasks = {
            platform: self._run_scraper(platform, query, location, limit_per_platform)
            for platform in active_platforms
            if platform in self.scrapers
        }

        results: list[JobListing] = []
        gathered = await asyncio.gather(*tasks.values(), return_exceptions=True)

        for platform, result in zip(tasks.keys(), gathered):
            if isinstance(result, Exception):
                logger.error("[manager] Scraper '%s' raised exception: %s", platform, result)
            elif isinstance(result, list):
                logger.info("[manager] '%s' returned %d listings", platform, len(result))
                results.extend(result)

        # Deduplicate by (company lower + title lower)
        seen: set[str] = set()
        unique: list[JobListing] = []
        for job in results:
            key = f"{job.company.lower().strip()}|{job.title.lower().strip()}"
            if key not in seen:
                seen.add(key)
                unique.append(job)

        logger.info("[manager] Total unique listings after dedup: %d", len(unique))
        return unique

    async def search_platform(
        self,
        platform: str,
        query: str,
        location: str = "",
        limit: int = 10,
    ) -> list[JobListing]:
        """
        Search a single platform.

        Args:
            platform: Platform key (e.g. 'naukri', 'linkedin').
            query: Search query.
            location: Optional location.
            limit: Max number of results.

        Returns:
            List of JobListing objects from the specified platform.
        """
        if platform not in self.scrapers:
            logger.warning("[manager] Unknown platform: '%s'", platform)
            return []
        return await self._run_scraper(platform, query, location, limit)

    def available_platforms(self) -> list[str]:
        """Return list of available platform names."""
        return list(PLATFORM_MAP.keys())

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    async def _run_scraper(
        self,
        platform: str,
        query: str,
        location: str,
        limit: int,
    ) -> list[JobListing]:
        scraper = self.scrapers[platform]
        try:
            return await scraper.search(query, location, limit)
        except Exception as exc:
            logger.error("[manager] Scraper '%s' error: %s", platform, exc)
            return []
