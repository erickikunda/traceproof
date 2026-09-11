from flask import request
from storage import lookup_name
def lookup():
    name = request.args.get("name")
    return lookup_name(name)
