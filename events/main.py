from .scraper_interface import ScraperInterface, Event, ScraperConfig
from .merge import merge_events
from .scrapers.dates_md_scraper import DatesMdScraper
from threading import Thread
import os

import schedule
from datetime import datetime, timezone, timedelta
import logging as log
import time
from .db import Database
from .api import app


class Runner:

    BATCH_SIZE = timedelta(days=7)
    LOOKAHEAD = timedelta(days=365)

    def __init__(self, db: Database) -> None:
        self.scrapers: list[ScraperInterface] = [
            DatesMdScraper(),
        ]
        self.db = db

    def check_scrape(self):
        now = datetime.now(timezone.utc)

        # Priority 1: Fill database up to the lookahead
        latest = self.db.get_latest_date()
        if latest is None or latest < now + self.LOOKAHEAD:
            if latest:
                start_date = latest
            else:
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + self.BATCH_SIZE
            config = ScraperConfig(
                scraper_after=start_date,
                scrape_until=end_date,
            )
            log.info(f"Scraping to fill ahead: {start_date} till {end_date}")
            self.run_scrape(config)
            return

        # Priority 2: Check correctness of events upcoming soon
        # TODO

        # Priority 3: Re-scrape events which have been scraped a long time ago
        # TODO

    def run_scrape(self, config: ScraperConfig):
        pool: list[Event] = []
        for scraper in self.scrapers:
            try:
                log.info(
                    f"Scraping {scraper.source_name} until {config.scrape_until}..."
                )
                events = scraper.scrape_events(config)
                log.info(f"{scraper.source_name}: {len(events)} events after URL dedup")
                pool = merge_events(pool, events)
            except Exception as e:
                log.error(f"{scraper.source_name} failed: {e}", exc_info=True)

        log.info(f"After URL merge: {len(pool)} events")

        # pool = find_and_handle_duplicates(pool)
        # log.info(f"After fuzzy dedup: {len(pool)} events")

        try:
            self.db.upsert_events(pool)
        except Exception as e:
            log.error(f"DB write failed: {e}", exc_info=True)

    def run(self):
        scheduler = schedule.Scheduler()
        self.check_scrape()
        scheduler.every().day.at("03:00").do(self.check_scrape)
        scheduler.every().day.at("22:00").do(self.check_scrape)
        while True:
            scheduler.run_pending()
            time.sleep(60)


if __name__ == "__main__":
    log.basicConfig(
        level="INFO",
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    db = Database(
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", 5432)),
        username=os.environ.get("DB_USER", "postgres"),
        password=os.environ["DB_PASSWORD"],  # required
        database=os.environ.get("DB_DATABASE", "postgres"),
    )
    db.migrate()

    runner = Runner(db)
    Thread(target=runner.run).start()

    app.db = db
    app.run(host="0.0.0.0", port=3000)
