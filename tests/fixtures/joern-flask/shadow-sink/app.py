import os

from flask import request


def search(os):
    term = request.args.get("term")
    os.system(term)
