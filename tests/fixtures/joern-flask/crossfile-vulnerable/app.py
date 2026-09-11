from flask import request
from service import run


def arbitrary():
    return run(request.form.get("value"))
