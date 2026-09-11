import os

from flask import request


def search():
    term = request.args.get("term")
    os.system("echo safe")
