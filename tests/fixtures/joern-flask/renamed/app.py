import os as process

from flask import request as incoming


def anything():
    query = incoming.args.get("query")
    process.system(query)
