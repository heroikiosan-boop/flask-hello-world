import time, hmac, hashlib, requests, logging, json
from flask import Flask, request, jsonify

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app = Flask(__name__)

# --- CONFIG ---
WEEX_API_KEY = 'weex_57af930315aa859c641c180987f8ff5d'
WEEX_SECRET_KEY = '92f41c4b5fbe11fced7aa776dd305ae2e6600fc6e985d3df2ce94e8947293859'
WEEX_PASSPHRASE = 'Mosi4219sadra'
WEEX_URL = "https://weexapi.com"
WEBHOOK_SECRET_PASSWORD = "MY_SECURE_PASSWORD_123"

def get_weex_sign(params, secret_key):
    query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
    return hmac.new(secret_key.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

def send_weex_request(path, params):
    params['apiKey'] = WEEX_API_KEY
    params['passphrase'] = WEEX_PASSPHRASE
    params['timestamp'] = str(int(time.time() * 1000))
    params['sign'] = get_weex_sign(params, WEEX_SECRET_KEY)
    headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        res = requests.post(WEEX_URL + path, json=params, headers=headers, timeout=15)
        return res.json()
    except Exception as e:
        logging.error(f"Connection Error: {e}")
        return None

def execute_weex_order(symbol, action):
    path = "/capi/v3/order"
    trade_side = "BUY" if action.lower() in ["buy", "long"] else "SELL"
    pos_side = "LONG" if action.lower() in ["buy", "long"] else "SHORT"
    
    params = {
        "symbol": symbol.upper(),
        "side": trade_side,
        "positionSide": pos_side,
        "type": "MARKET",
        "quantity": "0.01"
    }
    return send_weex_request(path, params)

@app.route('/webhook/', methods=['POST'])
def webhook():
    try:
        raw_data = request.data.decode('utf-8').strip().strip('"')
        data = json.loads(raw_data)
        logging.info(f"Signal Received: {data}")
        if data.get("secret") != WEBHOOK_SECRET_PASSWORD:
            return jsonify({"status": "unauthorized"}), 401
        
        symbol = data.get("market")
        action = data.get("action")
        
        if symbol and action:
            result = execute_weex_order(symbol, action)
            return jsonify({"status": "processed", "response": result}), 200
        return jsonify({"status": "missing_data"}), 400
    except Exception as e:
        logging.error(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run()
