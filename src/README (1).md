# PayPal Support frontend

A small React + Vite frontend for a FastAPI customer-support backend. It uses regular React components, CSS, and `fetch`; there is no UI framework or hardcoded transaction data.

## Requirements
- Node.js 18+
- Your FastAPI server running and reachable from the browser

## Run it
1. Extract this folder.
2. Copy `.env.example` to `.env`.
3. Set `VITE_API_BASE_URL` to the address that the browser can reach, for example `http://127.0.0.1:8000`.
4. Set `VITE_CHAT_ENDPOINT` to the exact POST path shown in FastAPI Swagger.
5. If the backend expects a different request field, change `VITE_MESSAGE_FIELD` (default: `message`).
6. In this folder, run:

   ```bash
   npm install
   npm run dev
   ```

7. Open the Vite URL printed in the terminal.

## FastAPI notes
- Swagger's `/docs` URL is not the chat API URL. Open `/docs`, expand the chat endpoint, and copy its actual path and HTTP method.
- The frontend expects a JSON response with a reply field named `reply`, `answer`, `response`, or `message`.
- Optional fields supported:
  - `summary`: `{ "intent": "...", "details": "...", "sentiment": "..." }`
  - `visualization`: see the example below.
  - `status`: set to `"transfer"` to mark a human handoff.
- If FastAPI is on another origin, enable CORS for the Vite dev origin (usually `http://localhost:5173`). Do not use `*` with credentials in production.
- `127.0.0.1` means the computer running the browser. For another device on your LAN, use the FastAPI machine's LAN IP, and make sure the server is listening on `0.0.0.0`.

## Suggested response contract

```json
{
  "reply": "Your refund is being processed.",
  "summary": {
    "intent": "Refund status",
    "details": "Refund request is being processed",
    "sentiment": "concerned"
  },
  "visualization": {
    "type": "timeline",
    "title": "Refund progress",
    "status": "processing",
    "amount": "$42.00",
    "reference": "REF-123",
    "stages": [
      {
        "label": "Refund requested",
        "status": "completed",
        "description": "The request was received."
      },
      {
        "label": "Processing",
        "status": "processing",
        "description": "The refund is being handled."
      },
      {
        "label": "Refund completed",
        "status": "pending",
        "description": "Waiting for confirmation."
      }
    ],
    "updated_at": "2026-11-11 08:30"
  }
}
```

The example is a response shape only. Do not return made-up transaction statuses in a real support flow; populate these fields from your authorised backend data.

## Important
- Never put PayPal Client Secret, AI provider API keys, or other secrets in this frontend or a `VITE_*` variable. Vite exposes `VITE_*` values to the browser bundle.
- Keep secrets in FastAPI environment variables and have FastAPI call external services.
- This starter uses ordinary JSON responses. If your endpoint returns SSE or a streaming text response, the request handling needs to be adapted.
