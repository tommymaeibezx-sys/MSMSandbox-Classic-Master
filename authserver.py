from flask import Flask, request, jsonify, g, send_from_directory, abort, render_template_string
import secrets
import sqlite3
import hashlib
import time
import random
import os
import re
import platform
import requests
import json

from tools.database import get_db, db_player # type: ignore

from tools.utils import *

app = Flask(__name__)

CONTENT_ROOT = os.path.join(os.path.dirname(__file__), "files")

IV = get_config_value("iv")
KEY = get_config_value("key")

def table_exists(cursor, table_name):
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
    """, (table_name,))
    return cursor.fetchone() is not None

def create_player_tables():
    tables = {
        "users": """
            CREATE TABLE users (
                bbb_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                date_created INTEGER,
                mac_address TEXT NOT NULL,
                ip TEXT
            )
        """,
        "user_friends": """
            CREATE TABLE user_friends (
                user_1 INTEGER,
                user_2 INTEGER
            )
        """,
        "players": """
            CREATE TABLE players (
                bbb_id INTEGER PRIMARY KEY,
                active_island INTEGER,
                coins INTEGER DEFAULT 0,
                food INTEGER DEFAULT 0,
                diamonds INTEGER DEFAULT 0,
                shards INTEGER DEFAULT 0,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                last_login INTEGER,
                display_name TEXT
            )
        """,
        "player_islands": """
            CREATE TABLE player_islands (
                user_island_id INTEGER PRIMARY KEY AUTOINCREMENT,
                bbb_id INTEGER,
                date_created INTEGER,
                likes INTEGER DEFAULT 0,
                dislikes INTEGER DEFAULT 0,
                island_id INTEGER,
                warp_speed REAL DEFAULT 1.0,
                FOREIGN KEY(bbb_id) REFERENCES users(bbb_id)
            )
        """,
        "player_monsters": """
            CREATE TABLE player_monsters (
                user_monster_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_island_id INTEGER,
                pos_x INTEGER,
                pos_y INTEGER,
                flip INTEGER DEFAULT 0,
                muted INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                date_created INTEGER,
                happiness INTEGER DEFAULT 50,
                monster INTEGER,
                volume REAL DEFAULT 1.0,
                times_fed INTEGER DEFAULT 0,
                collected_coins INTEGER DEFAULT 0,
                last_collection INTEGER,
                FOREIGN KEY(user_island_id) REFERENCES player_islands(user_island_id)
            )
        """,
        "player_structures": """
            CREATE TABLE player_structures (
                user_structure_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_island_id INTEGER,
                date_created INTEGER,
                pos_x INTEGER,
                pos_y INTEGER,
                flip INTEGER DEFAULT 0,
                muted INTEGER DEFAULT 0,
                is_complete INTEGER DEFAULT 0,
                is_upgrading INTEGER DEFAULT 0,
                structure INTEGER,
                scale REAL DEFAULT 1.0,
                building_completed INTEGER,
                last_collection INTEGER,
                obj_data INTEGER,
                obj_end INTEGER
            )
        """,
        "player_eggs": """
            CREATE TABLE player_eggs (
                user_egg_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_island_id INTEGER,
                laid_on INTEGER,
                hatches_on INTEGER,
                monster INTEGER,
                user_structure_id INTEGER,
                FOREIGN KEY(user_island_id) REFERENCES player_islands(user_island_id)
            )
        """,
        "monster_mega_data": """
            CREATE TABLE monster_mega_data (
                user_monster_id INTEGER PRIMARY KEY,
                started_at INTEGER,
                finishes_at INTEGER,
                permamega INTEGER,
                currently_mega INTEGER,
                FOREIGN KEY(user_monster_id) REFERENCES player_monsters(user_monster_id)
            )
        """,
    }

    for name, query in tables.items():
        if not table_exists(cur_player, name):
            cur_player.execute(query)
            print(f"✅ Table '{name}' created successfully.")
        else:
            print(f"ℹ️ Table '{name}' already exists.")

    db_player.commit()

def md5_file(path):
    hash_md5 = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def generate_game_info(length):
    chars = "bcdfghjkmnpqrstvwxyz23456789"
    return ''.join(random.choice(chars) for _ in range(length))

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'])
def catch_all(path):
    print("----- Incoming Request -----")
    print("Method:", request.method)
    print("Path:", "/" + path)
    print("Remote Addr:", request.remote_addr)

    print("\nHeaders:")
    for k, v in request.headers.items():
        print(f"  {k}: {v}")

    print("\nQuery Params:")
    print(request.args.to_dict())

    print("\nBody:")
    try:
        print(request.get_data(as_text=True))
    except Exception as e:
        print("Could not read body:", e)

    print("----- End Request -----\n")

    return "OK\n", 200

GAME_SERVER_IP = "35.177.202.244"

if platform.system() == "Windows":
    GAME_SERVER_IP = "192.168.1.16"
    
@app.route('/auth.php', methods=['GET'])
def auth():
    q = request.args
    username = q.get("u")
    password = q.get("p")
    login_type = q.get("t")
    game = int(q.get("g", 0))
    client_version = q.get("client_version")
    ip = request.remote_addr

    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT bbb_id, password FROM users WHERE username = ?", (username,))
    user = cur.fetchone()

    if user:
        bbb_id, stored_password = user
        if stored_password != password:
            response = {
                "ok": False,
                "acc_exists": True,
                "message": "Incorrect password"
            }
            return jsonify(response)
    else:
        cur.execute(
            "INSERT INTO users (username, password, date_created, mac_address, ip) VALUES (?, ?, ?, ?, ?)",
            (username, password, int(time.time()), "00:00:00:00:00:00", ip)
        )
        bbb_id = cur.lastrowid
        db.commit()

    token_json = {
        "username": username,
        "password": password,
        "login_type": login_type,
        "client_version": client_version
    }
    access_token = encrypt(json.dumps(token_json), IV, KEY)

    response = {
        "ok": True,
        "acc_exists": True,
        "sessId": access_token,
        "bbbId": bbb_id,
        "username": username,
        "password": password,
        "serverIp": GAME_SERVER_IP,
        "login_type": login_type,
        "contentUrl": f"http://{GAME_SERVER_IP}:900/content/{client_version}/files.json",
        "friends": get_friends(cur, bbb_id),
        "auto_login": True
    }

    print(response)
    return jsonify(response)

def get_friends(cur, bbb_id):
    cur.execute("""
    SELECT user_1, user_2 FROM user_friends 
    WHERE user_1 = ? OR user_2 = ?
    """, (bbb_id, bbb_id))

    rows = cur.fetchall()

    friends = []

    for u1, u2 in rows:
        if u1 == bbb_id:
            friends.append(u2)
        else:
            friends.append(u1)

    return friends

'''
@app.route('/friends.php', methods=['GET'])
def friends():
    fid = request.args.get('fid', "")
    cmd = request.args.get('c', "")

    numeric_fid = int(''.join(re.findall(r'\d+', fid))) if fid else None

    data = ip2user.get(request.remote_addr)
    if not data:
        return jsonify({"ok": False, "c": cmd})

    username = data["username"]
    password = data["password"]
    bbb_id = data["bbb_id"]

    db = get_db()
    cur = db.cursor()

    exists = player_exists(numeric_fid)

    if bbb_id and numeric_fid != "" and exists:
        if cmd == "add":
            insert_values = (bbb_id, numeric_fid)
            cur.execute("""
                INSERT OR IGNORE INTO user_friends (user_1, user_2) 
                VALUES (?, ?)
            """, insert_values)
            db.commit()

            response = {
                "add": "1",
                "fid": numeric_fid,
                "c": cmd,
                "ok": True,
                "friends": get_friends(cur, bbb_id)
            }
        else:
            cur.execute("""
                DELETE FROM user_friends WHERE (user_1=? AND user_2=?) OR (user_1=? AND user_2=?)
            """, (bbb_id, numeric_fid, numeric_fid, bbb_id))
            db.commit()

            response = {
                "ok": True,
                "c": cmd,
                "fid": numeric_fid,
                "remove": "1",
                "friends": get_friends(cur, bbb_id)
            }
    else:
        print(bbb_id, numeric_fid, exists)
        response = {
            "ok": False,
            "c": cmd
        }

    return jsonify(response)
'''

updates_data = []

@app.route('/content/<ver>/files.json', methods=['GET'])
def get_updates(ver):
    files_list = []

    version_root = os.path.join(CONTENT_ROOT, ver)

    for root, dirs, files in os.walk(version_root):
        for file in files:
            full_path = os.path.join(root, file)

            relative_path = os.path.relpath(full_path, version_root)

            checksum = md5_file(full_path)

            files_list.append({
                "localName": relative_path,
                "serverName": relative_path,
                "checksum": checksum
            })

    return jsonify(files_list)

@app.route('/content/<ver>/<path:filename>', methods=['GET'])
def serve_file(ver, filename):
    filename = filename.replace("\\", "/")
    full_path = os.path.join(CONTENT_ROOT, ver, filename)
    if os.path.isfile(full_path):
        return send_from_directory(os.path.join(CONTENT_ROOT, ver), filename)
    else:
        abort(404)

create_player_tables()
#create_new_content()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=900,
        debug=False
    )
