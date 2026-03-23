import ccxt, pandas_ta as ta, pandas as pd, time, os
from flask import Flask
from threading import Thread

# Web Server လေး တစ်ခု ဆောက်ထားမယ် (Render မအိပ်အောင်လို့ပါ)
app = Flask('')
@app.route('/')
def home(): return "Bot is running!"

def run_web(): app.run(host='0.0.0.0', port=8080)

# Bot ရဲ့ ပင်မအလုပ်
def trade_logic():
    exchange = ccxt.binance({'apiKey': 'L48AM3ytdBa3QUfW9qeLZj5X9xTJK8GKB0Vc9fR4ml2Eo8QNRcjNdKIsiz6EWj8F', 'secret': 'EESYNU9Y4vwjHomIcGxglc25cvTpHU9jom88E2shCMW6q4xQyRCS833sBr26FORT', 'enableRateLimit': True, 'options': {'defaultType': 'future'}})
    exchange.set_sandbox_mode(True)
    symbol = 'SOL/USDT'
    
    while True:
        try:
            bars = exchange.fetch_ohlcv(symbol, timeframe='5m', limit=100)
            df = pd.DataFrame(bars, columns=['t', 'o', 'h', 'l', 'c', 'v'])
            df['RSI'] = ta.rsi(df['c'], length=14)
            rsi = df['RSI'].iloc[-1]
            print(f"Checking RSI: {rsi:.2f}")
            
            if rsi < 30: exchange.create_market_buy_order(symbol, 0.1)
            elif rsi > 70: exchange.create_market_sell_order(symbol, 0.1)
            
            time.sleep(300) # ၅ မိနစ် တစ်ခါ စစ်မယ်
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(60)

# Bot နဲ့ Web Server ကို ပြိုင်တူ Run မယ်
if __name__ == "__main__":
    Thread(target=run_web).start()
    trade_logic()
