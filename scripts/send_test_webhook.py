import argparse
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import requests


def _now_z() -> str:
    return datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _make_payload(
    amount: float,
    currency: str,
    event_type: str,
) -> dict[str, Any]:
    event_id = f"TEST-{int(time.time())}-{uuid.uuid4().hex[:8]}"
    return {
        "id": event_id,
        "event_type": event_type,
        "create_time": _now_z(),
        "resource": {
            "id": f"CAP-{uuid.uuid4().hex[:12].upper()}",
            "amount": {
                "currency_code": currency.upper(),
                "value": f"{amount:.2f}",
            },
            "status": "COMPLETED",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "DEV-ONLY: Send unsigned test events to webhook_server.py. "
            "For real PayPal webhooks (_verified=true), configure PayPal to "
            "call "
            "your public HTTPS /paypal/webhook."
        )
    )
    parser.add_argument(
        "--url",
        default=os.getenv("TEST_WEBHOOK_URL")
        or os.getenv("WEBHOOK_URL")
        or "http://127.0.0.1:8503/paypal/webhook",
        help=(
            "Webhook endpoint URL " "(default: http://127.0.0.1:8503/paypal/webhook)"
        ),
    )
    parser.add_argument(
        "--count", type=int, default=int(os.getenv("TEST_WEBHOOK_COUNT", "1"))
    )
    parser.add_argument(
        "--amount",
        type=float,
        default=float(os.getenv("TEST_WEBHOOK_AMOUNT", "10")),
    )
    parser.add_argument(
        "--currency",
        default=os.getenv("TEST_WEBHOOK_CCY", "EUR"),
    )
    parser.add_argument(
        "--event-type",
        default=os.getenv(
            "TEST_WEBHOOK_EVENT_TYPE",
            "PAYMENT.CAPTURE.COMPLETED",
        ),
    )
    parser.add_argument(
        "--print-every",
        type=int,
        default=int(os.getenv("TEST_WEBHOOK_PRINT_EVERY", "0")),
        help="Progress output every N events (0=auto)",
    )
    parser.add_argument(
        "--sleep-ms",
        type=int,
        default=int(os.getenv("TEST_WEBHOOK_SLEEP_MS", "0")),
        help="Optional delay between events in milliseconds",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.getenv("TEST_WEBHOOK_TIMEOUT", "8")),
        help="HTTP timeout seconds",
    )
    args = parser.parse_args()

    # NOTE: If webhook_server.py is running in strict LIVE mode (default),
    # it will reject requests without PayPal signature headers.
    # For local development only, start the server
    # with ALLOW_UNVERIFIED_WEBHOOKS=true.

    if args.count < 1:
        raise SystemExit("--count must be >= 1")

    print_every = args.print_every
    if print_every <= 0:
        if args.count <= 20:
            print_every = 1
        elif args.count <= 500:
            print_every = 25
        else:
            print_every = 100

    sleep_s = max(0, args.sleep_ms) / 1000.0

    ok = 0
    errors = 0
    session = requests.Session()
    started = time.time()

    for i in range(args.count):
        payload = _make_payload(args.amount, args.currency, args.event_type)
        try:
            resp = session.post(args.url, json=payload, timeout=args.timeout)
            if resp.status_code // 100 == 2:
                ok += 1
            else:
                errors += 1

            if (i + 1) % print_every == 0 or (i + 1) == args.count:
                elapsed = max(0.001, time.time() - started)
                rps = (i + 1) / elapsed
                print(
                    (
                        f"[{i+1}/{args.count}] ok={ok} errors={errors} "
                        f"last_http={resp.status_code} rps={rps:.1f}"
                    )
                )
        except Exception as e:
            errors += 1
            if (i + 1) % print_every == 0 or (i + 1) == args.count:
                elapsed = max(0.001, time.time() - started)
                rps = (i + 1) / elapsed
                print(
                    (
                        f"[{i+1}/{args.count}] ok={ok} errors={errors} "
                        f"last_error={e} rps={rps:.1f}"
                    )
                )

        if sleep_s:
            time.sleep(sleep_s)

    total_s = max(0.001, time.time() - started)
    print(
        (
            f"done: sent={args.count} ok={ok} errors={errors} "
            f"url={args.url} seconds={total_s:.2f}"
        )
    )
    return 0 if errors == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
