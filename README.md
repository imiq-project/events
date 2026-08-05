# IMIQ Events Scraper

## Development Setup

### Using docker (recommended)
The `docker-compose.yml` already provides a docker based config for local development.
You can spin it up using:

```sh
docker compose up -d
```

Then enter the development container using

```sh
docker compose exec scraper bash
```

And inside the container:

```sh
python -m events.main
```

### Without docker
Create a virtual environment first

```sh
python -m venv .venv
source .venv/bin/activate.sh
```

The actual procedure depends on your platform and is described here: https://docs.python.org/3/library/venv.html
Next install required packages:

```sh
pip install -r requirements.txt
```

Additionally, you need a postgres database.

Finally, start the application using

```sh
python -m events.main
```