# 🤖 MEGA-ULTRA-ROBOTER-KI

## 🚀 PayPal Revenue via Webhooks

Kernpfad: **PayPal Webhook → JSONL (`data/paypal_events.jsonl`) → `/stats` → Streamlit Dashboard**.

### ✅ Features

- Webhook-Receiver (FastAPI): `POST /paypal/webhook`, `GET /stats`, `GET /health`
- Streamlit Dashboard (8502) liest Umsatz aus `/stats` (remote) oder lokalem JSONL-Fallback
- Optionale PayPal Checkout Demo: `POST /paypal/create-order`, `POST /paypal/capture-order`

### 🛠️ Lokales Starten

Empfohlen (VS Code Tasks):

- Webhook Server: Task "MEGA: Run Webhook Server (8503)"
- Dashboard: Task "MEGA: Run Streamlit Dashboard (8502)"

Alternativ manuell:

1. Webhook Server: `python webhook_server.py` (Port via `WEBHOOK_PORT`/`PORT`, default 8503)
2. Dashboard: `python -m streamlit run dashboard_ui.py --server.port 8502`

### 🔑 Konfiguration (niemals Secrets committen)

Nutze `.env.example` als Vorlage und halte echte Secrets nur lokal in `env.ini`/`.env` oder als Deployment-Secrets.

Für echte Webhook-Verifikation (LIVE oder SANDBOX):

- `PAYPAL_CLIENT_ID`
- `PAYPAL_CLIENT_SECRET`
- `PAYPAL_WEBHOOK_ID`

### ⚠️ Hinweise

#### Warum Umsatz bei €0.00 bleiben kann

Wenn PayPal Auth klappt, aber Transaktionen nie auftauchen: Die PayPal Reporting API kann **403 NOT_AUTHORIZED** liefern (Permissions). Dieses Repo setzt daher primär auf **Webhook-Ingestion** statt Polling.

#### Webhooks (empfohlen)

1. Webhook Server starten
	- `RUN_WEBHOOK_SERVER.bat` (Health: `http://127.0.0.1:8503/health`)
	- Hinweis: `POST /paypal/webhook` ist standardmäßig **LIVE-strikt** (erwartet echte PayPal-Signatur-Header). Unsigned lokale Tests sind DEV-only via `ALLOW_UNVERIFIED_WEBHOOKS=true`.
2. PayPal Webhook konfigurieren
	- Webhook URL: `https://<your-public-url>/paypal/webhook`
	- Event Types z.B. `PAYMENT.CAPTURE.COMPLETED`
3. Dashboard an `/stats` hängen
	- In `env.ini`: `PAYPAL_INGEST_BASE_URL=https://<your-public-url>` oder `PAYPAL_STATS_URL=https://<your-public-url>/stats`

*System verified and deployed on 2025-12-17.*
