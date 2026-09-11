import os

from flask import request


def search(request):
    term = request.args.get("term")
    os.system(term)
