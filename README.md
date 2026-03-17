# Cards (Flask) — Polish → translation

Web app with flashcards for language learning:
- click the card or press **Space** to flip (Polish ↔ translation)
- **→ / ArrowRight** — next random card
- **← / ArrowLeft** — previous card from history (up to 30 recent, stored in cookie session)
- **Upload** — import `pl – translation` pairs with deduplication by Polish text

## Local run (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export SECRET_KEY="change-me"
flask --app app run --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000`.

By default, SQLite is stored in `./data/cards.sqlite` (created automatically).

## Run with Docker (recommended)

The DB is stored **outside the container** (in the project folder `./data`); the path is configurable via `DB_PATH`.

### Option 1: docker compose

```bash
docker compose up --build
```

Open `http://localhost:8000`.

### Option 2: docker run

```bash
docker build -t cards .
mkdir -p data
docker run --rm -p 8000:8000 \
  -e DB_PATH=/data/cards.sqlite \
  -e SECRET_KEY=change-me \
  -v "$(pwd)/data:/data" \
  cards
```

## Import format

Paste lines like:

```
zadbany – well-groomed
skąpy – stingy
godny zaufania – trustworthy
```

Supported separators: `-`, `–`, `—`. Empty lines are ignored.
