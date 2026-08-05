import os
from datetime import datetime, date, timezone
import psycopg2
import psycopg2.extras
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Magdeburg Events</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: system-ui, sans-serif; background: #f5f5f5; color: #222; padding: 2rem; }
        h1 { margin-bottom: 0.5rem; font-size: 1.75rem; }
        .meta { color: #666; font-size: 0.9rem; margin-bottom: 1.5rem; }
        .controls { display: flex; flex-wrap: wrap; gap: 1rem; align-items: flex-end; margin-bottom: 1.5rem; }
        .control-group { display: flex; flex-direction: column; gap: 0.3rem; }
        label { font-size: 0.9rem; color: #444; }
        input[type="date"] { padding: 0.5rem 0.75rem; border: 1px solid #ddd; border-radius: 8px; background: #fff; }
        button { padding: 0.65rem 1rem; border: none; border-radius: 8px; background: #1a56db; color: #fff; cursor: pointer; font-weight: 600; }
        button:hover { background: #1648b3; }
        .status { color: #444; margin-bottom: 1rem; }
        .table-wrap { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
        thead { background: #1a1a2e; color: #fff; }
        th, td { padding: 0.85rem 1rem; text-align: left; vertical-align: top; }
        th { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; }
        td { font-size: 0.9rem; border-top: 1px solid #eee; }
        tr:hover td { background: #f9f9ff; }
        .source-badge { display: inline-flex; align-items: center; gap: 0.4rem; background: #e8f0fe; color: #1a56db; padding: 0.15rem 0.5rem; border-radius: 999px; font-size: 0.75rem; }
        .price { color: #15803d; font-weight: 600; }
        .no-data { text-align: center; color: #888; padding: 2rem; }
        a { color: #1a56db; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>📅 Magdeburg Events</h1>
    <div class="meta" id="event-meta">Loading events...</div>
    <div class="controls">
        <div class="control-group">
            <label for="from-date">From</label>
            <input id="from-date" type="date" />
        </div>
        <div class="control-group">
            <label for="to-date">To</label>
            <input id="to-date" type="date" />
        </div>
        <button id="refresh-button" type="button">Refresh</button>
    </div>

    <div class="status" id="status"></div>
    <div class="table-wrap">
        <table id="events-table">
            <thead>
                <tr>
                    <th>Event</th>
                    <th>Source</th>
                    <th>Description</th>
                    <th>Start</th>
                    <th>End</th>
                    <th>Venue</th>
                </tr>
            </thead>
            <tbody id="events-body">
                <tr><td class="no-data" colspan="6">Loading events…</td></tr>
            </tbody>
        </table>
    </div>

    <script>
        const metaEl = document.getElementById('event-meta');
        const statusEl = document.getElementById('status');
        const bodyEl = document.getElementById('events-body');
        const refreshButton = document.getElementById('refresh-button');
        const fromInput = document.getElementById('from-date');
        const toInput = document.getElementById('to-date');

        function formatDate(isoValue) {
            if (!isoValue) return '';
            const date = new Date(isoValue);
            return new Intl.DateTimeFormat('default', {
                dateStyle: 'medium',
                timeStyle: 'short'
            }).format(date);
        }

        function renderEvents(events) {
            bodyEl.innerHTML = '';

            if (!events.length) {
                bodyEl.innerHTML = '<tr><td class="no-data" colspan="6">No events found for the selected range.</td></tr>';
                metaEl.textContent = '0 events found';
                return;
            }

            metaEl.textContent = `${events.length} event${events.length !== 1 ? 's' : ''} found`;

            for (const event of events) {
                const row = document.createElement('tr');
                const sourceText = Array.isArray(event.source) ? event.source.join(', ') : event.source;
                const sourceUrl = Array.isArray(event.source_url) ? event.source_url[0] : event.source_url;

                row.innerHTML = `
                    <td><a href="${sourceUrl || '#'}" target="_blank" rel="noreferrer noopener">${event.event_name || 'Unnamed event'}</a></td>
                    <td>${sourceText || ''}</td>
                    <td>${event.description}</td>
                    <td>${formatDate(event.start_iso)}</td>
                    <td>${formatDate(event.end_iso)}</td>
                    <td>${event.venue_name || ''}${event.address ? ', ' + event.address : ''}</td>
                `;
                bodyEl.appendChild(row);
            }
        }

        async function fetchEvents() {
            statusEl.textContent = '';
            metaEl.textContent = 'Loading events…';
            bodyEl.innerHTML = '<tr><td class="no-data" colspan="6">Loading events…</td></tr>';

            const params = new URLSearchParams();
            if (fromInput.value) params.set('from', fromInput.value);
            if (toInput.value) params.set('to', toInput.value);

            try {
                const response = await fetch('/api/events?' + params.toString());
                if (!response.ok) {
                    const payload = await response.json().catch(() => ({}));
                    statusEl.textContent = payload.error || 'Unable to load events';
                    bodyEl.innerHTML = '<tr><td class="no-data" colspan="6">Failed to load events.</td></tr>';
                    return;
                }

                const events = await response.json();
                renderEvents(events);
            } catch (error) {
                statusEl.textContent = 'Error fetching events.';
                bodyEl.innerHTML = '<tr><td class="no-data" colspan="6">Could not load events.</td></tr>';
            }
        }

        refreshButton.addEventListener('click', fetchEvents);
        document.addEventListener('DOMContentLoaded', fetchEvents);
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

def _parse_datetime_param(value: str):
    if not value:
        return None

    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        try:
            parsed_date = date.fromisoformat(value)
            parsed = datetime(parsed_date.year, parsed_date.month, parsed_date.day, tzinfo=timezone.utc)
        except ValueError:
            return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed


def _event_to_dict(event):
    data = dict(event.__dict__)
    for field in ("scraped_at", "start_iso", "end_iso"):
        value = data.get(field)
        if value is not None:
            data[field] = value.isoformat()
    return data


@app.route("/api/events")
def events():
    from_date = _parse_datetime_param(request.args.get("from", ""))
    to_date = _parse_datetime_param(request.args.get("to", ""))

    if request.args.get("from") and from_date is None:
        return jsonify({"error": "Invalid 'from' datetime"}), 400
    if request.args.get("to") and to_date is None:
        return jsonify({"error": "Invalid 'to' datetime"}), 400
    if from_date is not None and to_date is not None and from_date > to_date:
        return jsonify({"error": "'from' must be before or equal to 'to'"}), 400

    events = app.db.get_all_events(from_date=from_date, to_date=to_date)
    return jsonify([_event_to_dict(event) for event in events])
