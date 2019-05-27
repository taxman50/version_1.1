import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps



def lookup(symbol):
    """Look up quote for symbol."""

    # Contact API
    try:
        response = requests.get(f"https://api.iextrading.com/1.0/stock/{urllib.parse.quote_plus(symbol)}/quote")
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    try:
        quote = response.json()
        return {
            "name": quote["companyName"],
            "price": float(quote["latestPrice"]),
            "symbol": quote["symbol"],
            "marketCap":quote["marketCap"]
        }
    except (KeyError, TypeError, ValueError):
        return None



def cap(value):
    if value < 1000000000:
        value = value / 1000000
        return f"${value:,.2f}M"
    else:
        value = value / 1000000000
        return f"${value:,.2f}B"