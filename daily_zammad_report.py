#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo  # Python 3.9+

ZAMMAD_URL   = os.getenv("ZAMMAD_URL", "").rstrip("/")
ZAMMAD_TOKEN = os.getenv("ZAMMAD_TOKEN", "")
BOT_TOKEN     = os.getenv("BOT_TOKEN", "")
CHAT_ID   = os.getenv("CHAT_ID", "")
TIMEZONE     = os.getenv("TIMEZONE", "Asia/Tashkent")  # change if needed

# What you count as "active" tickets. Default = state:open.
# You can expand this to include multiple states, e.g. "(new OR open OR \"pending reminder\" OR escalated)".
ACTIVE_QUERY = os.getenv("ACTIVE_QUERY", "(state_id:1 OR state_id:2 OR state_id:3 OR state_id:6)")
HEADERS = {"Authorization": f"Token token={ZAMMAD_TOKEN}"}
SEARCH  = "/api/v1/tickets/search"

def must_env(name, value):
    if not value:
        print(f"Missing required env var: {name}", file=sys.stderr)
        sys.exit(2)

for n, v in [("ZAMMAD_URL", ZAMMAD_URL), ("ZAMMAD_TOKEN", ZAMMAD_TOKEN),
             ("BOT_TOKEN", BOT_TOKEN), ("CHAT_ID", CHAT_ID)]:
    must_env(n, v)

def zammad_count(query: str) -> int:
    """Return only the total_count from Zammad search."""
    url = f"{ZAMMAD_URL}{SEARCH}"
    r = requests.get(url, headers=HEADERS,
                     params={"query": query, "only_total_count": "true"},
                     timeout=30)
    r.raise_for_status()
    return int(r.json().get("total_count", 0))

def build_report() -> str:
    tz = ZoneInfo(TIMEZONE)
    now = datetime.now(tz)
    today_00 = now.replace(hour=0, minute=0, second=0, microsecond=0)
    iso_from = today_00.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")

    all_tickets = zammad_count("*")
    todays_tickets = zammad_count(f"created_at:>={iso_from}")
    active_tickets = zammad_count(ACTIVE_QUERY)
    closed_today = zammad_count(f"state_id:4 AND close_at:>={iso_from}")

    # Format time like your example: 11/08/2025, 20:02:01
    stamp = now.strftime("%d/%m/%Y, %H:%M:%S")

    text = (
        "📊Ежедневный отчет:\n\n"
        f"📆Дата отчета: {stamp}\n\n"
        f"🗃️Всего тикетов: {all_tickets}\n\n"
        f"🗂️Сегодняшние тикеты: {todays_tickets}\n\n"
        f"🟠Активные тикеты: {active_tickets}\n\n"
        f"✅Закрытые тикеты: {closed_today}"
    )
    return text

def send_to_telegram(text: str) -> None:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    r = requests.post(url, json={
        "chat_id": CHAT_ID,
        "text": text,
        "disable_web_page_preview": True
    }, timeout=30)
    r.raise_for_status()

def main():
    try:
        send_to_telegram(build_report())
    except Exception as e:
        # Send error to Telegram too, so you see failures.
        try:
            send_to_telegram(f"⚠️ Zammad report failed: {e}")
        except Exception:
            pass
        raise

if __name__ == "__main__":
    main()
