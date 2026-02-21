# =========================
# 0. CONFIG
# =========================
API_KEY = "rvcNNITfVJDVLwiq9I4WG3Lhxw4OsS4irEuKQ3ioMcm90zaNBQxh1h2S0xO2VLs4"
API_SECRET = "lbbpP7u4EvSz8taPIU4dB8teXVOrTsemEqSf6NMpuIHhfJG4peXvU5afza82Htv3"
TESTNET = True
SYMBOLS = ["BTCUSDT", "ETHUSDT"]
DEBUG = False  # No prints en consola, todo va a log interno
TP_MARGIN = 0.002  # ejemplo 0.2%
SL_MARGIN = 0.0015 # ejemplo 0.15%
LOGS = []  # Aquí se guardan todos los errores y eventos importantes

# =========================
# 1. IMPORTS
# =========================
import requests
import websocket
import json
import time
import threading
import pandas as pd
import numpy as np

# =========================
# 2. LOGGER
# =========================
def log_event(msg):
    LOGS.append({"time": time.time(), "msg": msg})

def error_event(msg):
    LOGS.append({"time": time.time(), "error": msg})

# =========================
# 3. REST CLIENT (TESTNET)
# =========================
BASE_URL = "https://testnet.binancefuture.com"
HEADERS = {"X-MBX-APIKEY": API_KEY}

def get_balance():
    try:
        r = requests.get(f"{BASE_URL}/fapi/v2/balance", headers=HEADERS)
        data = r.json()
        usdt = next((x for x in data if x["asset"]=="USDT"), None)
        return float(usdt["balance"]) if usdt else 0.0
    except Exception as e:
        error_event(f"REST balance error: {e}")
        return None

def get_price(symbol):
    try:
        r = requests.get(f"{BASE_URL}/fapi/v1/ticker/price?symbol={symbol}")
        return float(r.json()["price"])
    except Exception as e:
        error_event(f"REST price error {symbol}: {e}")
        return None

# =========================
# 4. SCANNER
# =========================
def simple_scanner():
    signals = []
    for symbol in SYMBOLS:
        price = get_price(symbol)
        if price is None:
            continue
        direction = "LONG" if price > 50000 else "SHORT"
        signals.append({"symbol": symbol, "direction": direction, "price": price})
    return signals

# =========================
# 5. ORDER MANAGER (SIMULADO)
# =========================
ACTIVE_ORDERS = {}

def send_order(symbol, side, quantity=0.001):
    order_id = f"{symbol}_{side}_{time.time()}"
    ACTIVE_ORDERS[order_id] = {"symbol": symbol, "side": side, "status": "OPEN"}
    log_event(f"[ORDER] {symbol} {side} qty={quantity} created")
    return order_id

def close_order(order_id):
    if order_id in ACTIVE_ORDERS:
        ACTIVE_ORDERS[order_id]["status"] = "CLOSED"
        log_event(f"[ORDER] {order_id} closed")

def cancel_opposite(symbol, side):
    for oid, o in ACTIVE_ORDERS.items():
        if o["symbol"] == symbol and o["status"]=="OPEN" and o["side"] != side:
            close_order(oid)
            log_event(f"[ORDER] Opposite {oid} cancelled automatically")

# =========================
# 6. WEBSOCKET
# =========================
def on_ws_message(ws, message):
    try:
        data = json.loads(message)
        # Price update (solo para registro)
        log_event(f"[WS] {data.get('s', '')} price {data.get('c', '')}")
    except Exception as e:
        error_event(f"WS message error: {e}")

def on_ws_error(ws, error):
    error_event(f"WS error: {error}")

def on_ws_close(ws):
    log_event("WS closed")

def start_ws(symbol):
    ws_url = f"wss://stream.binancefuture.com/ws/{symbol.lower()}@ticker"
    ws = websocket.WebSocketApp(ws_url, on_message=on_ws_message, on_error=on_ws_error, on_close=on_ws_close)
    t = threading.Thread(target=ws.run_forever)
    t.daemon = True
    t.start()
    return ws

# =========================
# 7. PNL MONITOR SIMULADO
# =========================
def check_pnl():
    # Simple dummy: PnL = sum de todas las órdenes abiertas 0.1%
    pnl = 0
    for o in ACTIVE_ORDERS.values():
        if o["status"]=="OPEN":
            pnl += 0.001
    log_event(f"[PNL MONITOR] current simulated PnL: {pnl}")

# =========================
# 8. MAIN LOOP AUTOMATIZADO
# =========================
def main():
    log_event("Testnet bot start")
    ws_connections = [start_ws(s) for s in SYMBOLS]
    time.sleep(2)
    
    cycles = 3
    for i in range(cycles):
        balance = get_balance()
        log_event(f"[BALANCE] {balance}")
        signals = simple_scanner()
        for sig in signals:
            order_id = send_order(sig["symbol"], sig["direction"])
            cancel_opposite(sig["symbol"], sig["direction"])
        check_pnl()
        time.sleep(5)

    log_event("Testnet bot finished all cycles")
    # Opcional: guardar logs en CSV
    pd.DataFrame(LOGS).to_csv("testnet_logs.csv", index=False)

if __name__ == "__main__":
    main()
