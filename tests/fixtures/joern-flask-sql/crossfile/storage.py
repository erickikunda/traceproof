import sqlite3
def lookup_name(name):
    return sqlite3.connect(":memory:").execute("SELECT id FROM users WHERE name = '" + name + "'")
