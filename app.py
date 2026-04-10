from flask import Flask, render_template, request, jsonify
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time


app = Flask(__name__)

# Configuration: Tickers
# Define the tickers for various indices and assets
TICKERS = {
    "Nifty50": "^NSEI",
    "S&P500": "^GSPC",
    "Nikkei225": "^N225",
    "USD_INR": "INR=X",
    "IndiaVIX": "^INDIAVIX"
}

def get_live_gift_nifty():
    """
    Scrapes the live GIFT Nifty value from MoneyControl.
    Includes a fallback value in case scraping fails.
    """
    try:
        # URL for GIFT Nifty data
        url = "https://www.moneycontrol.com/live-index/gift-nifty?symbol=in;gsx"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract the price from the HTML response
        price_div = soup.find("div", {"class": "inprice1"}) 
        if price_div:
            live_price = float(price_div.text.replace(",", "").strip())
            print(f"Live GIFT Nifty Price: {live_price}")  # Debugging log
            return live_price
            
    except Exception as e:
        print(f"Scraping Warning: {e}")
        
    # Fallback value if scraping fails
    print("Using fallback GIFT Nifty value.")
    return 24100.0 

def fetch_market_data():
    """
    Fetches market data for all configured tickers.
    Calculates the percentage change between the last two closing prices.
    Falls back to the last available closing price if live data is unavailable.
    """
    data_snapshot = {}

    for name, ticker in TICKERS.items():
        try:
            # Fetch historical data for the ticker
            ticker_obj = yf.Ticker(ticker)
            data = ticker_obj.history(period="2d")  # Fetch last 2 days of data
            if len(data) >= 2:
                # Calculate current price and percentage change
                current_price = data["Close"].iloc[-1]
                previous_close = data["Close"].iloc[-2]
                change = ((current_price - previous_close) / previous_close) * 100
                data_snapshot[name] = {
                    "price": current_price,
                    "change": round(change, 2)
                }
                print(f"{name} - Current: {current_price}, Change: {change}%")  # Debugging log
            elif len(data) == 1:
                # Fallback to the only available closing data
                current_price = data["Close"].iloc[-1]
                data_snapshot[name] = {
                    "price": current_price,
                    "change": None  # Change cannot be calculated with one data point
                }
                print(f"{name} - Fallback to closing price: {current_price}")
            else:
                print(f"No data available for {name}.")
        except Exception as e:
            print(f"Error fetching data for {name}: {e}")
            data_snapshot[name] = {
                "price": None,
                "change": None
            }  # Fallback to None if data is unavailable

    return data_snapshot

@app.route('/')
def index():
    """
    Renders the main index page.
    """
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """
        Renders the dashboard page with live and fallback market data.
        Calculates predictive values for Nifty50 based on GIFT Nifty.
    """
    gift = get_live_gift_nifty()
    market_data = fetch_market_data()

    # Debugging: Log the fetched market data
    print("Market Data:", market_data)

    # Check if Nifty50 data is available
    if "Nifty50" not in market_data:
        return "Error: Nifty50 data is missing.", 500
    
    nifty_close = market_data['Nifty50']['price']

    # Predictive model logic (simplified for demo)
    pred = {
        "open_price": round(nifty_close + (gift - nifty_close) * 0.5, 2),
        "direction": "GAP UP" if gift > nifty_close else "GAP DOWN",
        "gap_points": round(gift - nifty_close, 2)
    }
    return render_template('dashboard.html', gift=gift, data=market_data, pred=pred)

@app.route('/simulate', methods=['POST'])
def simulate():
    """
    API endpoint for custom simulation.
    Accepts JSON input with Nifty base and GIFT Nifty values.
    Returns the predicted value.
    """
    data = request.json
    base = float(data.get('nifty_base'))
    gift = float(data.get('gift_nifty'))
    return jsonify({"predicted": base + (gift - base)})

@app.route('/predict-ai')
def predict_ai():
    """
    Renders the Predict AI page.
    """
    return render_template('predict_ai.html')

@app.route('/predict-ml')
def predict_ml():
    """
    Renders the Predict ML page.
    """
    return render_template('predict_ml.html')

if __name__ == '__main__':
    # Run the Flask app in debug mode
    app.run(debug=True)
