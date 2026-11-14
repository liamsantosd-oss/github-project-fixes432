# Google AI Studio handoff notes

This repository is currently an offline archive, not an AI Studio application. It uses a Python standard-library HTTP server and captured Roblox page snapshots; it does not contain an AI model, Google AI Studio configuration, or Gemini API integration.

## If adding Gemini later
- Start with a separate, clearly named feature or service rather than replacing the static archive server.
- Prototype prompts and model behavior in Google AI Studio, then export/copy the generated integration into a maintained module.
- Keep API keys server-side in environment variables (for example `GEMINI_API_KEY`); never put secrets in HTML, browser JavaScript, commits, or screenshots.
- Add a `.env.example` containing variable names only, and keep `.env` ignored.
- Use the official Google Gen AI SDK and current documentation for the chosen runtime; pin and review dependencies before adding them.
- Add explicit error handling, request limits, timeouts, and tests with a mocked model response. Do not make the archived pages depend on Gemini to load.
- Document what Gemini sends/receives and avoid sending Roblox credentials, account data, or other sensitive material.

## Current boundaries
The archive runs without Google credentials, Node dependencies, or internet access. Its saved pages and API fixtures are read-only and finite. The local catalog helper filters and sorts only the cards present in the captured marketplace page; it does not call Roblox or Gemini.