from flask import request
from storage import read_file
def download():
    name = request.args.get("name")
    return read_file(name)
