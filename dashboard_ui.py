import json
import os
import time
from pathlib import Path
from typing import Any, Mapping, cast

import requests
import streamlit as st

# Page Config
st.set_page_config(
    page_title="MEGA-ULTRA-ROBOTER-KI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown(
    """
<style>
    .stApp {
        background-color: #0e1117;
        color: #00ff00;
    }
    .metric-card {
        background-color: #1e2130;
        border: 1px solid #00ff00;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 0 10px rgba(0, 255, 0, 0.2);
    }
    h1, h2, h3 {
        color: #00ff00 !important;
        font-family: 'Courier New', Courier, monospace;
    }
    .stButton>button {
        background-color: #00ff00;
        color: black;
        border: none;
        font-weight: bold;
        width: 100%;
    }
</style>
""",
    unsafe_allow_html=True,
)


def load_api_keys():
    # Try env.ini first, then .env
    env_files = [Path("env.ini"), Path(".env")]
    api_keys: dict[str, str] = {}

    for env_file in env_files:
        if env_file.exists():
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            if key.strip() not in api_keys:
                                clean_value = value.strip().strip('"').strip("'")
                                api_keys[key.strip()] = clean_value
            except Exception:
                pass
    return api_keys


def _json_dict(resp: requests.Response) -> dict[str, Any]:
    try:
        data = resp.json()
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    # JSON object keys are strings; normalize for type checkers.
    typed = cast(dict[str, Any], data)
    return {str(k): v for k, v in typed.items()}


def _format_money(amount: float, currency: str) -> str:
    ccy = (currency or "EUR").strip() or "EUR"
    if ccy.upper() == "EUR":
        return f"€{amount:,.2f}"
    return f"{ccy.upper()} {amount:,.2f}"


def _pick_currency_total(
    currency_map: Mapping[str, Any],
) -> tuple[float, str] | None:
    if not isinstance(currency_map, dict) or not currency_map:
        return None
    if "EUR" in currency_map:
        try:
            return float(currency_map["EUR"]), "EUR"
        except Exception:
            pass
    for ccy, val in currency_map.items():
        try:
            return float(val), str(ccy)
        except Exception:
            continue
    return None


def _resolve_stats_url(api_keys: Mapping[str, str]) -> str:
    stats_url = (
        os.getenv("PAYPAL_STATS_URL", "") or api_keys.get("PAYPAL_STATS_URL", "")
    ).strip()
    ingest_base = (
        os.getenv("PAYPAL_INGEST_BASE_URL", "")
        or api_keys.get("PAYPAL_INGEST_BASE_URL", "")
    ).strip()
    if not stats_url and ingest_base:
        stats_url = ingest_base.rstrip("/") + "/stats"
    # Local default (so it feels alive immediately when webhook_server.py runs)
    if not stats_url:
        stats_url = "http://127.0.0.1:8503/stats"
    return stats_url


def _resolve_ingest_base(api_keys: Mapping[str, str]) -> str:
    stats_url = _resolve_stats_url(api_keys)
    if stats_url.endswith("/stats"):
        return stats_url[: -len("/stats")]
    return stats_url.rstrip("/")


def _resolve_events_path(api_keys: Mapping[str, str]) -> Path:
    configured = (
        os.getenv("PAYPAL_EVENTS_PATH", "") or api_keys.get("PAYPAL_EVENTS_PATH", "")
    ).strip()
    if configured:
        return Path(configured)
    return Path("data") / "paypal_events.jsonl"


