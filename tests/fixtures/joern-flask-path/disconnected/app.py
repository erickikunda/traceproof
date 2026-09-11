from flask import request
def download():
    name = request.args.get("name")
    return name
def unrelated(value):
    return open(value).read()
