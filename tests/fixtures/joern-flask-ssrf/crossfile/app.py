from flask import request
from client import fetch_url
def fetch():
    url = request.args.get("url")
    return fetch_url(url)
