# Personal AI Chatbot

A private terminal chatbot powered by a local Ollama model. It saves recent conversation history and facts you explicitly ask it to remember on this computer.

## Requirements

- Python 3.10 or newer
- [Ollama](https://ollama.com/) installed and running

## Setup

From this project directory, install the Python dependencies and download the default model:

```powershell
python -m pip install -r requirements-llm.txt
ollama pull llama3.2
Copy-Item .env.example .env
```

Start the chatbot:

```powershell
python main.py
```

If using the workspace virtual environment from the parent directory, run:

```powershell
& ".\.venv\Scripts\python.exe" ".\personal_ai_chatbot\main.py"
```

## Commands

- `/help` shows commands.
- `/remember <fact>` saves a personal fact for future chats.
- `/memory` lists saved facts and the number of stored conversation turns.
- `/forget` deletes saved facts but keeps conversation history.
- `/clear` deletes conversation history but keeps saved facts.
- `/faqs` lists the FAQ entries.
- `/exit` quits.

## Configuration

Copy `.env.example` to `.env` and set:

- `OLLAMA_MODEL` to a model already installed in Ollama (default: `llama3.2`).
- `OLLAMA_HOST` to the Ollama server address (default: `http://localhost:11434`).
- `OLLAMA_MAX_TURNS` to the number of recent chat turns sent as context (default: `12`).

## Personal FAQs

Add your own reference entries to `data/faqs.json`:

```json
[
	{
		"question": "What time do I usually start work?",
		"answer": "I usually start at 9 AM."
	}
]
```

Relevant entries are included as reference context when you ask related questions. The chatbot does not edit this file.

## Local data and tests

Saved facts and recent conversation turns are stored in `data/memory.json`. They are plain text on disk and are not sent anywhere except as context to your configured Ollama server. Back up or delete this file to manage that data.

Run the test suite with:

```powershell
python -m unittest discover -s tests -v
```