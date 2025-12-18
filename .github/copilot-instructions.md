# Copilot Instructions (MEGA-ULTRA-ROBOTER-KI)

## Big Picture
- Streamlit UI zeigt Revenue/Logs und ist **WEBHOOKS-only** (kein POLLING/Reporting-API mehr im Dashboard).
- Webhook-Ingest ist der robuste Weg (keine Reporting-API-Rechte nötig): FastAPI Server empfängt PayPal Webhooks, verifiziert Signaturen und persistiert Events.

## Wichtige Entry Points
- Dashboard (Streamlit): `dashboard_ui.py` (Standard-Port 8502)
- Webhook Receiver (FastAPI): `webhook_server.py` (Standard-Port 8503; in Cloud via `PORT`)
- Simple API Demo (FastAPI): `main.py` (Port 8000; eher Launcher/Smoke-API)
- Alternative/ältere Dashboards: `new_dashboard.py`, `paypal_maximizer.py` (nur anfassen, wenn du gezielt diese Variante ändern willst)

## Lokales Starten (Windows)
- VS Code Tasks bevorzugen:
  - `MEGA: Run Streamlit Dashboard (8502)`
  - `MEGA: Run Webhook Server (8503)`
- Alternativ per CLI:
  - `python -m streamlit run dashboard_ui.py --server.port 8502`
  - `python webhook_server.py` (Health: `http://127.0.0.1:8503/health`)

## Datenfluss: Webhooks → Revenue
- `webhook_server.py` Endpoints:
  - `POST /paypal/webhook` (PayPal webhook)
  - `GET /stats` (MVP Aggregation für Dashboard)
  - `GET /health`
- `GET /stats` liefert i.d.R. das Shape: `{ events, gross: {CCY: number}, estimated_net: {CCY: number} }` (Dashboard bevorzugt `estimated_net`, sonst `gross`).
- Persistenz:
  - Lokal JSONL: `data/paypal_events.jsonl` (override via `PAYPAL_EVENTS_PATH`, auch über `env.ini`/`.env` möglich)
  - Optional Azure Blob (durable): `AZURE_STORAGE_CONNECTION_STRING` (+ optional `PAYPAL_EVENTS_CONTAINER`, `PAYPAL_EVENTS_PREFIX`)
  - Storage-Fehler sollen Webhook nicht abbrechen: Ingest soll trotzdem 200/ACK liefern.
- Dashboard kann Stats remote holen: setze `PAYPAL_STATS_URL` oder `PAYPAL_INGEST_BASE_URL` (siehe `dashboard_ui.py`).

## Secrets/Config
- Keys werden aus `env.ini` bevorzugt, dann `.env`, dann Environment gelesen (siehe `webhook_server.py` und `dashboard_ui.py`).
- PayPal (LIVE/SANDBOX): `PAYPAL_ENV` steuert Basen-URL und welche Keys genutzt werden.
- Niemals Secrets committen; Repo enthält Hinweise zur Bereinigung in `DEPLOY_STREAMLIT.md`.

## Azure Deploy (Webhook 24/7)
- Azure Container Apps Quickstart: `azure/aca_deploy.ps1` (baut `Dockerfile.webhook` per `az acr build` und deployed ACA).
- Optional Storage Setup: `azure/storage_setup.ps1`.
- Doku: `azure/README.md`.

## Repo-Konventionen / Stolpersteine
- Viele Root-Dateien sind Launcher/Installer/Backups (z.B. `dashboard_ui.py.*.bak`): ändere nur die „aktive“ Datei, nicht die Backups.
- `manifest.json` ist sehr groß und wirkt wie generiertes Asset/Bundle-Mapping: nicht manuell bearbeiten.
- Keine Testsuite im Repo; Änderungen lokal via Dashboard/Webhook-Health prüfen.
