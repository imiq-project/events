from datetime import datetime, timezone as _tz
from typing import Optional, List
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class Event:
    event_name: str
    source: List[str]
    source_url: List[str]
    scraped_at: datetime
    description: str
    keywords: List[str]
    start_iso: datetime
    end_iso: datetime
    venue_name: Optional[str]
    address: Optional[str]
    geo_lat: Optional[float]
    geo_lon: Optional[float]
    price: Optional[str]
    image_url: List[str]
    series_id: List[str]


@dataclass
class ScraperConfig:
    scraper_after: datetime
    scrape_until: datetime


class ScraperInterface(ABC):

    # Must implement
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Unique identifier string for this source e.g. 'magdeburg_tourist'"""
        pass

    @abstractmethod
    def scrape_events(self, config: ScraperConfig) -> List[Event]:
        """Full scrape orchestration. Returns list of Event objects."""
        pass
