from unittest import TestCase
import responses
import datetime

from events.scrapers.dates_md_scraper import DatesMdScraper
from events.scraper_interface import ScraperConfig
from pathlib import Path

script_dir = Path(__file__).parent.parent
fixtures_dir = script_dir / "fixtures" / "dates_md"

def date_with_tz(s: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(s).replace(tzinfo=datetime.timezone.utc)

class DatesMdScraperTest(TestCase):

    def test_parse_listing(self):
        scraper = DatesMdScraper()
        with open(fixtures_dir / "listing.html", "r") as f:
            listing_html = f.read()
        stubs, has_next = scraper.parse_listing_page(listing_html)
        self.assertTrue(has_next)
        self.assertEqual(len(stubs), 20)
        for stub in stubs:
            self.assertIn("description", stub)
            self.assertIn("startDate", stub)
            self.assertIn("endDate", stub)
            self.assertIn("url", stub)
            self.assertIn("eventStatus", stub)
            self.assertIn("name", stub)
            self.assertIn("image", stub)
            self.assertIn("location", stub)
        # Test first stub
        self.assertEqual(stubs[0]["startDate"], "2026-07-28T11:00:00")
        self.assertEqual(stubs[0]["endDate"], "2026-07-28T17:00:00")
        self.assertEqual(
            stubs[0]["name"],
            "Thomas Bachler - Am Fluss & Sonnenblumen (Fotografie, Druckgrafik)",
        )

    @responses.activate
    def test_fetch(self):
        with open(fixtures_dir / "listing.html", "r") as f:
            listing_html = f.read()

        scraper = DatesMdScraper(max_pages=1)
        responses.get(
            "https://www.dates-md.de/search/event/veranstaltungen-magdeburg/?search_date=2026-07-28&search_date_end=2026-07-28&page=1",
            body=listing_html,
        )
        config = ScraperConfig(
            scraper_after=date_with_tz("2026-07-28T17:00:00"),
            scrape_until=date_with_tz("2026-07-28T17:00:00"),
        )
        events = scraper.scrape_events(config)
        self.assertEqual(len(events), 20)
        # check last event
        last_event = events[-1]
        self.assertEqual(last_event.event_name, "Arezo Tajik - Mein Weg in Linien")
        # TODO: this should be at 11:00!
        self.assertEqual(last_event.start_iso,  datetime.datetime(2026, 7, 28, 0, 0, tzinfo=datetime.timezone.utc))
        self.assertEqual(last_event.end_iso,  datetime.datetime(2026, 7, 28, 18, 0, tzinfo=datetime.timezone.utc))