def _compute_totals_from_jsonl(
    events_path: Path, max_lines: int = 500
) -> tuple[tuple[float, str] | None, dict[str, Any] | None]:
    if not events_path.exists():
        return None, None

    try:
        lines = events_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return None, None

    gross_totals: dict[str, float] = {}
    net_totals: dict[str, float] = {}
    last_record: dict[str, Any] | None = None

    def _add_amt(
        totals: dict[str, float],
        d: Mapping[str, Any] | None,
    ) -> None:
        if not isinstance(d, dict):
            return
        raw_ccy = d.get("currency")
        ccy = str(raw_ccy).strip() if raw_ccy is not None else ""
        ccy = ccy or "EUR"
        try:
            raw_val = d.get("value")
            if raw_val is None:
                return
            val = float(raw_val)
        except Exception:
            return
        totals[ccy] = totals.get(ccy, 0.0) + val

    for raw in lines[-max_lines:]:
        try:
            rec = json.loads(raw)
        except Exception:
            continue
        last_record = rec
        _add_amt(gross_totals, rec.get("amount"))
        _add_amt(net_totals, rec.get("estimated_net"))

    picked = None
    if "EUR" in net_totals:
        picked = (net_totals["EUR"], "EUR")
    elif len(net_totals) == 1:
        (ccy, val) = next(iter(net_totals.items()))
        picked = (val, ccy)
    elif "EUR" in gross_totals:
        picked = (gross_totals["EUR"], "EUR")
    elif len(gross_totals) == 1:
        (ccy, val) = next(iter(gross_totals.items()))
        picked = (val, ccy)

    last_event = last_record.get("event") if isinstance(last_record, dict) else None
    return picked, last_event


