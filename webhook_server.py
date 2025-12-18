import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Tuple

import requests
from fastapi import FastAPI, Header, HTTPException, Request

try:
    from azure.core.exceptions import ResourceExistsError
    from azure.storage.blob import BlobServiceClient
except Exception:  # Azure deps optional (local-only mode)
    ResourceExistsError = None
    BlobServiceClient = None


BASE_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class PayPalConfig:
    base_url: str
    client_id: str
    client_secret: str
    webhook_id: str


def _load_kv_file(path: Path, into: dict) -> None:
    if not path.exists():
        return
    try:
        for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and k not in into:
                into[k] = v
    except Exception:
        return


def load_api_keys() -> dict:
    keys: dict = {}
    _load_kv_file(BASE_DIR / "env.ini", keys)
    _load_kv_file(BASE_DIR / ".env", keys)
    return keys


def _get_key(keys: dict, name: str, default: str = "") -> str:
    return (os.getenv(name) or keys.get(name) or default).strip()


def _detect_env(keys: dict) -> str:
    env = (_get_key(keys, "PAYPAL_ENV") or _get_key(keys, "ENV") or "LIVE").upper()
    if env not in {"LIVE", "SANDBOX"}:
        env = "LIVE"
    return env


def get_paypal_config() -> PayPalConfig:
    keys = load_api_keys()
    env = _detect_env(keys)

    if env == "SANDBOX":
        base_url = "https://api-m.sandbox.paypal.com"
        client_id = _get_key(keys, "PAYPAL_SANDBOX_CLIENT_ID") or _get_key(keys, "PAYPAL_CLIENT_ID")
        client_secret = _get_key(keys, "PAYPAL_SANDBOX_CLIENT_SECRET") or _get_key(keys, "PAYPAL_CLIENT_SECRET")
        webhook_id = _get_key(keys, "PAYPAL_SANDBOX_WEBHOOK_ID") or _get_key(keys, "PAYPAL_WEBHOOK_ID")
    else:
        base_url = "https://api-m.paypal.com"
        client_id = _get_key(keys, "PAYPAL_CLIENT_ID")
        client_secret = _get_key(keys, "PAYPAL_CLIENT_SECRET")
        webhook_id = _get_key(keys, "PAYPAL_WEBHOOK_ID")

    if not client_id or not client_secret:
        raise RuntimeError("Missing PayPal client credentials (PAYPAL_CLIENT_ID/SECRET).")
    if not webhook_id:
        raise RuntimeError("Missing PayPal webhook id (PAYPAL_WEBHOOK_ID).")

    return PayPalConfig(
        base_url=base_url,
        client_id=client_id,
        client_secret=client_secret,
        webhook_id=webhook_id,
    )


def get_access_token(cfg: PayPalConfig) -> str:
    url = f"{cfg.base_url}/v1/oauth2/token"
    resp = requests.post(
        url,
        headers={"Accept": "application/json", "Accept-Language": "en_US"},
        data={"grant_type": "client_credentials"},
        auth=(cfg.client_id, cfg.client_secret),
        timeout=12,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"PayPal auth failed: {resp.status_code} {resp.text[:500]}")
    token = (resp.json() or {}).get("access_token")
    if not token:
        raise RuntimeError("PayPal auth succeeded but no access_token returned")
    return token


def verify_webhook_signature(cfg: PayPalConfig, payload: dict, headers: dict) -> bool:
    token = get_access_token(cfg)
    url = f"{cfg.base_url}/v1/notifications/verify-webhook-signature"

    body = {
        "auth_algo": headers.get("paypal-auth-algo"),
        "cert_url": headers.get("paypal-cert-url"),
        "transmission_id": headers.get("paypal-transmission-id"),
        "transmission_sig": headers.get("paypal-transmission-sig"),
        "transmission_time": headers.get("paypal-transmission-time"),
        "webhook_id": cfg.webhook_id,
        "webhook_event": payload,
    }

    resp = requests.post(
        url,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        json=body,
        timeout=12,
    )

    if resp.status_code != 200:
        return False
    status = (resp.json() or {}).get("verification_status")
    return status == "SUCCESS"


def _local_events_path() -> Path:
    raw = os.getenv("PAYPAL_EVENTS_PATH")
    if raw:
        return Path(raw)
    return BASE_DIR / "data" / "paypal_events.jsonl"


def _append_local_record(record: dict) -> None:
    out_path = _local_events_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.open("a", encoding="utf-8").write(json.dumps(record, ensure_ascii=False) + "\n")


def _get_event_id(payload: dict) -> str:
    return (
        str(payload.get("id") or "")
        or str((payload.get("resource") or {}).get("id") or "")
        or f"noid_{int(datetime.now(tz=timezone.utc).timestamp())}"
    )


def _azure_blob_settings() -> Optional[Tuple[str, str, str]]:
    conn = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not conn:
        return None

    container = os.getenv("PAYPAL_EVENTS_CONTAINER") or "paypal-events"
    prefix = (os.getenv("PAYPAL_EVENTS_PREFIX") or "events").strip("/")
    return conn, container, prefix


_blob_container_client = None


def _get_blob_container_client():
    global _blob_container_client

    settings = _azure_blob_settings()
    if not settings:
        return None

    if BlobServiceClient is None:
        raise RuntimeError("azure-storage-blob not installed but AZURE_STORAGE_CONNECTION_STRING is set")

    if _blob_container_client is not None:
        return _blob_container_client

    conn, container, _prefix = settings
    svc = BlobServiceClient.from_connection_string(conn)
    cc = svc.get_container_client(container)
    try:
        cc.create_container()
    except Exception:
        pass

    _blob_container_client = cc
    return cc


