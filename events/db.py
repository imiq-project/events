from datetime import datetime, timezone
from typing import Optional, List
from scraper_interface import Event
from psycopg2 import pool
from yoyo import read_migrations
from yoyo import get_backend
from contextlib import contextmanager


class Database:

    def __init__(
        self, username: str, password: str, host: str, database: str, port: int
    ) -> None:
        self.conninfo = f"postgresql://{username}:{password}@{host}/{database}"
        self.pool = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            host=host,
            database=database,
            user=username,
            password=password,
            port=port,
        )

    @contextmanager
    def _get_connection(self):
        conn = self.pool.getconn()
        try:
            yield conn
        finally:
            self.pool.putconn(conn)

    def migrate(self):
        backend = get_backend(self.conninfo)
        migrations = read_migrations("migrations")
        with backend.lock():
            backend.apply_migrations(backend.to_apply(migrations))

    def get_latest_date(self) -> Optional[datetime]:
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT MAX(start_iso) FROM events",
                )
                result = cursor.fetchone()
                if result and result[0] is not None:
                    dt = result[0]
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
            return None

    def get_all_events(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> List[Event]:
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                query = "SELECT event_name, source, source_url, scraped_at, description, keywords, start_iso, end_iso, venue_name, address, geo_lat, geo_lon, price, image_url, series_id FROM events"
                params = {}
                clauses: list[str] = []

                if from_date is not None:
                    clauses.append("start_iso >= %(from_date)s")
                    params["from_date"] = from_date
                if to_date is not None:
                    clauses.append("start_iso <= %(to_date)s")
                    params["to_date"] = to_date
                if clauses:
                    query += " WHERE " + " AND ".join(clauses)

                query += " ORDER BY start_iso ASC NULLS LAST;"
                cursor.execute(query, params)
                rows = cursor.fetchall()

        events: List[Event] = []
        for row in rows:
            event_name, source, source_url, scraped_at, description, keywords, start_iso, end_iso, venue_name, address, geo_lat, geo_lon, price, image_url, series_id = row
            if start_iso is not None and start_iso.tzinfo is None:
                start_iso = start_iso.replace(tzinfo=timezone.utc)
            if end_iso is not None and end_iso.tzinfo is None:
                end_iso = end_iso.replace(tzinfo=timezone.utc)
            events.append(
                Event(
                    event_name=event_name,
                    source=source,
                    source_url=source_url,
                    scraped_at=scraped_at,
                    description=description,
                    keywords=keywords,
                    start_iso=start_iso,
                    end_iso=end_iso,
                    venue_name=venue_name,
                    address=address,
                    geo_lat=geo_lat,
                    geo_lon=geo_lon,
                    price=price,
                    image_url=image_url,
                    series_id=series_id,
                )
            )
        return events


    def upsert_events(self, events: list[Event]):
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                for e in events:
                    row = {
                        "event_name": e.event_name,
                        "source": e.source,
                        "source_url": e.source_url,
                        "scraped_at": e.scraped_at,
                        "description": e.description,
                        "keywords": e.keywords,
                        "start_iso": e.start_iso,
                        "end_iso": e.end_iso,
                        "venue_name": e.venue_name,
                        "address": e.address,
                        "geo_lat": e.geo_lat,
                        "geo_lon": e.geo_lon,
                        "price": e.price,
                        "image_url": e.image_url,
                        "series_id": e.series_id,
                    }
                    cursor.execute(
                        """
                        INSERT INTO events (
                            event_name, source, source_url,
                            scraped_at, description, keywords, start_iso, end_iso,
                            venue_name, address, geo_lat, geo_lon, price,
                            image_url, series_id
                        ) VALUES (
                            %(event_name)s, %(source)s, %(source_url)s,
                            %(scraped_at)s, %(description)s, %(keywords)s, %(start_iso)s, %(end_iso)s,
                            %(venue_name)s, %(address)s, %(geo_lat)s, %(geo_lon)s, %(price)s,
                            %(image_url)s, %(series_id)s
                        )
                        """,
                        row,
                    )
                conn.commit()