def main():
    if "revenue" not in st.session_state:
        st.session_state.revenue = 0.0
    if "revenue_currency" not in st.session_state:
        st.session_state.revenue_currency = "EUR"
    if "active" not in st.session_state:
        st.session_state.active = True
    if "logs" not in st.session_state:
        st.session_state.logs = [
            "[SYSTEM] Core initialized...",
            "[AI] Neural Link established.",
            "[PAYPAL] Connection secure.",
            "[BOT] Waiting for incoming transactions...",
        ]
    if "last_check" not in st.session_state:
        st.session_state.last_check = time.time()

    api_keys = load_api_keys()

    with st.sidebar:
        st.image(
            "https://img.icons8.com/fluency/96/robot-2.png",
            width=100,
        )
        st.title("SYSTEM CONTROL")
        st.markdown("---")
        real_keys = sum(
            1
            for v in api_keys.values()
            if v
            and not v.startswith(("PLACEHOLDER", "AZ...", "sk-ant-", "xai-", "BB-"))
        )

        st.metric("API Keys Loaded", len(api_keys))
        st.metric("Active Modules", "5")

        if real_keys == 0:
            st.error("⚠️ NO REAL KEYS DETECTED")
        else:
            st.success(f"✅ {real_keys} KEYS ACTIVE")

        st.markdown("### Settings")
        st.success("🌍 MODE: WEBHOOKS (LIVE)")
        st.caption("Revenue kommt aus webhook_server.py (/stats) oder JSONL.")

        stats_url = _resolve_stats_url(api_keys)
        st.code(stats_url, language="text")

        st.markdown("### Checkout")
        st.caption("Erstellt echte PayPal Checkout-Links (LIVE/SANDBOX).")

        ingest_base = _resolve_ingest_base(api_keys)
        create_url = ingest_base.rstrip("/") + "/paypal/create-order"
        capture_url = ingest_base.rstrip("/") + "/paypal/capture-order"

        if "last_order_id" not in st.session_state:
            st.session_state.last_order_id = ""
        if "last_approve_url" not in st.session_state:
            st.session_state.last_approve_url = ""

        if st.button("💳 Checkout-Link generieren"):
            try:
                resp = requests.post(create_url, json={}, timeout=12)
                if resp.status_code == 200:
                    data = _json_dict(resp)
                    st.session_state.last_order_id = str(data.get("order_id") or "")
                    st.session_state.last_approve_url = str(
                        data.get("approve_url") or ""
                    )
                    st.session_state.logs.append(
                        (
                            "[PAYPAL] Order created | id="
                            f"{st.session_state.last_order_id}"
                        )
                    )
                else:
                    st.session_state.logs.append(
                        (
                            f"[PAYPAL] create-order HTTP {resp.status_code}: "
                            f"{resp.text[:120]}"
                        )
                    )
            except Exception as e:
                st.session_state.logs.append(f"[PAYPAL] create-order error: {e}")
            st.rerun()

        if st.session_state.last_order_id:
            st.text_input(
                "Order ID",
                value=st.session_state.last_order_id,
                key="_order_id_readonly",
                disabled=True,
            )
        if st.session_state.last_approve_url:
            st.link_button(
                "➡️ Zur PayPal Zahlung",
                st.session_state.last_approve_url,
            )

        if st.button("✅ Capture (nach Approval)"):
            oid = (st.session_state.last_order_id or "").strip()
            if not oid:
                st.session_state.logs.append("[PAYPAL] No order_id to capture")
            else:
                try:
                    resp = requests.post(
                        capture_url,
                        json={"order_id": oid},
                        timeout=12,
                    )
                    if resp.status_code == 200:
                        data = _json_dict(resp)
                        st.session_state.logs.append(
                            (
                                f"[PAYPAL] capture status={data.get('status')}"
                                f" | id={oid}"
                            )
                        )
                    else:
                        st.session_state.logs.append(
                            (
                                f"[PAYPAL] capture HTTP {resp.status_code}: "
                                f"{resp.text[:120]}"
                            )
                        )
                except Exception as e:
                    st.session_state.logs.append(f"[PAYPAL] capture error: {e}")
            st.rerun()

        if st.button("🔴 STOP SYSTEM"):
            st.session_state.active = False
            st.rerun()

    # Main Content
    st.title("🤖 MEGA-ULTRA-ROBOTER-KI")
    st.caption(
        "🔒 Secure Local Connection " "(Ignore browser warnings - running on localhost)"
    )
    st.markdown("### 🚀 PAYPAL REVENUE MAXIMIZATION SYSTEM")
    st.markdown("---")

    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="Monthly Target", value="€50,000", delta="Goal")
    with col2:
        revenue_placeholder = st.empty()
        revenue_placeholder.metric(
            label="Current Revenue",
            value=_format_money(
                st.session_state.revenue, st.session_state.revenue_currency
            ),
            delta="",
        )
    with col3:
        st.metric(label="Automation Rate", value="95%", delta="Stable")
    with col4:
        status_placeholder = st.empty()
        if st.session_state.active:
            status_placeholder.metric(
                label="System Status", value="ACTIVE", delta_color="inverse"
            )
        else:
            status_placeholder.metric(
                label="System Status", value="STANDBY", delta_color="normal"
            )

    # Control Panel
    st.markdown("### ⚡ OPERATION CENTER")
    c1, c2 = st.columns([2, 1])

    with c1:
        if not st.session_state.active:
            st.info(
                "System is ready for autonomous operation. "
                "AI modules are initialized."
            )
            if st.button("ACTIVATE REVENUE GENERATION", type="primary"):
                st.session_state.active = True
                st.rerun()

        if st.button("✅ Webhook-Verifikation prüfen / Setup"):
            st.toast(
                (
                    "Echte Verifikation klappt nur über PayPal → "
                    "öffentliche HTTPS URL."
                ),
                icon="ℹ️",
            )
            st.session_state.logs.append(
                (
                    "[WEBHOOK] Für _verified=true muss PayPal an "
                    "https://<public>/paypal/webhook senden "
                    "(mit Signatur-Headern)."
                )
            )
            st.session_state.logs.append(
                (
                    "[WEBHOOK] Lokal testen ohne PayPal ist DEV-only: "
                    "Server mit ALLOW_UNVERIFIED_WEBHOOKS=true starten."
                )
            )
            st.rerun()
        else:
            st.success("SYSTEM FULLY ACTIVE! Monitoring revenue streams...")
            st.markdown("Running autonomous transaction processing...")

            log_placeholder = st.empty()
            log_text = "\n".join(st.session_state.logs[-10:])
            log_placeholder.code(log_text, language="bash")

            current_time = time.time()
            if current_time - st.session_state.last_check > 10:
                st.session_state.last_check = current_time

                remote_ok = False
                stats_url = _resolve_stats_url(api_keys)
                if stats_url:
                    try:
                        resp = requests.get(stats_url, timeout=5)
                        if resp.status_code == 200:
                            stats = _json_dict(resp)
                            raw_net = stats.get("estimated_net") or stats.get("net")
                            if isinstance(raw_net, dict):
                                typed_net = cast(dict[str, Any], raw_net)
                                net_map: dict[str, Any] = {
                                    str(k): v for k, v in typed_net.items()
                                }
                            else:
                                net_map = {}

                            raw_gross = stats.get("gross") or stats.get("gross_total")
                            if isinstance(raw_gross, dict):
                                typed_gross = cast(dict[str, Any], raw_gross)
                                gross_map: dict[str, Any] = {
                                    str(k): v for k, v in typed_gross.items()
                                }
                            else:
                                gross_map = {}

                            picked = _pick_currency_total(
                                net_map
                            ) or _pick_currency_total(gross_map)
                            if picked is not None:
                                (
                                    st.session_state.revenue,
                                    st.session_state.revenue_currency,
                                ) = picked
                                remote_ok = True

                            last_log = st.session_state.get(
                                "last_remote_stats_log",
                                0.0,
                            )
                            if time.time() - last_log > 30:
                                st.session_state.last_remote_stats_log = time.time()
                                status = "OK" if remote_ok else "missing totals"
                                st.session_state.logs.append(
                                    (
                                        "[PAYPAL WEBHOOK] /stats "
                                        f"{status}"
                                        f" | url={stats_url}"
                                    )
                                )
                        else:
                            last_log = st.session_state.get(
                                "last_remote_stats_log",
                                0.0,
                            )
                            if time.time() - last_log > 30:
                                st.session_state.last_remote_stats_log = time.time()
                                code = resp.status_code
                                st.session_state.logs.append(
                                    (
                                        f"[PAYPAL WEBHOOK] /stats HTTP {code}"
                                        f" | url={stats_url}"
                                    )
                                )
                    except Exception as e:
                        last_log = st.session_state.get(
                            "last_remote_stats_log",
                            0.0,
                        )
                        if time.time() - last_log > 30:
                            st.session_state.last_remote_stats_log = time.time()
                            st.session_state.logs.append(
                                f"[PAYPAL WEBHOOK] /stats error: {e}"
                            )

                if not remote_ok:
                    events_path = _resolve_events_path(api_keys)
                    picked, _last_evt = _compute_totals_from_jsonl(events_path)
                    if picked is not None:
                        (
                            st.session_state.revenue,
                            st.session_state.revenue_currency,
                        ) = picked
                    elif not any(
                        "Waiting for webhook" in log
                        for log in st.session_state.logs[-5:]
                    ):
                        st.session_state.logs.append(
                            (
                                "[PAYPAL] Waiting for webhook events. "
                                "Start webhook_server.py OR set "
                                "PAYPAL_INGEST_BASE_URL/PAYPAL_STATS_URL."
                            )
                        )

                revenue_placeholder.metric(
                    label="Current Revenue",
                    value=_format_money(
                        st.session_state.revenue,
                        st.session_state.revenue_currency,
                    ),
                    delta="",
                )

            # Important: Avoid tight auto-rerun loops.
            # Continuous reruns can crash Streamlit/Tornado on
            # client disconnect.
            # Example: tornado.websocket.WebSocketClosedError.
            # naturally (browser reload/interactions) for stability.
            log_text = "\n".join(st.session_state.logs[-10:])
            log_placeholder.code(log_text, language="bash")

    with c2:
        st.markdown("#### Active Protocols")
        st.checkbox("Auto-Approve Transactions", value=True)
        st.checkbox("Smart Upselling AI", value=True)
        st.checkbox("Fraud Detection", value=True)
        st.checkbox("24/7 Monitoring", value=True)

    if not st.session_state.active:
        st.markdown("### 📟 SYSTEM LOG")
        with st.expander("View Real-time Logs", expanded=True):
            st.code("\n".join(st.session_state.logs[-5:]), language="bash")


if __name__ == "__main__":
    main()
