"""
premium_sentiment.py
---------------------
Scans top Indian financial RSS headlines through FinBERT (Hugging Face).
Posts HIGH-CONVICTION bullish/bearish alerts to the premium Telegram channel.
"""

import os
import time
import requests
import feedparser
import telebot
from dotenv import load_dotenv

load_dotenv()

# ─── CONFIG ───────────────────────────────────────────────────────────────────

FINBERT_URL = "https://api-inference.huggingface.co/models/ProsusAI/finbert"
CONVICTION_THRESHOLD = 0.82   # Lowered slightly from 0.85 to catch more alerts

RSS_FEEDS = [
    "https://www.moneycontrol.com/rss/marketreports.xml",
    "https://www.livemint.com/rss/markets",
    "https://economictimes.indiatimes.com/markets/rss.cms",
    "https://www.business-standard.com/rss/markets-106.rss",
]

LABEL_EMOJI = {
    "positive": "📈",
    "negative": "📉",
    "neutral":  "⚪",
}


# ─── FINBERT ──────────────────────────────────────────────────────────────────

def query_finbert(text: str, hf_token: str):
    """
    Posts text to HuggingFace FinBERT inference API.
    Returns a list of {label, score} dicts, or None on failure.
    """
    headers = {"Authorization": f"Bearer {hf_token}"}
    try:
        resp = requests.post(
            FINBERT_URL,
            headers=headers,
            json={"inputs": text},
            timeout=15,
        )
        # HF returns [[{label, score}, ...]] — take the first element
        result = resp.json()
        if isinstance(result, list) and len(result) > 0:
            inner = result[0]
            if isinstance(inner, list):
                return inner          # [[{...}]] format
            return result             # [{...}] format
        return None
    except Exception as e:
        print(f"FinBERT error: {e}")
        return None


# ─── DEDUPLICATION ────────────────────────────────────────────────────────────

def _seen_titles() -> set:
    """Simple in-memory dedup for one run."""
    return set()


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def run_sentiment_engine():
    token      = os.getenv("TELEGRAM_TOKEN")
    premium_id = os.getenv("PREMIUM_CHAT_ID")
    hf_token   = os.getenv("HF_TOKEN")

    if not token or not premium_id:
        print("❌ TELEGRAM_TOKEN or PREMIUM_CHAT_ID missing.")
        return
    if not hf_token:
        print("❌ HF_TOKEN missing — cannot run FinBERT sentiment.")
        return

    bot = telebot.TeleBot(token)

    seen      = _seen_titles()
    alerts    = []
    checked   = 0

    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            entries = feed.entries[:5]   # top 5 from each feed
        except Exception as e:
            print(f"RSS parse error ({feed_url}): {e}")
            continue

        for entry in entries:
            title = entry.get("title", "").strip()
            if not title or title in seen:
                continue
            seen.add(title)
            checked += 1

            results = query_finbert(title, hf_token)
            if not results:
                continue

            top = max(results, key=lambda x: x.get("score", 0))
            label = top.get("label", "neutral").lower()
            score = top.get("score", 0.0)

            print(f"[{label.upper()} {score:.2f}] {title}")

            if score >= CONVICTION_THRESHOLD and label != "neutral":
                alerts.append({
                    "title":  title,
                    "label":  label,
                    "score":  score,
                    "source": feed.feed.get("title", "News"),
                    "link":   entry.get("link", ""),
                })

            time.sleep(0.3)   # be polite to HF API

    print(f"Checked {checked} headlines, found {len(alerts)} high-conviction alerts.")

    if not alerts:
        print("☕ No high-conviction sentiment shifts detected. No message sent.")
        return

    # Sort: most confident first
    alerts.sort(key=lambda x: x["score"], reverse=True)

    message = "🧠 *AI Sentiment Alert: Market Narrative*\n━━━━━━━━━━━━━━━━━━\n\n"

    for a in alerts[:8]:   # cap at 8 alerts per message
        emoji = LABEL_EMOJI.get(a["label"], "⚪")
        message += (
            f"{emoji} *{a['label'].upper()} — {a['score']:.0%} confidence*\n"
            f"📰 {a['title']}\n"
            f"🔗 [Read more]({a['link']})\n\n"
        )

    message += f"_Scanned {checked} headlines from {len(RSS_FEEDS)} sources._"

    bot.send_message(premium_id, message, parse_mode="Markdown", disable_web_page_preview=True)
    print("✅ Sentiment alerts posted to premium channel.")


if __name__ == "__main__":
    run_sentiment_engine()
