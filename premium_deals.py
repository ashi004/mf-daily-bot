import os
import pandas as pd
import telebot
from NseKit import get
from nselib import capital_market
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()

def run_whale_watch():
    bot = telebot.TeleBot(os.getenv("TELEGRAM_TOKEN"))
    premium_id = os.getenv("PREMIUM_CHAT_ID")
    
    try:
        # 1. FETCH DATA
        print("Fetching Bulk Deals...")
        bulk_df = get.bulk_deals()
        
        print("Fetching Insider Trading...")
        insider_df = capital_market.insider_trading_data(period='1D')
        
        # 2. CREATE EXCEL FILE
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            if not bulk_df.empty:
                bulk_df.to_excel(writer, sheet_name='Bulk_Deals', index=False)
            if not insider_df.empty:
                insider_df.to_excel(writer, sheet_name='Insider_Trading', index=False)
        output.seek(0)

        # 3. CONSTRUCT SUMMARY MESSAGE
        message = "🐋 *PREMIUM: Daily Whale Watch Report*\n━━━━━━━━━━━━━━━━━━\n"
        
        # Add Promoter Highlights
        if not insider_df.empty:
            p_buys = insider_df[(insider_df['PERSON_CATEGORY'] == 'Promoters') & 
                                (insider_df['ACQUISITION_MODE'] == 'Market Purchase')].head(5)
            if not p_buys.empty:
                message += "🔑 *Promoter Market Buys:*\n"
                for _, row in p_buys.iterrows():
                    message += f"• *{row['SYMBOL']}*: {row['NO_REGSPEC_VAL']} shares\n"
                message += "\n"

        # Add Bulk Deal Highlights
        if not bulk_df.empty:
            b_buys = bulk_df[bulk_df['Buy / Sell'] == 'BUY'].head(5)
            if not b_buys.empty:
                message += "🏛️ *Top Institutional Buys:*\n"
                for _, row in b_buys.iterrows():
                    message += f"• *{row['Symbol']}*: {row['Quantity Traded']} shares\n"
                message += "\n"

        message += "📑 *Full Data Attached:* Open the Excel file for the 100% complete list of today's trades."

        # 4. SEND TO TELEGRAM
        bot.send_message(premium_id, message, parse_mode="Markdown")
        bot.send_document(
            premium_id, 
            document=('NSE_Whale_Report.xlsx', output),
            caption="📊 Nivesh Niti Premium: Bulk & Insider Data"
        )
        print("✅ Report sent successfully!")

    except Exception as e:
        print(f"❌ Error during execution: {e}")

if __name__ == "__main__":
    run_whale_watch()