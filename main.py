import os
# IMPORTANT: Numba ကို လုံးဝ အသုံးမပြုရန် ပိတ်ထားခြင်း
os.environ['PANDAS_TA_NUMBA'] = '0'

import ccxt
import pandas as pd
import pandas_ta as ta
import requests
import threading
import time
from flask import Flask
from datetime import datetime

app = Flask(__name__)

# Environment Variables
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')
TG_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

PAIRS = ['SOL/USDT', 'CAKE/USDT', 'LTC/USDT', 'BNB/USDT', 'DASH/USDT']

def send_tg(msg):
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID, 
            "text": f"🤖 *REPORT*\n{msg}", 
            "parse_mode": "Markdown"
        }
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"TG Error: {e}")

def bot_job():
    # API initialization inside thread
    exchange = ccxt.binance({
        'apiKey': API_KEY,
        'secret': API_SECRET,
        'options': {'defaultType': 'future'},
        'enableRateLimit': True
    })

    send_tg("🚀 Bot is live on Render (Numba-free version).")

    while True:
        try:
            # Session Check
            now_utc = datetime.utcnow().hour
            if not (7 <= now_utc <= 21):
                if now_utc % 4 == 0:
                    send_tg("💤 System Status: Market outside session window. Idling...")
                time.sleep(1800)
                continue

            for symbol in PAIRS:
                # Fetching 1H candles
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=105)
                df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
                
                # Indicators (Numba မလိုသော Standard Pandas Calculation)
                df['ema21'] = ta.ema(df['close'], length=21)
                df['ema55'] = ta.ema(df['close'], length=55)
                df['ema100'] = ta.ema(df['close'], length=100)
                df['rsi'] = ta.rsi(df['close'], length=14)
                df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)

                curr = df.iloc[-1]
                
                # Logic: EMA Alignment
                bullish = curr['ema21'] > curr['ema55'] > curr['ema100']
                bearish = curr['ema21'] < curr['ema55'] < curr['ema100']

                # Entry Check
                if bullish and curr['rsi'] > 55:
                    send_tg(f"⚡ *BUY SIGNAL* - {symbol}\nPrice: {curr['close']}\nStrategy: EMA Trend Follow")
                elif bearish and curr['rsi'] < 45:
                    send_tg(f"🔻 *SELL SIGNAL* - {symbol}\nPrice: {curr['close']}\nStrategy: EMA Trend Follow")

            # Hourly Pulse
            if datetime.now().minute < 10:
                send_tg(f"📊 Hourly Check: Bot is monitoring {len(PAIRS)} pairs. No errors.")

            time.sleep(600) # 10 mins interval

        except Exception as e:
            send_tg(f"⚠️ Runtime Error: `{str(e)}`")
            time.sleep(300)

@app.route('/')
def health():
    return "Bot is Active and Healthy!"

if __name__ == "__main__":
    # Background Thread for Trading
    threading.Thread(target=bot_job, daemon=True).start()
    
    # Port for Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
