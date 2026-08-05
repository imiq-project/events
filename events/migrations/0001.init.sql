CREATE TABLE events (
    id BIGSERIAL PRIMARY KEY,
    
    event_name TEXT NOT NULL,

    source TEXT[] NOT NULL,
    source_url TEXT[] NOT NULL,
    scraped_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    description TEXT,

    keywords TEXT[],

    start_iso TIMESTAMPTZ,
    end_iso TIMESTAMPTZ,

    venue_name TEXT,
    address TEXT,
    geo_lat DOUBLE PRECISION,
    geo_lon DOUBLE PRECISION,

    price TEXT,
    image_url TEXT[],
    series_id TEXT[]  DEFAULT NULL
);

CREATE INDEX idx_events_start_iso ON events (start_iso);
