#!/bin/bash
export DATABASE_PATH=./vocab.db
echo "Starting Spanish Vocab Tracker..."
echo "Open your browser at: http://localhost:5050"
echo "Press Ctrl+C to stop."
cd "$(dirname "$0")"
python3 app.py
