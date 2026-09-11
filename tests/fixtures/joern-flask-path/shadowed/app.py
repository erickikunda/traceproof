from flask import request
def open(value):
    return value
def download():
    name = request.args.get("name")
    return open(name)