def _store_blob_event(event_id: str, record: dict) -> None:
    settings = _azure_blob_settings()
    if not settings:
        return

    cc = _get_blob_container_client()
    if cc is None:
        return

    _conn, _container, prefix = settings
    blob_name = f"{prefix}/{event_id}.json"
    blob_client = cc.get_blob_client(blob_name)

    data = json.dumps(record, ensure_ascii=False).encode("utf-8")

    try:
        blob_client.upload_blob(data, overwrite=False)
    except Exception as e:
        # Idempotency: event already stored
        if ResourceExistsError is not None and isinstance(e, ResourceExistsError):
            return
        # Fallback: ignore any other storage failure (webhook should still ACK)
        return


def extract_amount(payload: dict) -> Optional[Tuple[float, str]]:
    # Supports common PayPal event shapes
    candidates = []

    resource = payload.get("resource") or {}
    candidates.append(resource.get("amount"))
    candidates.append(payload.get("amount"))

    for cand in candidates:
        if not isinstance(cand, dict):
            continue

        currency = cand.get("currency_code") or cand.get("currency")
        value = cand.get("value")
        if currency and value is not None:
            try:
                return float(value), str(currency)
            except Exception:
                pass

        # Legacy / alternate
        currency = cand.get("currency")
        total = cand.get("total")
        if currency and total is not None:
            try:
                return float(total), str(currency)
            except Exception:
                pass

    return None


def estimate_paypal_fee(amount: float, currency: str) -> Optional[Tuple[float, float]]:
    # Optional heuristic; configure via env vars to match your account/fee schedule.
    try:
        fee_pct = float(os.getenv("EST_PAYPAL_FEE_PCT", "0"))
        fee_fixed = float(os.getenv("EST_PAYPAL_FEE_FIXED", "0"))
        fee_ccy = (os.getenv("EST_PAYPAL_FEE_CCY") or currency).upper()
    except Exception:
        return None

    if fee_pct <= 0 and fee_fixed <= 0:
        return None

    fee = amount * (fee_pct / 100.0)
    if fee_ccy == str(currency).upper():
        fee += fee_fixed

    net = amount - fee
    return fee, net


def persist_event(payload: dict) -> dict:
    record = {
        "received_at": datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        "event": payload,
    }

    event_id = _get_event_id(payload)
    record["event_id"] = event_id

    amt = extract_amount(payload)
    if amt:
        amount, currency = amt
        record["amount"] = {"value": amount, "currency": currency}
        est = estimate_paypal_fee(amount, currency)
        if est:
            fee, net = est
            record["estimated_fee"] = {"value": fee, "currency": currency}
            record["estimated_net"] = {"value": net, "currency": currency}

    _append_local_record(record)
    _store_blob_event(event_id, record)
    return record


app = FastAPI(title="Mega Ultra Roboter KI - PayPal Webhook Ingest")


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/stats")
def stats(limit: int = 500):
    # Quick MVP stats: local JSONL. If running in cloud, prefer Blob-stored events and build a proper aggregator.
    path = _local_events_path()
    if not path.exists():
        return {"events": 0, "gross": {}, "estimated_net": {}}

    gross: dict[str, float] = {}
    net: dict[str, float] = {}
    count = 0

    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        if limit > 0:
            lines = lines[-limit:]

        for line in lines:
            try:
                rec = json.loads(line)
            except Exception:
                continue

            amt = rec.get("amount") or {}
            ccy = amt.get("currency")
            val = amt.get("value")
            if ccy and val is not None:
                gross[ccy] = gross.get(ccy, 0.0) + float(val)

            n = rec.get("estimated_net") or {}
            n_ccy = n.get("currency")
            n_val = n.get("value")
            if n_ccy and n_val is not None:
                net[n_ccy] = net.get(n_ccy, 0.0) + float(n_val)

            count += 1
    except Exception:
        pass

    return {"events": count, "gross": gross, "estimated_net": net}


@app.post("/paypal/webhook")
async def paypal_webhook(
    request: Request,
    paypal_transmission_id: str | None = Header(default=None, alias="PayPal-Transmission-Id"),
    paypal_transmission_time: str | None = Header(default=None, alias="PayPal-Transmission-Time"),
    paypal_transmission_sig: str | None = Header(default=None, alias="PayPal-Transmission-Sig"),
    paypal_cert_url: str | None = Header(default=None, alias="PayPal-Cert-Url"),
    paypal_auth_algo: str | None = Header(default=None, alias="PayPal-Auth-Algo"),
):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    hdrs = {
        "paypal-transmission-id": paypal_transmission_id,
        "paypal-transmission-time": paypal_transmission_time,
        "paypal-transmission-sig": paypal_transmission_sig,
        "paypal-cert-url": paypal_cert_url,
        "paypal-auth-algo": paypal_auth_algo,
    }

    missing = [k for k, v in hdrs.items() if not v]

    if not missing:
        try:
            cfg = get_paypal_config()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Server config error: {str(e)[:300]}")

        ok = verify_webhook_signature(cfg, payload, hdrs)
        if not ok:
            raise HTTPException(status_code=401, detail="Signature verification failed")

        payload = {"_verified": True, **payload}
    else:
        # Local test mode (no PayPal headers): accept but mark unverified.
        payload = {"_verified": False, "_missing_headers": missing, **payload}

    record = persist_event(payload)
    return {"ok": True, "event_id": record.get("event_id")}


if __name__ == "__main__":
    import uvicorn

    # Azure Container Apps: bind 0.0.0.0 and honor PORT.
    port = int(os.getenv("PORT") or os.getenv("WEBHOOK_PORT") or "8503")
    host = os.getenv("WEBHOOK_HOST") or "0.0.0.0"

    uvicorn.run("webhook_server:app", host=host, port=port, reload=False)

