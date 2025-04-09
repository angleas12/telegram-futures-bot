import time
import requests

# === Config ===
TOKEN = "7637589435:AAGHvzoe6Of3TgF4dREdrRZxJvbqWoaQhaQ"
URL = f"https://api.telegram.org/bot{TOKEN}"
LAST_UPDATE_ID = 0  # Store last processed message

# === Market Data Functions ===
def get_binance_spot(symbol):
    try:
        res = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol.upper()}USDT")
        return float(res.json()['price'])
    except:
        return None

def get_binance_futures(symbol):
    try:
        fut = requests.get(f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol.upper()}USDT").json()
        funding = requests.get(f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol.upper()}USDT&limit=1").json()
        return float(fut['price']), float(funding[0]['fundingRate'])
    except:
        return None, None

def get_ls_ratio(symbol):
    mock = {"PEPE": 1.85, "DOGE": 1.4, "SHIB": 0.9}
    return mock.get(symbol.upper(), 1.2)

def decide_signal(spot, fut, funding, ls):
    reasons = []
    signal = "NEUTRAL"
    premium = (fut - spot) / spot if spot and fut else 0

    if funding and funding > 0.01:
        signal = "SHORT"
        reasons.append("High funding → long crowd")
    elif funding and funding < -0.01:
        signal = "LONG"
        reasons.append("Negative funding → short crowd")

    if premium > 0.01:
        signal = "SHORT"
        reasons.append("Futures > Spot → Likely correction")
    elif premium < -0.01:
        signal = "LONG"
        reasons.append("Spot > Futures → Bullish")

    if ls:
        if ls > 1.5:
            signal = "SHORT"
            reasons.append("L/S ratio overheated")
        elif ls < 0.7:
            signal = "LONG"
            reasons.append("L/S ratio low → short-heavy")

    return signal, reasons

def extended_analysis(spot, signal):
    if signal == "LONG":
        entry = f"{spot*0.995:.8f} - {spot*1.002:.8f}"
        tp = f"{spot*1.02:.8f}"
        sl = f"{spot*0.985:.8f}"
        lev = "5x - 10x"
    elif signal == "SHORT":
        entry = f"{spot*1.002:.8f} - {spot*1.007:.8f}"
        tp = f"{spot*0.98:.8f}"
        sl = f"{spot*1.015:.8f}"
        lev = "5x - 8x"
    else:
        entry = "Neutral zone"
        tp = "-"
        sl = "-"
        lev = "1x or skip"
    return entry, tp, sl, lev

# === Telegram sendMessage ===
def send_msg(chat_id, msg):
    try:
        requests.post(f"{URL}/sendMessage", data={
            "chat_id": chat_id,
            "text": msg,
            "parse_mode": "HTML"
        })
    except Exception as e:
        print(f"Telegram send error: {e}")

# === Main Listener ===
def run_bot():
    global LAST_UPDATE_ID
    print("🤖 Listening for commands... Send coin symbol to bot.")

    while True:
        try:
            res = requests.get(f"{URL}/getUpdates?offset={LAST_UPDATE_ID+1}&timeout=10").json()
            for update in res['result']:
                LAST_UPDATE_ID = update['update_id']
                msg = update.get('message') or update.get('channel_post')
                chat_id = msg['chat']['id']
                text = msg.get('text', '').strip()

                if not text.isalpha(): continue  # Only coin names

                coin = text.upper()
                spot = get_binance_spot(coin)
                fut, funding = get_binance_futures(coin)
                ls = get_ls_ratio(coin)

                if not all([spot, fut]):
                    send_msg(chat_id, f"❌ Data not found for {coin}")
                    continue

                signal, reasons = decide_signal(spot, fut, funding, ls)
                entry, tp, sl, lev = extended_analysis(spot, signal)

                reply = f"""📢 <b>{coin} Futures Signal</b>

📈 <b>Position</b>: {signal}
🎯 Entry: <code>{entry}</code>
🎯 TP: {tp} | 🛑 SL: {sl}
💥 Leverage: {lev}
📊 Funding: {funding}
📌 Reasons:
""" + "\n".join([f"• {r}" for r in reasons])

                send_msg(chat_id, reply)

        except Exception as e:
            print("Loop error:", e)

        time.sleep(2)  # Polling delay

if __name__ == "__main__":
    run_bot()
