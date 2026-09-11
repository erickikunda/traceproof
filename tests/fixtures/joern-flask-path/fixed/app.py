from flask import request
def download():
    name = request.args.get("name")
    return open("/srv/files/help.txt").read()
