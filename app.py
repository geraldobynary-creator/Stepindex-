import os
import asyncio
import pandas as pd
import telebot
from telebot import types
from deriv_api import DerivAPI
from flask import Flask
from threading import Thread

app = Flask('')
@app.route('/')
def home(): return "Bot Step Index Intelligence Visuelle"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# --- CONFIG ---
TOKEN_TG = "8796066471:AAEb97AFAnubWlnb7ATwX87wrnOIYztzdXA"
ID_CHAT = "7893239258"
TOKEN_DERIV = "IWDrM4XskBkVkRx"

bot = telebot.TeleBot(TOKEN_TG)
current_tf = "5m"
tf_seconds = {"5m": 300, "15m": 900, "30m": 1800}

def analyze_patterns(current, previous):
    """Analyse complète des bougies de retournement pour le Step Index"""
    # Mesures de base
    c_open, c_close, c_high, c_low = current['open'], current['close'], current['high'], current['low']
    p_open, p_close = previous['open'], previous['close']
    
    body = abs(c_close - c_open)
    upper_wick = c_high - max(c_open, c_close)
    lower_wick = c_min = min(c_open, c_close) - c_low
    full_range = c_high - c_low
    
    if full_range == 0: return None

    # 1. ENGLOBANTE (Engulfing) - Très fort sur Step Index
    if c_close > c_open and p_close < p_open and c_close > p_open and c_open < p_close:
        return "ENGLOBANTE HAUSSIÈRE 📈"
    if c_close < c_open and p_close > p_open and c_close < p_open and c_open > p_close:
        return "ENGLOBANTE BAISSIÈRE 📉"

    # 2. MARTEAU / ETOILE FILANTE
    if lower_wick > (1.5 * body) and upper_wick < (0.2 * body):
        return "MARTEAU (REJET BAS) 🔨"
    if upper_wick > (1.5 * body) and lower_wick < (0.2 * body):
        return "ÉTOILE FILANTE (REJET HAUT) ☄️"

    # 3. DOJI (Indécision)
    if body < (0.1 * full_range):
        return "DOJI (RETOURNEMENT POSSIBLE) ⚖️"

    return None

async def trading_logic():
    api = DerivAPI(app_id=1089)
    await api.authorize(TOKEN_DERIV)
    last_epoch = None

    while True:
        try:
            r = await api.ticks_history({'ticks_history': 'stpY', 'count': 300, 'end': 'latest', 'style': 'candles', 'granularity': tf_seconds[current_tf]})
            df = pd.DataFrame(r['candles'])
            for col in ['open', 'close', 'high', 'low']: df[col] = df[col].astype(float)
            
            # Indicateurs
            ema = df['close'].ewm(span=200, adjust=False).mean()
            delta = df['close'].diff(); g = delta.where(delta > 0, 0).rolling(14).mean(); l = -delta.where(delta < 0, 0).rolling(14).mean()
            rsi = 100 - (100 / (1 + (g / l)))
            
            # Bougies pour analyse
            curr_c = df.iloc[-2] # Bougie confirmée
            prev_c = df.iloc[-3] # Bougie précédente
            
            p, r_val, e_val, epoch = curr_c['close'], rsi.iloc[-2], ema.iloc[-2], curr_c['epoch']
            pattern = analyze_patterns(curr_c, prev_c)

            if epoch != last_epoch:
                sig = None
                # LOGIQUE ACHAT : Tendance Haussière + RSI Sortie de Zone + Bougie Haussière
                if p > e_val and r_val >= 30 and pattern in ["ENGLOBANTE HAUSSIÈRE 📈", "MARTEAU (REJET BAS) 🔨"]:
                    sig = "ACHAT 🔵"
                    sl, tp1, tp2, tp3 = p-7, p+5, p+10, p+25
                
                # LOGIQUE VENTE : Tendance Baissière + RSI Sortie de Zone + Bougie Baissière
                elif p < e_val and r_val <= 70 and pattern in ["ENGLOBANTE BAISSIÈRE 📉", "ÉTOILE FILANTE (REJET HAUT) ☄️"]:
                    sig = "VENTE 🔴"
                    sl, tp1, tp2, tp3 = p+7, p-5, p-10, p-25

                if sig:
                    msg = (f"🎯 **SIGNAL STEP INDEX ({current_tf})**\nType: {sig}\nConfirmation: {pattern}\n\n"
                           f"Prix: `{p}`\n❌ SL: `{sl}`\n✅ TP1: `{tp1}` | TP2: `{tp2}` | TP3: `{tp3}`")
                    bot.send_message(ID_CHAT, msg, parse_mode="Markdown")
                last_epoch = epoch
        except Exception as e: print(f"Erreur: {e}")
        await asyncio.sleep(20)

if __name__ == "__main__":
    Thread(target=run_web).start()
    Thread(target=bot.infinity_polling, daemon=True).start()
    asyncio.run(trading_logic())
                    
