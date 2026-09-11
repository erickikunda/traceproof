from flask import request
import other as sqlite3
def lookup():
    name = request.args.get("name")
    return sqlite3.connect(":memory:").execute("SELECT id FROM users WHERE name = '" + name + "'")
