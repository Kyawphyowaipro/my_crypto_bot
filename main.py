import ccxt, pandas as pd, time
from stockstats import StockDataFrame
from flask import Flask
from threading import Thread
import os

app = Flask('')
@app.route('/')
def home(): return "Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def trade_logic():
    # API Key များ ထည့်သွင်းခြင်း
    exchange = ccxt.binance({
        'apiKey': 'L48AM3ytdBa3QUfW9qeLZj5X9xTJK8GKB0Vc9fR4ml2Eo8QNRcjNdKIsiz6EWj8F',
        'secret': 'EESYNU9Y4vwjHomIcGxglc25cvTpHU9jom88E2shCMW6q4xQyRCS833sBr26FORT',
        'enableRateLimit': True,
        'options': {'defaultType': 'future'}
    })
    exchange.set_sandbox_mode(True)
    symbol = 'SOL/USDT'
    
    print("Bot started monitoring...")
    
    while True:
        try:
            bars = exchange.fetch_ohlcv(symbol, timeframe='5m', limit=100)
            df = pd.DataFrame(bars, columns=['open_time', 'open', 'high', 'low', 'close', 'volume'])
            stock = StockDataFrame.retype(df)
            # RSI တွက်ခြင်း
            rsi = stock['rsi_14'].iloc[-1]
            
            print(f"Current RSI: {rsi:.2f}")
            
            # အရောင်းအဝယ် ဗျူဟာ
            if rsi < 30:
                print("Signal: BUY 0.1 SOL")
                exchange.create_market_buy_order(symbol, 0.1)
            elif rsi > 70:
                print("Signal: SELL 0.1 SOL")
                exchange.create_market_sell_order(symbol, 0.1)
                
            time.sleep(300) # ၅ မိနစ် တစ်ခါ စစ်မည်
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    # Web server ကို အရင်ပွင့်အောင် လုပ်မည် (Port error ကင်းဝေးစေရန်)
    Thread(target=run_web).start()
    trade_logic()
