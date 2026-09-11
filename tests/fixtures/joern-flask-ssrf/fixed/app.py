from flask import request
import requests
def fetch():
    url = request.args.get("url")
    return requests.get("https://fixed.example.invalid", timeout=5)
