from __future__ import annotations

from pathlib import Path

FILE = Path("dashboard_ui.py")

NEW_BLOCK = r"""
                # WEBHOOK MODE: prefer remote /stats (cloud), fallback to local JSONL
                if ingest_mode.startswith("WEBHOOKS"):
                    stats_url = os.getenv("PAYPAL_STATS_URL", "").strip()
                    ingest_base = os.getenv("PAYPAL_INGEST_BASE_URL", "").strip()
                    if not stats_url and ingest_base:
                        stats_url = ingest_base.rstrip("/") + "/stats"

                    remote_ok = False
                    if stats_url:
                        try:
                            resp = requests.get(stats_url, timeout=5)
                            if resp.status_code == 200:
                                stats = resp.json() or {}

                                def _as_amount(x):
                                    if x is None:
                                        return None
                                    if isinstance(x, (int, float)):
                                        return float(x)
                                    if isinstance(x, str):
                                        try:
                                            return float(x)
                                        except Exception:
                                            return None
                                    if isinstance(x, dict):
                                        for key in ("value", "amount", "total"):
                                            if key in x:
                                                try:
                                                    return float(x[key])
                                                except Exception:
                                                    return None
                                    return None

                                net_total = (
                                    stats.get("net_total")
                                    or stats.get("total_net")
                                    or stats.get("revenue_total")
                                    or stats.get("net")
                                )
                                gross_total = (
                                    stats.get("gross_total")
                                    or stats.get("total")
                                    or stats.get("revenue")
                                    or stats.get("gross")
                                )

                                amt = _as_amount(net_total)
                                if amt is None:
                                    amt = _as_amount(gross_total)
                                if amt is not None:
                                    st.session_state.revenue = amt
                                    remote_ok = True

                                event_count = (
                                    stats.get("events")
                                    or stats.get("event_count")
                                    or stats.get("count")
                                )

                                # Throttle log noise (once per minute)
                                last_remote_log = st.session_state.get("last_remote_stats_log", 0.0)
                                if time.time() - last_remote_log > 60:
                                    st.session_state.last_remote_stats_log = time.time()
                                    if remote_ok:
                                        st.session_state.logs.append(
                                            f"[PAYPAL WEBHOOK] Remote stats OK: {event_count or '?'} events | Total EUR {st.session_state.revenue:.2f} | url={stats_url}"
                                        )
                                    else:
                                        st.session_state.logs.append(
                                            f"[PAYPAL WEBHOOK] Remote stats missing totals | url={stats_url}"
                                        )
                            else:
                                last_remote_log = st.session_state.get("last_remote_stats_log", 0.0)
                                if time.time() - last_remote_log > 60:
                                    st.session_state.last_remote_stats_log = time.time()
                                    st.session_state.logs.append(
                                        f"[PAYPAL WEBHOOK] Remote stats HTTP {resp.status_code} | url={stats_url}"
                                    )
                        except Exception as e:
                            last_remote_log = st.session_state.get("last_remote_stats_log", 0.0)
                            if time.time() - last_remote_log > 60:
                                st.session_state.last_remote_stats_log = time.time()
                                st.session_state.logs.append(f"[PAYPAL WEBHOOK] Remote stats error: {e}")

                    if not remote_ok:
                        events_path = Path("data") / "paypal_events.jsonl"
                        if "processed_event_ids" not in st.session_state:
                            st.session_state.processed_event_ids = set()

                        if events_path.exists():
                            try:
                                lines = events_path.read_text(encoding="utf-8", errors="ignore").splitlines()
                            except Exception:
                                lines = []

                            # Process last N events only
                            for raw in lines[-50:]:
                                try:
                                    rec = json.loads(raw)
                                    evt = rec.get("event") or {}
                                except Exception:
                                    continue

                                # Prefer stable event_id from ingest server if present
                                evt_id = rec.get("event_id") or evt.get("id") or (evt.get("resource", {}) or {}).get("id")
                                if not evt_id or evt_id in st.session_state.processed_event_ids:
                                    continue
                                st.session_state.processed_event_ids.add(evt_id)

                                event_type = evt.get("event_type") or "UNKNOWN"

                                # Prefer estimated_net (if webhook ingest is configured with EST_PAYPAL_FEE_*)
                                net_amt = rec.get("estimated_net") or {}
                                gross_amt = rec.get("amount") or {}

                                def _read_amt(d):
                                    try:
                                        return float(d.get("value")), (d.get("currency") or "EUR")
                                    except Exception:
                                        return None

                                net = _read_amt(net_amt) if isinstance(net_amt, dict) else None
                                gross = _read_amt(gross_amt) if isinstance(gross_amt, dict) else None
                                if net and net[0] > 0:
                                    amount, currency = net
                                    st.session_state.revenue += amount
                                    if gross and gross[1] == currency:
                                        st.session_state.logs.append(f"[PAYPAL WEBHOOK] {event_type}: +{currency} {amount:.2f} (NET est, gross {gross[0]:.2f}) | id={evt_id}")
                                    else:
                                        st.session_state.logs.append(f"[PAYPAL WEBHOOK] {event_type}: +{currency} {amount:.2f} (NET est) | id={evt_id}")
                                elif gross and gross[0] > 0:
                                    amount, currency = gross
                                    st.session_state.revenue += amount
                                    st.session_state.logs.append(f"[PAYPAL WEBHOOK] {event_type}: +{currency} {amount:.2f} | id={evt_id}")
                                else:
                                    st.session_state.logs.append(f"[PAYPAL WEBHOOK] {event_type} received | id={evt_id}")
                        else:
                            if not any("Waiting for webhook" in log for log in st.session_state.logs[-5:]):
                                st.session_state.logs.append(
                                    "[PAYPAL] Waiting for webhook events. Start webhook_server.py locally OR set PAYPAL_INGEST_BASE_URL / PAYPAL_STATS_URL to use cloud stats." 
                                )
"""


def main() -> None:
    text = FILE.read_text(encoding="utf-8", errors="ignore")

    if "PAYPAL_STATS_URL" in text or "PAYPAL_INGEST_BASE_URL" in text:
        print("dashboard_ui.py already patched for remote /stats.")
        return

    start_marker = "                # WEBHOOK MODE: read locally ingested events\n"
    end_marker = "                # POLLING MODE: call PayPal Reporting API (requires permissions)\n"

    start_idx = text.find(start_marker)
    end_idx = text.find(end_marker)

    if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
        raise SystemExit("Could not find expected markers to patch. File may have changed.")

    new_text = text[:start_idx] + NEW_BLOCK + "\n" + text[end_idx:]
    FILE.write_text(new_text, encoding="utf-8")
    print("Patched dashboard_ui.py: added remote /stats support (PAYPAL_STATS_URL / PAYPAL_INGEST_BASE_URL).")


if __name__ == "__main__":
    main()
