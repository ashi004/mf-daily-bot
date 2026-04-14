import os
import telebot
from NseKit import get
from google import genai
from dotenv import load_dotenv

load_dotenv()

def get_premium_insight(client, symbol, buyer, qty):
    prompt = f"In the Indian market, {buyer} bought {qty} shares of {symbol}. Write a 1-sentence professional insight into why an institution would buy this. Be punchy. Format: 'Insight - Research Desk'"
    try:
        response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        return response.text.strip()
    except:
        return "Institutional accumulation detected. - Research Desk"

def run_premium_scan():
    # Fetch today's Bulk Deals
    df = get.bulk_deals()
    if df.empty:
        return

    # Filter for top 3 BUY deals
    buys = df[df['Buy / Sell'] == 'BUY'].head(3) 

    bot = telebot.TeleBot(os.getenv("TELEGRAM_TOKEN"))
    premium_id = os.getenv("PREMIUM_CHAT_ID")
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    message = "💎 *PREMIUM: Smart Money Flow*\n━━━━━━━━━━━━━━━━━━\n"
    
    for _, row in buys.iterrows():
        insight = get_premium_insight(client, row['Symbol'], row['Client Name'], row['Quantity Traded'])
        message += f"🚀 *{row['Symbol']}*\n"
        message += f"👤 *Buyer:* {row['Client Name']}\n"
        message += f"📦 *Qty:* {row['Quantity Traded']}\n"
        message += f"💡 _{insight}_\n\n"

    bot.send_message(premium_id, message, parse_mode="Markdown")

if __name__ == "__main__":
    run_premium_scan()