import os
import asyncio
import pandas as pd
import telebot
from deriv_api import DerivAPI
from flask import Flask
from threading import Thread

# --- SERVEUR POUR RENDER ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Alive"

def run_web():
    # Render utilise un port dynamique
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# --- TA CONFIGURATION ---
TOKEN_TG = "TON_TOKEN_TELEGRAM"
ID_CHAT = "TON_CHAT_ID"
TOKEN_DERIV = "TON_TOKEN_DERIV"

bot = telebot.TeleBot(TOKEN_TG)

async def start_trading():
    api = DerivAPI(app_id=1089)
    await api.authorize(TOKEN_DERIV)
    bot.send_message(ID_CHAT, "🚀 Bot Step Index en ligne sur Render !")

    last_ts = None
    while True:
        try:
            r = await api.ticks_history({'ticks_history': 'stpY', 'count': 300, 'style': 'candles', 'granularity': 300})
            df = pd.DataFrame(r['candles'])
            df['close'] = df['close'].astype(float)
            
            # MM200 et RSI (Calcul simplifié)
            ema = df['close'].ewm(span=200).mean().iloc[-1]
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rsi = 100 - (100 / (1 + (gain / loss))).iloc[-1]
            
            p, ts = df['close'].iloc[-1], df['epoch'].iloc[-1]

            if ts != last_ts:
                # ACHAT
                if p > ema and rsi >= 30 and rsi < 35:
                    bot.send_message(ID_CHAT, f"🔵 ACHAT STEP\nPrix: {p}\nTP1: {p+4}")
                # VENTE
                elif p < ema and rsi <= 70 and rsi > 65:
                    bot.send_message(ID_CHAT, f"🔴 VENTE STEP\nPrix: {p}\nTP1: {p-4}")
                last_ts = ts
        except Exception as e: print(f"Erreur: {e}")
        await asyncio.sleep(20)

if __name__ == "__main__":
    Thread(target=run_web).start() # Lance le serveur web
    asyncio.run(start_trading())   # Lance le bot
