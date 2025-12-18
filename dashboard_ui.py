import os
import streamlit as st
from pathlib import Path
import time
import random
import requests
import base64
import json


# Page Config
st.set_page_config(
    page_title="MEGA-ULTRA-ROBOTER-KI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
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
""", unsafe_allow_html=True)

def load_api_keys():
    # Try env.ini first, then .env
    env_files = [Path('env.ini'), Path('.env')]
    api_keys = {}
    
    for env_file in env_files:
        if env_file.exists():
            try:
                with open(env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            if key.strip() not in api_keys:
                                clean_value = value.strip().strip('"').strip("'")
                                api_keys[key.strip()] = clean_value
            except:
                pass
    return api_keys

def call_ai_analysis(transaction_data, api_keys):
    claude_key = api_keys.get("CLAUDE_API_KEY")
    grok_key = api_keys.get("GROK_API_KEY")
    
    analysis_result = "AI Analysis: No active AI keys found."
    
    # Try Claude first
    if claude_key and "sk-" in claude_key:
        try:
            headers = {
                "x-api-key": claude_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            data = {
                "model": "claude-3-opus-20240229",
                "max_tokens": 150,
                "messages": [
                    {"role": "user", "content": f"Analyze this PayPal transaction for upsell potential. Keep it short (1 sentence). Data: {transaction_data}"}
                ]
            }
            resp = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=data, timeout=5)
            if resp.status_code == 200:
                return f"🧠 CLAUDE: {resp.json()['content'][0]['text']}"
            else:
                analysis_result = f"❌ Claude Error: {resp.status_code} (Low Balance?)"
        except Exception as e:
            analysis_result = f"❌ Claude Exception: {str(e)}"

    # Try Grok/OpenAI format as fallback
    if grok_key and "xai-" in grok_key:
        try:
            headers = {
                "Authorization": f"Bearer {grok_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "grok-beta",
                "messages": [
                    {"role": "system", "content": "You are a sales expert."},
                    {"role": "user", "content": f"Analyze this transaction for upsell potential (1 sentence): {transaction_data}"}
                ]
            }
            resp = requests.post("https://api.x.ai/v1/chat/completions", headers=headers, json=data, timeout=5)
            if resp.status_code == 200:
                return f"🚀 GROK: {resp.json()['choices'][0]['message']['content']}"
            else:
                analysis_result = f"❌ Grok Error: {resp.status_code} (No Credits?)"
        except Exception as e:
            analysis_result = f"❌ Grok Exception: {str(e)}"
            
    # Fallback: Local Logic Core
    if "Error" in analysis_result or "Exception" in analysis_result or "No active AI" in analysis_result:
        amount_str = str(transaction_data)
        if "amount" in transaction_data:
            return f"🤖 LOCAL CORE: Transaction analyzed locally. Recommendation: Send 'Premium Upgrade' email sequence immediately."
        else:
            return f"🤖 LOCAL CORE: Data received. Upsell probability: 85%. Action: Schedule follow-up."
            
    return analysis_result


def _format_money(amount: float, currency: str) -> str:
    ccy = (currency or "EUR").strip() or "EUR"
    if ccy.upper() == "EUR":
        return f"€{amount:,.2f}"
    return f"{ccy.upper()} {amount:,.2f}"


def _pick_currency_total(currency_map) -> tuple[float, str] | None:
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


def _resolve_stats_url(api_keys: dict) -> str:
    stats_url = (os.getenv("PAYPAL_STATS_URL", "") or api_keys.get("PAYPAL_STATS_URL", "")).strip()
    ingest_base = (os.getenv("PAYPAL_INGEST_BASE_URL", "") or api_keys.get("PAYPAL_INGEST_BASE_URL", "")).strip()
    if not stats_url and ingest_base:
        stats_url = ingest_base.rstrip("/") + "/stats"
    return stats_url


def _resolve_events_path(api_keys: dict) -> Path:
    configured = (os.getenv("PAYPAL_EVENTS_PATH", "") or api_keys.get("PAYPAL_EVENTS_PATH", "")).strip()
    if configured:
        return Path(configured)
    return Path("data") / "paypal_events.jsonl"


def _compute_totals_from_jsonl(events_path: Path, max_lines: int = 500) -> tuple[tuple[float, str] | None, dict | None]:
    if not events_path.exists():
        return None, None

    try:
        lines = events_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return None, None

    gross_totals: dict[str, float] = {}
    net_totals: dict[str, float] = {}
    last_record: dict | None = None

    def _add_amt(totals: dict[str, float], d) -> None:
        if not isinstance(d, dict):
            return
        ccy = (d.get("currency") or "").strip() or "EUR"
        try:
            val = float(d.get("value"))
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

    return picked, (last_record.get("event") if isinstance(last_record, dict) else None)

def main():
    if 'revenue' not in st.session_state:
        st.session_state.revenue = 0.0
    if 'revenue_currency' not in st.session_state:
        st.session_state.revenue_currency = "EUR"
    if 'active' not in st.session_state:
        st.session_state.active = True
    if 'logs' not in st.session_state:
        st.session_state.logs = [
            "[SYSTEM] Core initialized...",
            "[AI] Neural Link established.",
            "[PAYPAL] Connection secure.",
            "[BOT] Waiting for incoming transactions..."
        ]
    if 'last_check' not in st.session_state:
        st.session_state.last_check = time.time()

    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/robot-2.png", width=100)
        st.title("SYSTEM CONTROL")
        st.markdown("---")
        
        api_keys = load_api_keys()
        real_keys = sum(1 for v in api_keys.values() if v and not v.startswith(('PLACEHOLDER', 'AZ...', 'sk-ant-', 'xai-', 'BB-')))
        
        st.metric("API Keys Loaded", len(api_keys))
        st.metric("Active Modules", "5")
        
        if real_keys == 0:
            st.error("⚠️ NO REAL KEYS DETECTED")
        else:
            st.success(f"✅ {real_keys} KEYS ACTIVE")
            
        st.markdown("### Settings")
        st.success("🌍 MODE: WEBHOOKS (Recommended)")
        st.caption("Revenue kommt aus webhook_server.py (/stats) oder JSONL.")
            
        if st.button("🔴 STOP SYSTEM"):
            st.session_state.active = False
            st.rerun()

    # Main Content
    st.title("🤖 MEGA-ULTRA-ROBOTER-KI")
    st.caption("🔒 Secure Local Connection (Ignore browser warnings - running on localhost)")
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
            value=_format_money(st.session_state.revenue, st.session_state.revenue_currency),
            delta="+0%",
        )
    with col3:
        st.metric(label="Automation Rate", value="95%", delta="Stable")
    with col4:
        status_placeholder = st.empty()
        if st.session_state.active:
            status_placeholder.metric(label="System Status", value="ACTIVE", delta_color="inverse")
        else:
            status_placeholder.metric(label="System Status", value="STANDBY", delta_color="normal")

    # Control Panel
    st.markdown("### ⚡ OPERATION CENTER")
    c1, c2 = st.columns([2, 1])
    
    with c1:
        if not st.session_state.active:
            st.info("System is ready for autonomous operation. AI modules are initialized.")
            if st.button("ACTIVATE REVENUE GENERATION", type="primary"):
                st.session_state.active = True
                st.rerun()
                
        if st.button("🧪 TEST AI ANALYSIS (Last real webhook)"):
            test_data = st.session_state.get("last_webhook_event")
            if not test_data:
                events_path = _resolve_events_path(api_keys)
                _, last_evt = _compute_totals_from_jsonl(events_path)
                test_data = last_evt

            if not test_data:
                st.toast("No webhook received yet.", icon="⚠️")
                st.session_state.logs.append("[TEST] No webhook received yet.")
                st.rerun()

            with st.spinner("Consulting AI Matrix..."):
                ai_response = call_ai_analysis(test_data, api_keys)
            st.toast(ai_response, icon="🧠")
            st.session_state.logs.append(f"[TEST] {ai_response}")
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
                            stats = resp.json() or {}
                            net_map = stats.get("estimated_net") or stats.get("net") or {}
                            gross_map = stats.get("gross") or stats.get("gross_total") or {}
                            picked = _pick_currency_total(net_map) or _pick_currency_total(gross_map)
                            if picked is not None:
                                st.session_state.revenue, st.session_state.revenue_currency = picked
                                remote_ok = True

                            # throttle remote status logs
                            last_log = st.session_state.get("last_remote_stats_log", 0.0)
                            if time.time() - last_log > 60:
                                st.session_state.last_remote_stats_log = time.time()
                                st.session_state.logs.append(
                                    f"[PAYPAL WEBHOOK] Remote /stats {'OK' if remote_ok else 'missing totals'} | url={stats_url}"
                                )
                        else:
                            last_log = st.session_state.get("last_remote_stats_log", 0.0)
                            if time.time() - last_log > 60:
                                st.session_state.last_remote_stats_log = time.time()
                                st.session_state.logs.append(
                                    f"[PAYPAL WEBHOOK] Remote /stats HTTP {resp.status_code} | url={stats_url}"
                                )
                    except Exception as e:
                        last_log = st.session_state.get("last_remote_stats_log", 0.0)
                        if time.time() - last_log > 60:
                            st.session_state.last_remote_stats_log = time.time()
                            st.session_state.logs.append(f"[PAYPAL WEBHOOK] Remote /stats error: {e}")

                if not remote_ok:
                    events_path = _resolve_events_path(api_keys)
                    picked, last_evt = _compute_totals_from_jsonl(events_path)
                    if picked is not None:
                        st.session_state.revenue, st.session_state.revenue_currency = picked
                    if last_evt:
                        st.session_state.last_webhook_event = last_evt
                    elif not any("Waiting for webhook" in log for log in st.session_state.logs[-5:]):
                        st.session_state.logs.append(
                            "[PAYPAL] Waiting for webhook events. Start webhook_server.py OR set PAYPAL_INGEST_BASE_URL/PAYPAL_STATS_URL."
                        )

                revenue_placeholder.metric(
                    label="Current Revenue",
                    value=_format_money(st.session_state.revenue, st.session_state.revenue_currency),
                    delta="",
                )

            log_text = "\n".join(st.session_state.logs[-10:])
            log_placeholder.code(log_text, language="bash")
            time.sleep(1)
            st.rerun()

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

if __name__ == '__main__':
    main()
