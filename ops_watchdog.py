from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Optional

import requests


@dataclass(frozen=True)
class Endpoint:
    name: str
    url: str


def _get_env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def _post_telegram(message: str) -> None:
    token = _get_env("TELEGRAM_BOT_TOKEN")
    chat_id = _get_env("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return

    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message},
            timeout=10,
        )
    except Exception:
        return


def _check_health(endpoint: Endpoint) -> tuple[bool, str]:
    try:
        resp = requests.get(endpoint.url, timeout=8)
        if resp.status_code >= 200 and resp.status_code < 400:
            return True, f"{endpoint.name} OK ({resp.status_code})"
        return False, f"{endpoint.name} BAD ({resp.status_code}): {resp.text[:200]}"
    except Exception as e:
        return False, f"{endpoint.name} DOWN: {e}"


def main() -> int:
    interval = int(_get_env("WATCHDOG_INTERVAL_SECONDS", "30") or "30")

    primary = Endpoint("B_PRIMARY", _get_env("B_PRIMARY_HEALTH_URL", "http://127.0.0.1:8503/health"))
    fallback = Endpoint("A_FALLBACK", _get_env("A_FALLBACK_HEALTH_URL", "http://127.0.0.1:8503/health"))

    last_state: dict[str, Optional[bool]] = {primary.name: None, fallback.name: None}

    while True:
        for ep in (primary, fallback):
            ok, msg = _check_health(ep)
            prev = last_state.get(ep.name)
            last_state[ep.name] = ok

            # Notify only on state change
            if prev is None:
                print(msg)
            elif prev != ok:
                print(msg)
                _post_telegram(f"[MEGA WATCHDOG] {msg}")

        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
