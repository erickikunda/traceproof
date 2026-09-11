from flask import request
import requests
def fetch():
    url = request.args.get("url")
    return requests.get(url, timeout=5)
