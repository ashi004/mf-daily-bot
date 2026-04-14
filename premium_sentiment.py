import os
import requests
import feedparser
import telebot
from dotenv import load_dotenv

load_dotenv()

# Hugging Face FinBERT API Configuration
API_URL = "https://api-inference.huggingface.co/models/ProsusAI/finbert"
headers = {"Authorization": f"Bearer {os.getenv('HF_TOKEN')}"}

def query_finbert(text):
    """Sends text to Hugging Face and returns sentiment scores."""
    try:
        response = requests.post(API_URL, headers=headers, json={"inputs": text}, timeout=10)
        # API usually returns a list of dictionaries
        return response.json()[0] 
    except Exception as e:
        print(f"AI Query Error: {e}")
        return None

def run_sentiment_engine():
    # Focused Indian Financial RSS feeds
    feeds = [
        "https://www.moneycontrol.com/rss/marketreports.xml",
        "https://www.livemint.com/rss/markets"
    ]
    
    bot = telebot.TeleBot(os.getenv("TELEGRAM_TOKEN"))
    premium_id = os.getenv("PREMIUM_CHAT_ID")
    
    found_news = False
    message = "🧠 *AI Sentiment Alert: Market Narrative*\n━━━━━━━━━━━━━━━━━━\n"

    for url in feeds:
        feed = feedparser.parse(url)
        # Check only the most recent 3 headlines to keep alerts relevant
        for entry in feed.entries[:3]:
            results = query_finbert(entry.title)
            
            if results:
                # Find the label with the highest score
                top_result = max(results, key=lambda x: x['score'])
                label = top_result['label'] # 'positive', 'negative', or 'neutral'
                score = top_result['score']
                
                # 💎 PREMIUM FILTER: Only alert on High-Conviction Bullish/Bearish news
                if score > 0.85 and label != "neutral":
                    found_news = True
                    emoji = "📈" if label == "positive" else "📉"
                    message += f"{emoji} *{label.upper()} SENTIMENT*\n"
                    message += f"📰 {entry.title}\n"
                    message += f"🎯 Confidence: {score:.2f}\n\n"

    if found_news:
        bot.send_message(premium_id, message, parse_mode="Markdown")
        print("✅ Sentiment alerts posted to Premium.")
    else:
        print("☕ No high-conviction sentiment shifts detected.")

if __name__ == "__main__":
    run_sentiment_engine()