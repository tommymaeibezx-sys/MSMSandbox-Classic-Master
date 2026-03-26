import sqlite3
import time

from flask import g

db_player = sqlite3.connect("player_data.db", check_same_thread=False)
db_player.row_factory = sqlite3.Row

db_player.execute("PRAGMA journal_mode=WAL;")
db_player.commit()

cur_player = db_player.cursor()

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect("player_data.db")
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL;")
    return g.db