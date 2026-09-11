from flask import request
def download():
    name = request.args.get("name")
    if ".." not in name:
        return open("/srv/files/" + name).read()
