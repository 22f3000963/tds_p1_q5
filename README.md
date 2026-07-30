# Data Analyst Telegram Bot

This is a Telegram Bot built for a Data Science exam project. It acts as a data analyst, processing natural language questions via an LLM and returning exactly formatted JSON responses.

## Features
- **Always-on:** Hosted 24/7 on Render as a Background Worker.
- **LLM Integration:** Connects to `aipipe.org` using the `gpt-5-mini` model to dynamically answer analytical questions.
- **Strict Formatting:** Injects a dynamic `log_url` and ensures all responses strictly adhere to requested JSON schemas without Markdown wrapping or conversational filler.
- **Run Logging:** Every incoming and outgoing message is logged to a public `run.jsonl` file.

## Tech Stack
- Python 3
- `python-telegram-bot` for async long-polling
- `requests` for native API integration
- Hosted on [Render](https://render.com/)

## How it works
1. You message the bot a question, optionally specifying the exact JSON format you want back.
2. The bot passes your chat history to the LLM.
3. The bot extracts the raw JSON from the LLM, injects its public log URL, and replies to you.
