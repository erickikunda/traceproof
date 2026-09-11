from flask import request
import other as requests
def fetch():
    url = request.args.get("url")
    return requests.get(url)
