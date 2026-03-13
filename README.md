# Spanish Vocab Tracker

A local web app for practising Spanish vocabulary with flashcard-style reveal and audio pronunciation.

## Requirements

- Python 3
- Flask (`pip3 install flask --break-system-packages`)

## Running

```bash
chmod +x start.sh
./start.sh
```

Then open **http://localhost:5050** in your browser.

## Features

- Flashcard reveal: click English to show Spanish, click either to hide
- Audio pronunciation via browser Web Speech API (uses Google Español es-ES if available)
- Add new lessons from within the app
- Add new words to any lesson
- Delete words or entire lessons
- All data saved to `lessons.json` — persists between sessions
