import os

from flask import request


def search():
    term = request.args.get("term")


def other(value):
    os.system(value)
