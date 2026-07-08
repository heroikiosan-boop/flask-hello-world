import time
import hmac
import hashlib
import requests
import logging
from flask import Flask, request, jsonify

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# --- 1. تنظیمات صرافی ویکس (مشخصات خود را دقیقاً اینجا وارد کنید) ---
WEEX_API_KEY = 'weex_57af930315aa859c641c180987f8ff5d'
WEEX_SECRET_KEY = '92f41c4b5fbe11fced7aa776dd305ae2e6600fc6e985d3df2ce94e8947293859'
WEEX_PASSPHRASE = 'Mosi4219sadra'
WEEX_URL = "https://api.weex.com" 

# رمز عبور اختصاصی وب‌هوک شما برای تریدینگ‌ویو
WEBHOOK_SECRET_PASSWORD = "MY_SECURE_PASSWORD_123"

def get_weex_sign(params, secret_key):
    query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
    return hmac.new(secret_key.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

def send_weex_request(path, params):
    params['apiKey'] = WEEX_API_KEY
    params['passphrase'] = WEEX_PASSPHRASE
    params['timestamp'] = str(int(time.time() * 1000))
    params['sign'] = get_weex_sign(params, WEEX_SECRET_KEY)

    headers = {"Content-Type": "application/json"}
    url = WEEX_URL + path
    try:
        response = requests.post(url, json=params, headers=headers, timeout=10)
        return response.json()
    except Exception as e:
        logging.error(f"Connection Error: {e}")
        return None

def setup_weex_leverage(symbol, leverage=10):
    path = "/api/v1/futures/changeLeverage"
    params = {
        "symbol": symbol.upper(),
        "leverage": str(leverage),
        "marginMode": "ISOLATED"
    }
    return send_weex_request(path, params)

def execute_weex_order(symbol, action, quantity):
    setup_weex_leverage(symbol, leverage=10)
    path = "/api/v1/futures/order"
    
    action_mapping = {
        "buy": "open_long",
        "sell": "open_short",
        "close_long": "close_long",
        "close_short": "close_short"
    }
    trade_side = action_mapping.get(action.lower(), "open_long")

    params = {
        "symbol": symbol.upper(),
        "side": trade_side,
        "type": "market",
        "quantity": str(quantity)
    }
    return send_weex_request(path, params)

@app.route('/webhook/', methods=['POST'])
def webhook():
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No data received"}), 400

        logging.info(f"Signal Received: {data}")

        if data.get("secret") != WEBHOOK_SECRET_PASSWORD:
            logging.warning("Unauthorized access attempt!")
            return jsonify({"status": "unauthorized"}), 401

        symbol = data.get("market")
        action = data.get("action")
        quantity = data.get("amount")

        if symbol and action and quantity:
            result = execute_weex_order(symbol, action, quantity)
            if result and result.get("code") == "0":
                return jsonify({"status": "success", "order_id": result.get("data", {}).get("orderId")}), 200
            else:
                return jsonify({"status": "exchange_error", "details": result}), 400
        else:
            return jsonify({"status": "missing_data"}), 400

    except Exception as e:
        logging.error(f"Webhook Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run()
