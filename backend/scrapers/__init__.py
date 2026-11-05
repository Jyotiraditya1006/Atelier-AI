"""
scrapers package – multi-platform job scraper suite.
"""

from .base import BaseScraper, JobListing
from .internshala import InternshalaScaper
from .indeed import IndeedScraper
from .linkedin import LinkedInScraper
from .naukri import NaukriScraper
from .wellfound import WellfoundScraper
from .scraper_manager import ScraperManager

__all__ = [
    "BaseScraper",
    "JobListing",
    "InternshalaScaper",
    "IndeedScraper",
    "LinkedInScraper",
    "NaukriScraper",
    "WellfoundScraper",
    "ScraperManager",
]
