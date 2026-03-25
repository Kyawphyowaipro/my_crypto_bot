import ccxt
import pandas as pd
import pandas_ta as ta
import time
import os
import requests
import threading
from flask import Flask
from datetime import datetime

# --- FLASK SERVER FOR RENDER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Trading Bot is Running! 🚀"

@app.route('/health')
def health():
    return {"status": "healthy", "timestamp": str(datetime.now())}

# --- CONFIGURATION FROM ENVIRONMENT ---
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')
TG_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

PAIRS = ['SOL/USDT', 'CAKE/USDT', 'LTC/USDT', 'BNB/USDT', 'DASH/USDT']

# --- BOT LOGIC ---
def send_tg(msg):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": f"🤖 {msg}", "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def trade_logic():
    exchange = ccxt.binance({
        'apiKey': API_KEY,
        'secret': API_SECRET,
        'options': {'defaultType': 'future'}
    })
    
    send_tg("Bot started as Web Service. Monitoring active.")
    
    while True:
        try:
            # Session Check (London/NY)
            now_hour = datetime.utcnow().hour
            if not (7 <= now_hour <= 21):
                # Low activity message 
                if now_hour % 4 == 0: # ၄ နာရီတစ်ခါပဲ report ပို့မယ် (ညဘက် အနှောင့်အယှက်မဖြစ်အောင်)
                    send_tg("💤 Session closed. Bot is idling...")
                time.sleep(1800)
                continue

            for symbol in PAIRS:
                # Fetch Data
                bars = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=100)
                df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
                
                # Indicators
                df['ema21'] = ta.ema(df['close'], 21)
                df['ema55'] = ta.ema(df['close'], 55)
                df['ema100'] = ta.ema(df['close'], 100)
                df['rsi'] = ta.rsi(df['close'], 14)
                df['atr'] = ta.atr(df['high'], df['low'], df['close'], 14)
                
                last = df.iloc[-1]
                
                # Strategy: EMA Alignment + RSI
                is_bullish = last['ema21'] > last['ema55'] > last['ema100']
                is_bearish = last['ema21'] < last['ema55'] < last['ema100']
                
                if is_bullish and last['rsi'] > 55:
                    send_tg(f"📈 *BULLISH SIGNAL*: {symbol}\nPrice: {last['close']}\nATR: {last['atr']:.2f}")
                elif is_bearish and last['rsi'] < 45:
                    send_tg(f"📉 *BEARISH SIGNAL*: {symbol}\nPrice: {last['close']}\nATR: {last['atr']:.2f}")

            time.sleep(600) # ၁၀ မိနစ်တစ်ခါ check လုပ်မယ်

        except Exception as e:
            send_tg(f"⚠️ Error: {str(e)}")
            time.sleep(300)

# --- STARTUP ---
if __name__ == "__main__":
    # Trading Logic ကို Background မှာ run မယ်
    threading.Thread(target=trade_logic, daemon=True).start()
    
    # Web Server ကို Port 10000 (Render default) မှာ run မယ်
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
