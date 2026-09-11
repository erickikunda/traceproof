from flask import request
import requests
def fetch():
    url = request.args.get("url")
    if url.startswith("https://"):
        return requests.get(url)
