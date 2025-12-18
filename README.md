# 🤖 MEGA-ULTRA-ROBOTER-KI

## 🚀 PayPal Revenue Maximization System

**STATUS: LIVE (PRODUCTION)** 🟢

This system is a fully autonomous revenue maximization bot connected to the PayPal Live API. It monitors transactions in real-time and uses AI (Claude/Grok/Local Core) to analyze sales and suggest upsells.

### ✅ Features

- **Real-Time Monitoring:** Checks PayPal for new transactions every 10 seconds.
- **AI Analysis:** Uses Claude 3 Opus or Grok Beta to analyze buyer behavior.
- **Local Core Fallback:** Continues to work even if AI credits run out.
- **Secure:** API keys are stored locally in `env.ini` and never uploaded to Git.

### 🛠️ How to Start

1. Double-click **`START_ROBOTER.bat`** on your Desktop.
2. Keep the black window open.
3. The Dashboard will open automatically in your browser (`http://localhost:8502`).

### 🔑 Configuration

- **PayPal Keys:** Managed in `env.ini` (Live Mode).
- **AI Keys:** Managed in `env.ini` (Claude/Grok).

### ⚠️ Important Notes

### 🛠️ Why revenue can stay at €0.00

If PayPal auth works but transactions never show up, the PayPal Reporting API (`/v1/reporting/transactions`) can return **403 NOT_AUTHORIZED** due to **insufficient permissions**.

### 🔔 Recommended: Webhooks ingestion (works without Reporting permissions)

This repo includes a local webhook ingest server that writes incoming PayPal events to `data/paypal_events.jsonl`, and the Streamlit dashboard can display revenue from those events.

1) Start the webhook server

- Run `RUN_WEBHOOK_SERVER.bat` (local: `http://127.0.0.1:8503/health`)

2) Configure PayPal Webhook

- Webhook URL: `https://<your-public-url>/paypal/webhook`
- Add event types like `PAYMENT.CAPTURE.COMPLETED`

3) Add env keys (never commit secrets)

- `PAYPAL_WEBHOOK_ID`
- `PAYPAL_CLIENT_ID` / `PAYPAL_CLIENT_SECRET`
- Optional Sandbox keys: `PAYPAL_ENV=SANDBOX`, `PAYPAL_SANDBOX_CLIENT_ID`, `PAYPAL_SANDBOX_CLIENT_SECRET`, `PAYPAL_SANDBOX_WEBHOOK_ID`

4) In the Streamlit sidebar

- Set "PAYPAL MODE" to `WEBHOOKS (Recommended)`.

*System verified and deployed on 2025-12-17.*
