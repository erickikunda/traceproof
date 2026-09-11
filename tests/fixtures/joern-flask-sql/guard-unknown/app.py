from flask import request
import sqlite3
def lookup():
    name = request.args.get("name")
    if len(name) < 30:
        return sqlite3.connect(":memory:").execute("SELECT id FROM users WHERE name = '" + name + "'")
