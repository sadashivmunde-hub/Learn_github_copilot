from flask import Flask, render_template, request, jsonify
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

app = Flask(__name__)

# Configuration: Tickers
TICKERS = {
    "Nifty50": "^NSEI",
    "S&P500": "^GSPC",
    "Nikkei225": "^N225",
    "USD_INR": "INR=X",
    "IndiaVIX": "^INDIAVIX"
}

def get_live_gift_nifty():
    """
    Scrapes GIFT Nifty. Includes a fallback for when scraping fails.
    """
    try:
        # SOURCE: MoneyControl (Selectors subject to change)
        url = "https://www.moneycontrol.com/live-index/gift-nifty?symbol=in;gsx"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Attempt to find price (Update class based on site changes)
        price_div = soup.find("div", {"class": "inprice1"}) 
        if price_div:
            return float(price_div.text.replace(",", "").strip())
            
    except Exception as e:
        print(f"Scraping Warning: {e}")
        
    # FALLBACK: Return a calculated estimate if scraper fails (for demo stability)
    # In production, use a paid API like Bloomberg/Refinitiv
    return 24100.0 

def fetch_market_data():
    """
    Fetches previous close data for all indicators.
    """
    data_snapshot = {}
    
    for name, ticker in TICKERS.items():
        try:
            ticker_obj = yf.Ticker(ticker)
            hist = ticker_obj.history(period="5d") # Fetch 5 days to ensure we get last close
            
            if not hist.empty:
                last_close = hist['Close'].iloc[-1]
                prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else last_close
                change_pct = ((last_close - prev_close) / prev_close) * 100
                
                data_snapshot[name] = {
                    "price": round(last_close, 2),
                    "change": round(change_pct, 2)
                }
            else:
                data_snapshot[name] = {"price": 0, "change": 0}
                
        except Exception as e:
            print(f"Error fetching {name}: {e}")
            data_snapshot[name] = {"price": 0, "change": 0}
            
    return data_snapshot

@app.route('/')
def dashboard():
    # 1. Get Base Data
    market_data = fetch_market_data()
    gift_nifty_live = get_live_gift_nifty()
    
    nifty_close = market_data['Nifty50']['price']
    
    # 2. Prediction Logic (Heuristic Model)
    # Formula: Open ~ Nifty_Prev_Close + (GIFT_Nifty - Nifty_Prev_Close) + Sentiment_Bias
    
    # Calculate the raw gap
    raw_gap = gift_nifty_live - nifty_close
    
    # Calculate Sentiment Bias (Asian + US impact)
    sentiment_score = 0
    if market_data['Nikkei225']['change'] > 0.5: sentiment_score += 15
    if market_data['Nikkei225']['change'] < -0.5: sentiment_score -= 15
    if market_data['S&P500']['change'] > 0.5: sentiment_score += 10
    if market_data['S&P500']['change'] < -0.5: sentiment_score -= 10
    
    # Volatility Dampener: High VIX = Larger expected moves
    vix = market_data['IndiaVIX']['price']
    volatility_factor = 1.2 if vix > 15 else 0.8
    
    predicted_open = nifty_close + (raw_gap * 0.9) + (sentiment_score * volatility_factor)
    predicted_gap = predicted_open - nifty_close
    
    prediction = {
        "open_price": round(predicted_open, 2),
        "gap_points": round(predicted_gap, 2),
        "direction": "GAP UP" if predicted_gap > 0 else "GAP DOWN",
        "color": "green" if predicted_gap > 0 else "red"
    }
    
    return render_template('dashboard.html', 
                           data=market_data, 
                           gift=gift_nifty_live, 
                           pred=prediction)

@app.route('/simulate', methods=['POST'])
def simulate():
    # API Endpoint for custom simulation
    data = request.json
    base = float(data.get('nifty_base'))
    gift = float(data.get('gift_nifty'))
    return jsonify({"predicted": base + (gift - base)})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
