import sqlite3
import time
import platform

dev = platform.system() == "Windows"

suffix = "dev" if dev else "prod"

db_file_name = f"player_data_{suffix}.db"

db_player = sqlite3.connect(db_file_name, timeout=10, check_same_thread=False)
db_player.row_factory = sqlite3.Row

db_player.execute("PRAGMA journal_mode=WAL;")
db_player.commit()

cur_player = db_player.cursor()