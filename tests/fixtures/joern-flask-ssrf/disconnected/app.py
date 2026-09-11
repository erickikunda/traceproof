from flask import request
import requests
def fetch():
    return request.args.get("url")
def other(url):
    return requests.get(url)
