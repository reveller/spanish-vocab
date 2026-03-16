#!/bin/bash
export DATABASE_PATH=./vocab.db
export SECRET_KEY=dev-local-secret
# Set SEED_USER_EMAIL and SEED_USER_PASSWORD on first run to create the user.
# Once seeded, these can be removed.
echo "Starting Spanish Vocab Tracker..."
echo "Open your browser at: http://localhost:5050"
echo "Press Ctrl+C to stop."
cd "$(dirname "$0")"
python3 app.py
