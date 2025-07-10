import numpy as np

def calculate_rsi(prices, period=14):
    if len(prices) < period:
        return None
    deltas = np.diff(prices)
    seed = deltas[:period]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    if down == 0:
        return 100
    rs = up / down
    return 100 - 100 / (1 + rs)

def calculate_cvd(bid_volumes, ask_volumes):
    if len(bid_volumes) != len(ask_volumes):
        return None
    return np.cumsum(np.array(bid_volumes) - np.array(ask_volumes))

def detect_market_structure(prices):
    if len(prices) < 10:
        return "UNKNOWN"
    if prices[-1] > max(prices[:-5]):
        return "BULLISH STRUCTURE"
    elif prices[-1] < min(prices[:-5]):
        return "BEARISH STRUCTURE"
    else:
        return "SIDEWAYS"
