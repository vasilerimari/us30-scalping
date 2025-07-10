import streamlit as st
import asyncio
import websockets
import json
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict, deque
from utils_confirmari import calculate_rsi, calculate_cvd, detect_market_structure

POLYGON_API_KEY = "NcRnNhMkfPDwv_gCgMDCKwgnpXb0jLnM"
# versiune testată manual

TELEGRAM_WEBHOOK_URL = st.secrets.get("TELEGRAM_WEBHOOK_URL", "")

WATCHLIST = [
    "AAPL", "MSFT", "UNH", "JNJ", "V", "PG", "GS", "HD", "CVX", "MCD",
    "CAT", "MRK", "TRV", "HON", "AXP", "IBM", "NKE", "JPM", "DIS", "WMT",
    "KO", "INTC", "CSCO", "VZ", "BA", "MMM", "AMGN", "WBA", "DOW"
]

trades = defaultdict(lambda: deque(maxlen=300))
timestamps = defaultdict(lambda: deque(maxlen=300))
bid_volumes = defaultdict(lambda: deque(maxlen=300))
ask_volumes = defaultdict(lambda: deque(maxlen=300))
alerts = []
us30_index = deque(maxlen=300)
signal_results = []

def send_telegram(msg):
    if TELEGRAM_WEBHOOK_URL:
        try:
            requests.post(TELEGRAM_WEBHOOK_URL, json={"text": msg})
        except:
            pass

async def polygon_listener(queue, running):
    url = "wss://socket.polygon.io/stocks"
    async with websockets.connect(url) as ws:
        await ws.send(json.dumps({"action": "auth", "params": POLYGON_API_KEY}))
        params = ",".join([f"T.{t}" for t in WATCHLIST] + [f"Q.{t}" for t in WATCHLIST])
        await ws.send(json.dumps({"action": "subscribe", "params": params}))
        while running():
            try:
                msg = await ws.recv()
                data = json.loads(msg)
                for item in data:
                    t = item.get("sym")
                    if item["ev"] == "T":
                        trades[t].append(item["p"])
                        timestamps[t].append(datetime.fromtimestamp(item["t"] / 1000))
                    elif item["ev"] == "Q":
                        bid_volumes[t].append(item["s"])
                        ask_volumes[t].append(item["S"])
            except:
                await asyncio.sleep(1)

def analyze_confirmations():
    now = datetime.utcnow() + timedelta(hours=3)
    if not (now.hour >= 15 and now.hour < 22):
        return []
    signals = []
    for t in WATCHLIST:
        if len(trades[t]) >= 20:
            rsi = calculate_rsi(list(trades[t]))
            cvd_array = calculate_cvd(list(bid_volumes[t]), list(ask_volumes[t]))
            structure = detect_market_structure(list(trades[t]))

            score = 0
            if rsi and rsi < 30: score += 1
            if rsi and rsi > 70: score -= 1
            if structure == "BULLISH STRUCTURE": score += 1
            elif structure == "BEARISH STRUCTURE": score -= 1
            if cvd_array is not None and len(cvd_array) > 0:
                if cvd_array[-1] > 0: score += 1
                elif cvd_array[-1] < 0: score -= 1

            if score >= 2:
                msg = f"🟢 CONFIRMED BUY {t} | RSI={rsi:.1f}, Struct={structure}, CVD={cvd_array[-1]:.1f}"
                signals.append(msg)
                alerts.append(msg)
                send_telegram(msg)
                signal_results.append(True)
            elif score <= -2:
                msg = f"🔴 CONFIRMED SELL {t} | RSI={rsi:.1f}, Struct={structure}, CVD={cvd_array[-1]:.1f}"
                signals.append(msg)
                alerts.append(msg)
                send_telegram(msg)
                signal_results.append(True)
            else:
                signal_results.append(False)
    return signals
