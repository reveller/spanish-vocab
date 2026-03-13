# Spanish Vocab Tracker

A local web app for practising Spanish vocabulary with flashcard-style reveal and audio pronunciation.

## Features

- Flashcard reveal: click English to show Spanish, click either to hide
- Audio pronunciation via browser Web Speech API (uses Google Español es-ES if available)
- Progress tracking per lesson (not started / still learning / mastered)
- Add new lessons and words from within the app
- Delete words or entire lessons
- Data persisted in SQLite — survives restarts

## Quick Start (Local)

```bash
pip3 install -r requirements.txt
chmod +x start.sh
./start.sh
```

Open **http://localhost:5050** in your browser.

## Quick Start (Docker)

```bash
docker compose up --build
```

The app runs on **http://localhost:5050**. Data is stored in a named Docker volume (`vocab-data`) so it persists across container restarts.

## Architecture

| Component | Technology |
|-----------|-----------|
| Server | Flask + Gunicorn (1 worker, 2 threads) |
| Database | SQLite with WAL mode |
| Frontend | Vanilla HTML/CSS/JS |
| Deployment | Docker + docker-compose |

### Database

Two tables with a foreign key relationship:

- **lessons** — `id`, `title`, `progress`, `sort_order`
- **words** — `id`, `lesson_id` (FK), `en`, `es`, `sort_order`

On first run, `lessons.json` is imported as seed data. Subsequent starts skip seeding.

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serves the frontend |
| `GET` | `/api/health` | Health check |
| `GET` | `/api/lessons` | List all lessons with words |
| `POST` | `/api/lessons` | Create a lesson |
| `DELETE` | `/api/lessons/:id` | Delete a lesson |
| `PUT` | `/api/lessons/:id/progress` | Update lesson progress |
| `POST` | `/api/lessons/:id/words` | Add a word to a lesson |
| `DELETE` | `/api/lessons/:id/words/:index` | Delete a word by index |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_PATH` | `/data/vocab.db` | Path to SQLite database file |
| `PORT` | `5050` | Server port (dev mode only) |
| `DEBUG` | `false` | Enable Flask debug mode |

## File Structure

```
app.py              # Flask routes
db.py               # SQLite data access layer
lessons.json        # Seed data (imported on first run)
start.sh            # Local dev launcher
requirements.txt    # Python dependencies
Dockerfile          # Container image
docker-compose.yml  # Container orchestration
static/index.html   # Frontend SPA
```
