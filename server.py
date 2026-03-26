
import platform

from sfs2x.transport import server_from_url, TCPTransport
from sfs2x.protocol import Message, ControllerID, SysAction
from sfs2x.core import SFSObject, SFSArray

import hashlib
import asyncio
import time
import traceback

from flask import g

from room import Room

from msmdata.player import Player
from msmdata.island import Island
from msmdata.structure import Structure
from msmdata.egg import Egg # type: ignore
from msmdata.monster import Monster #type: ignore
from msmdata.megadata import MegaData # type: ignore

from msmdata.get_data import *

from tools.utils import player_exists

from tools.database import cur_player, db_player # type: ignore

CURRENT_PLAYERS = 0
MAX_PLAYERS = 100

KICK_IF_OUTDATED = True
GAME_SERVER_IP = "0.0.0.0"

if platform.system() == "Windows":
    KICK_IF_OUTDATED = False
    AUTH_SERVER_IP = "192.168.1.16"
    GAME_SERVER_IP = AUTH_SERVER_IP

DATA_CACHE = {}

async def send_extension_response(client, cmd, params):
    ext_resp = SFSObject()
    ext_resp.put_utf_string("c", cmd)
    ext_resp.put_int("r", -1)
    ext_resp.put_sfs_object("p", params)

    await client.send(Message(
        controller=ControllerID.EXTENSION,
        action=12,
        payload=ext_resp
    ))

def load_static_data():
    global DATA_CACHE

    print("Loading static data")

    DATA_CACHE["genes"] = get_genes()
    DATA_CACHE["islands"] = get_islands()
    DATA_CACHE["torches"] = get_torch_data()
    DATA_CACHE["monsters"] = get_monsters()
    DATA_CACHE["structures"] = get_structures()
    DATA_CACHE["levels"] = get_levels()
    DATA_CACHE["scratchoffs"] = get_scratchoffs()
    DATA_CACHE["timed_events"] = get_timed_events()
    DATA_CACHE["quests"] = get_quests()
    DATA_CACHE["game_settings"] = get_game_settings()

    print("Static data loaded")

def get_game_setting_from_key(search_key):
    for obj in DATA_CACHE["game_settings"]:
        key = obj.get("key")
        if key == search_key:
            return obj.get("value")
    return None

def buy_entity(client, entity_id):
    cur.execute("SELECT * FROM entities WHERE entity_id = ?", (entity_id,))
    row = cur.fetchone()

    worked = client.player.add_properties(-row["cost_coins"], -row["cost_diamonds"], 0, 0, row["cost_eth_currency"])

    return worked

def sell_entity(client, entity_id):
    cur.execute("SELECT * FROM entities WHERE entity_id = ?", (entity_id,))
    row = cur.fetchone()

    worked = client.player.add_properties(row["cost_coins"] * 0.75, row["cost_diamonds"] * 0.75, 0, 0, -row["cost_eth_currency"] * 0.75)

    return worked

async def handle_client(client: TCPTransport):
    global CURRENT_PLAYERS
    try:
        async for message in client.listen():
            payload = message.payload
            current_time_ms = int(time.time() * 1000)
            if "p" in payload and payload["p"] is not None:
                params = payload.get("p")
            else:
                params = SFSObject()

            if message.action == SysAction.HANDSHAKE:
                print("Handshake")
                token = hashlib.md5(client._host.encode()).hexdigest()

                session_info = SFSObject()
                session_info.put_int("ct", 1000000)
                session_info.put_int("ms", 8000000)
                session_info.put_utf_string("tk", token)
                
                await client.send(Message(
                    controller=ControllerID.SYSTEM,
                    action=SysAction.HANDSHAKE,
                    payload=session_info
                ))
            elif message.action == SysAction.LOGIN:
                print("Login")

                bbb_id = int(payload.get("un"))

                login = SFSObject()
                login.put_short("rs", 0)
                login.put_utf_string("zn", "MySingingMonsters")
                login.put_utf_string("un", str(bbb_id))
                login.put_short("pi", 3)
                login.put_int("id", 1)
                login.put_sfs_object("p", SFSObject())

                MSMRoom = Room(room_id=0, name="Limbo", room_type="default", is_hidden=False, 
                is_password_protected=False, is_game=False, min_players=0, max_players=MAX_PLAYERS)

                RoomArrays = SFSArray()
                RoomArrays.add(MSMRoom.to_sfs_array())

                login.put_sfs_array("rl", RoomArrays)

                await client.send(Message(
                    controller=ControllerID.SYSTEM,
                    action=SysAction.LOGIN,
                    payload=login
                ))

                game_settings = SFSObject()
                game_settings.put_sfs_array("user_game_settings", DATA_CACHE["game_settings"])

                await send_extension_response(client, "game_settings", game_settings)

                exists = player_exists(bbb_id)

                player = Player(bbb_id, "New Player")

                print(exists)

                if exists:
                    cur_player.execute("""
                        SELECT active_island, display_name FROM players WHERE bbb_id = ?
                    """, (bbb_id,))
                    row = cur_player.fetchone()

                    player.active_island = row["active_island"]
                    player.display_name = row["display_name"] or "New Player"

                    cur_player.execute("""
                        SELECT * FROM player_islands WHERE bbb_id = ?
                    """, (bbb_id,))
                    islands = cur_player.fetchall()
                    for islandData in islands:
                        island = Island(bbb_id, islandData["island_id"], islandData["user_island_id"])

                        island.likes = islandData["likes"]
                        island.dislikes = islandData["dislikes"]

                        island.add_player_monsters()
                        island.add_player_structures()
                        island.add_player_eggs()

                        player.add_island(island)                    
                else:
                    cur_player.execute("""
                        INSERT INTO player_islands (bbb_id, date_created, island_id)
                        VALUES (?, ?, ?)
                    """, (bbb_id, current_time_ms, 1))

                    db_player.commit()

                    user_island_id = cur_player.lastrowid

                    cur_player.execute("""
                        INSERT INTO players (
                            bbb_id,
                            active_island,
                            coins,
                            food,
                            diamonds,
                            shards,
                            xp,
                            level,
                            display_name,
                            last_login
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        bbb_id,
                        user_island_id, # active_island
                        5000,           # coins
                        0,              # food
                        20,             # diamonds
                        0,              # shards
                        0,              # xp
                        30,             # level
                        "New Player",
                        current_time_ms
                    ))

                    db_player.commit()

                    player.active_island = user_island_id

                    island = Island(bbb_id, 1, user_island_id)
                    island.create_structures()

                    player.add_island(island)

                query = "SELECT coins, diamonds, food, xp, level FROM players WHERE bbb_id = ?"
                cur_player.execute(query, (bbb_id,))
                row = cur_player.fetchone()

                player.coins = row["coins"]
                player.diamonds = row["diamonds"]
                player.food = row["food"]
                player.level = row["level"]
                player.xp = row["xp"]

                client.player = player

                initialized = SFSObject()
                initialized.put_long("bbb_id", bbb_id)

                CURRENT_PLAYERS += 1

                await send_extension_response(client, "gs_initialized", initialized)

                msg = SFSObject()
                msg.put_bool("force_logout", False)
                msg.put_utf_string("msg", f"Welcome to MSM Sandbox classic!\n\nOnline: ({CURRENT_PLAYERS}/{MAX_PLAYERS})")

                await send_extension_response(client, "gs_display_generic_message", msg)
            else:
                cmd = payload.get("c")
                print(cmd)
                if cmd == "db_gene":
                    response = SFSObject()
                    response.put_sfs_array("genes_data", DATA_CACHE["genes"])
                    response.put_long("server_time", current_time_ms)
                    response.put_long("last_updated", current_time_ms)

                    await send_extension_response(client, cmd, response)
                elif cmd == "db_island":
                    response = SFSObject()
                    response.put_sfs_array("islands_data", DATA_CACHE["islands"])
                    response.put_long("server_time", current_time_ms)
                    response.put_long("last_updated", current_time_ms)

                    await send_extension_response(client, cmd, response)
                elif cmd == "db_island_torches":
                    response = SFSObject()
                    response.put_sfs_array("island_torch_data", DATA_CACHE["torches"])
                    response.put_long("server_time", current_time_ms)
                    response.put_long("last_updated", current_time_ms)

                    await send_extension_response(client, cmd, response)
                elif cmd == "db_monster":
                    response = SFSObject()
                    response.put_sfs_array("monsters_data", DATA_CACHE["monsters"])
                    response.put_long("server_time", current_time_ms)
                    response.put_long("last_updated", current_time_ms)

                    await send_extension_response(client, cmd, response)
                elif cmd == "db_store":
                    store_items = SFSArray() #get_store_items()
                    store_groups = SFSArray()#get_store_groups()
                    store_currencys = SFSArray()#get_store_currencys()

                    response = SFSObject()
                    response.put_sfs_array("store_item_data", store_items)
                    response.put_sfs_array("store_group_data", store_groups)
                    response.put_sfs_array("store_currency_data", store_currencys)
                    response.put_long("server_time", current_time_ms)
                    response.put_long("last_updated", current_time_ms)

                    await send_extension_response(client, cmd, response)
                elif cmd == "db_structure":
                    response = SFSObject()
                    response.put_sfs_array("structures_data", DATA_CACHE["structures"])
                    response.put_long("server_time", current_time_ms)
                    response.put_long("last_updated", current_time_ms)
                        
                    await send_extension_response(client, cmd, response)
                elif cmd == "db_level":
                    response = SFSObject()
                    response.put_sfs_array("level_data", DATA_CACHE["levels"])
                    response.put_long("server_time", current_time_ms)
                    response.put_long("last_updated", current_time_ms)
                        
                    await send_extension_response(client, cmd, response)
                elif cmd == "db_scratch_offs":
                    response = SFSObject()
                    response.put_sfs_array("scratch_offs", DATA_CACHE["scratchoffs"])
                    response.put_long("server_time", current_time_ms)
                    response.put_long("last_updated", current_time_ms)
                        
                    await send_extension_response(client, cmd, response)
                elif cmd == "gs_promos":
                    response = SFSObject()

                    await send_extension_response(client, cmd, response)
                elif cmd == "gs_timed_events":
                    response = SFSObject()

                    response.put_sfs_array("timed_event_list", DATA_CACHE["timed_events"])
                    response.put_long("server_time", current_time_ms)
                    response.put_long("last_updated", current_time_ms)

                    await send_extension_response(client, cmd, response)
                elif cmd == "gs_quest":
                    response = SFSObject()
                    response.put_sfs_array("result", DATA_CACHE["quests"])
                    await send_extension_response(client, cmd, response)
                elif cmd == "gs_buy_island":
                    island_id = int(params.get("island_id"))
                    response = SFSObject()

                    if island_id == 0:
                        print("Whoops1")
                        response.put_bool("success", False)
                        response.put_utf_string("message", "Error")
                        await send_extension_response(client, cmd, response)
                        continue

                    cur_player.execute(
                        "SELECT * FROM player_islands WHERE bbb_id = ? AND island_id = ?",
                        (client.player.bbb_id, island_id)
                    )
                    existing = cur_player.fetchone()
                    if existing:
                        print("Whoops3")
                        response.put_bool("success", False)
                        response.put_utf_string("message", "Error")
                        await send_extension_response(client, cmd, response)
                        continue

                    cur.execute("SELECT * FROM islands WHERE island_id = ?", (island_id,))
                    island_row = cur.fetchone()
                    if not island_row:
                        print("Whoops")
                        response.put_bool("success", False)
                        response.put_utf_string("message", "Error")
                        await send_extension_response(client, cmd, response)
                        continue

                    cost_coins = island_row["cost_coins"]
                    cost_diamonds = island_row["cost_diamonds"]
                    if not client.player.add_properties(-cost_coins, -cost_diamonds, 0, 0):
                        response.put_bool("success", False)
                        response.put_utf_string("message", "Not enough resources")
                        await send_extension_response(client, cmd, response)
                        continue

                    cur_player.execute(
                        "INSERT INTO player_islands (bbb_id, date_created, island_id) VALUES (?, ?, ?)",
                        (client.player.bbb_id, current_time_ms, island_id)
                    )
                    db_player.commit()
                    user_island_id = cur_player.lastrowid

                    new_island = Island(client.player.bbb_id, island_id, user_island_id)
                    new_island.create_structures()
                    client.player.add_island(new_island)

                    response.put_bool("success", True)
                    response.put_sfs_array("properties", client.player.get_properties())
                    response.put_sfs_object("user_island", new_island.get_sfs_object())

                    await send_extension_response(client, cmd, response)
                elif cmd == "gs_change_island":
                    user_island_id = params.get("user_island_id")
                    bbb_id = client.player.bbb_id

                    response = SFSObject()

                    cur_player.execute(
                        "SELECT * FROM player_islands WHERE user_island_id = ? AND bbb_id = ?",
                        (user_island_id, bbb_id)
                    )
                    row = cur_player.fetchone()

                    if row:
                        cur_player.execute(
                            "UPDATE players SET active_island = ? WHERE bbb_id = ?",
                            (user_island_id, bbb_id)
                        )
                        db_player.commit()

                        client.player.active_island = user_island_id

                        response.put_bool("success", True)
                        response.put_long("user_island_id", user_island_id)
                    else:
                        response.put_bool("success", False)
                        response.put_utf_string("error", "You don't have this island")

                    hidden_objects = SFSObject()
                    hidden_objects.put_sfs_array("objects", SFSArray())
                    response.put_sfs_object("hidden_objects", hidden_objects)

                    await send_extension_response(client, cmd, response)
                elif cmd == "gs_buy_egg":
                    response = SFSObject()

                    monster_id = params.get("monster_id")

                    cur.execute("SELECT * FROM monsters WHERE monster_id = ?", (monster_id,))
                    row = cur.fetchone()

                    cur.execute("SELECT * FROM entities WHERE entity_id = ?", (row["entity"],))
                    row2 = cur.fetchone()

                    if buy_entity(client, row["entity"]) != True:
                        return

                    endtime = current_time_ms + (row2["build_time"] * 1000)

                    cur_player.execute(
                        "SELECT * FROM player_structures WHERE user_island_id = ? AND structure = 1",
                        (client.player.active_island,)
                    )

                    row = cur_player.fetchone()

                    if row is None:
                        print("Error")
                        response.put_bool("success", False)
                        response.put_utf_string("message", "Error")
                    else:
                        cur_player.execute(
                            "INSERT INTO player_eggs (user_island_id, laid_on, hatches_on, monster, user_structure_id) VALUES (?, ?, ?, ?, ?)",
                            (client.player.active_island, current_time_ms, endtime, monster_id, row["user_structure_id"])
                        )
                        db_player.commit()
                        user_egg_id = cur_player.lastrowid

                        egg = Egg(client.player.active_island, current_time_ms, endtime, monster_id, user_egg_id, row["user_structure_id"])

                        response.put_sfs_object("user_egg", egg.get_sfs_object())
                        response.put_bool("success", True)
                        response.put_bool("remove_buyback", False)
                        response.put_sfs_array("properties", client.player.get_properties())
                    print(response)
                    await send_extension_response(client, cmd, response)
                elif cmd == "gs_speed_up_hatching":
                    user_egg_id = params.get("user_egg_id")

                    cur_player.execute(
                        "SELECT * FROM player_eggs WHERE user_island_id = ? AND user_egg_id = ?",
                        (client.player.active_island, user_egg_id)
                    )
                    row = cur_player.fetchone()

                    if row is None:
                        response = SFSObject()
                        response.put_bool("success", False)
                        response.put_utf_string("message", "Error")
                        await send_extension_response(client, cmd, response)
                        return

                    response = SFSObject()

                    laid_on = row["laid_on"]
                    monster_id = row["monster"]

                    cur_player.execute(
                        "UPDATE player_eggs SET hatches_on = ? WHERE user_egg_id = ?",
                        (current_time_ms, user_egg_id)
                    )
                    db_player.commit()

                    response = SFSObject()
                    response.put_bool("success", True)
                    response.put_long("user_egg_id", user_egg_id)
                    response.put_long("hatches_on", current_time_ms)
                    response.put_long("laid_on", laid_on)
                    response.put_sfs_array("properties", client.player.get_properties())

                    await send_extension_response(client, cmd, response)
                elif cmd == "gs_hatch_egg":
                    pos_x = params.get("pos_x")
                    pos_y = params.get("pos_y")
                    flip = int(bool(params.get("flip")))
                    user_egg_id = params.get("user_egg_id")
                    response = SFSObject()

                    cur_player.execute(
                        "SELECT * FROM player_eggs WHERE user_island_id = ? AND user_egg_id = ?",
                        (client.player.active_island, user_egg_id)
                    )
                    row = cur_player.fetchone()

                    if row is None:
                        response.put_bool("success", False)
                        response.put_utf_string("message", "Error")
                        await send_extension_response(client, cmd, response)
                        return

                    monster_id = row["monster"]
                    user_structure_id = row["user_structure_id"]
                    
                    cur_player.execute(
                        "DELETE FROM player_eggs WHERE user_egg_id = ?",
                        (user_egg_id,)
                    )
                    db_player.commit()

                    cur_player.execute(
                        """
                        INSERT INTO player_monsters (
                            user_island_id,
                            pos_x,
                            pos_y,
                            flip,
                            level,
                            date_created,
                            monster,
                            last_collection
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            client.player.active_island,
                            pos_x,
                            pos_y,
                            flip,
                            1,
                            current_time_ms,
                            monster_id,
                            current_time_ms
                        )
                    )

                    db_player.commit()

                    cur_player.execute(
                        """
                        SELECT user_monster_id
                        FROM player_monsters
                        WHERE user_island_id = ?
                        ORDER BY user_monster_id DESC
                        LIMIT 1
                        """,
                        (client.player.active_island,)
                    )
                    monster_row = cur_player.fetchone()
                    user_monster_id = monster_row["user_monster_id"]

                    cur.execute("SELECT * FROM monsters WHERE monster_id = ?", (monster_id,))
                    monster_static = cur.fetchone()

                    cur.execute("SELECT xp FROM entities WHERE entity_id = ?", (monster_static["entity"],))
                    row2 = cur.fetchone()

                    client.player.add_properties(0, 0, 0, row2["xp"])

                    newMonster = Monster(client.player.active_island, user_monster_id, monster_id, pos_x, pos_y, flip, 1, 50, 0, 0, 1.0, current_time_ms, current_time_ms, 0)

                    response.put_sfs_array("properties", client.player.get_properties())
                    response.put_long("user_egg_id", user_egg_id)
                    response.put_long("island", client.player.active_island)
                    response.put_sfs_object("monster", newMonster.get_sfs_object())
                    response.put_bool("success", True)
                    response.put_bool("directPlace", False)
                    response.put_bool("remove_buyback", False)
                    response.put_long("user_structure_id", user_structure_id)

                    await send_extension_response(client, cmd, response)

                    plrisland = client.player.get_active_island()

                    plrisland.add_monster(newMonster)

                    player_response = SFSObject()
                    player_response.put_sfs_object("player_object", client.player.get_sfs_object())
                    player_response.put_long("server_time", current_time_ms)

                    await send_extension_response(client, "gs_player", player_response)
                elif cmd == "gs_buy_structure":
                    x = params.get("pos_x")
                    y = params.get("pos_y")
                    flip = params.get("flip")
                    scale = params.get("scale")
                    structure_id = params.get("structure_id")

                    cur.execute("SELECT * FROM structures WHERE structure_id = ?", (structure_id,))
                    row = cur.fetchone()

                    cur.execute("SELECT * FROM entities WHERE entity_id = ?", (row["entity"],))
                    row2 = cur.fetchone()

                    if buy_entity(client, row["entity"]) != True:
                        return

                    cur_player.execute("""
                        INSERT INTO player_structures (
                            user_island_id,
                            date_created,
                            pos_x,
                            pos_y,
                            flip,
                            muted,
                            is_complete,
                            is_upgrading,
                            structure,
                            scale,
                            building_completed,
                            last_collection,
                            obj_data,
                            obj_end
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        client.player.active_island,
                        current_time_ms,
                        x,
                        y,
                        flip,
                        0,
                        1,
                        0,
                        structure_id,
                        scale,
                        current_time_ms,
                        current_time_ms,
                        0,
                        0
                    ))

                    db_player.commit()

                    cur_player.execute("SELECT user_structure_id FROM player_structures WHERE user_island_id = ? AND pos_x = ? AND pos_y = ?", (client.player.active_island, x, y))
                    row = cur_player.fetchone()

                    newStructure = Structure(client.player.active_island, row["user_structure_id"], structure_id, x, y, flip, scale, current_time_ms, current_time_ms)

                    response = SFSObject()

                    response.put_bool("success", True)
                    response.put_sfs_array("properties", client.player.get_properties())
                    response.put_sfs_object("user_structure", newStructure.get_sfs_object())

                    await send_extension_response(client, cmd, response)
                elif cmd == "gs_mute_monster":
                    user_monster_id = params.get("user_monster_id")

                    cur_player.execute(
                        """
                        SELECT muted FROM player_monsters
                        WHERE user_monster_id = ? AND user_island_id = ?
                        """,
                        (user_monster_id, client.player.active_island)
                    )
                    row_muted = cur_player.fetchone()

                    muted = 0 if row_muted["muted"] == 1 else 1

                    response = SFSObject()

                    cur_player.execute(
                        """
                        UPDATE player_monsters
                        SET muted = ?
                        WHERE user_monster_id = ? AND user_island_id = ?
                        """,
                        (muted, user_monster_id, client.player.active_island)
                    )
                    db_player.commit()

                    cur_player.execute(
                        """
                        SELECT * FROM player_monsters
                        WHERE user_monster_id = ? AND user_island_id = ?
                        """,
                        (user_monster_id, client.player.active_island)
                    )
                    monster_row = cur_player.fetchone()

                    updatedMonster = Monster(
                        client.player.active_island,
                        user_monster_id,
                        monster_row["monster"],
                        monster_row["pos_x"],
                        monster_row["pos_y"],
                        monster_row["flip"],
                        monster_row["level"],
                        monster_row["happiness"],
                        monster_row["collected_coins"],
                        monster_row["times_fed"],
                        monster_row["volume"],
                        monster_row["date_created"],
                        monster_row["last_collection"],
                        muted
                    )

                    response.put_bool("success", True)
                    response.put_long("user_monster_id", user_monster_id)
                    response.put_sfs_object("monster", updatedMonster.get_sfs_object())
                    response.put_int("muted", muted)

                    response2 = SFSObject()
                    response2.put_bool("success", True)

                    await send_extension_response(client, cmd, response2)

                    await send_extension_response(client, "gs_update_monster", response)
                elif cmd == "gs_referral_request":
                    code = str(params.get("referring_bbb_id"))

                    response = SFSObject()

                    if code == "132026":
                        worked = client.player.add_properties(999_999_999, 999_999_999, 999_999_999, 0)

                        response.put_bool("success", True)
                        response.put_sfs_array("properties", client.player.get_properties())

                        await send_extension_response(client, "gs_update_properties", response)
                elif cmd == "gs_memory_minigame_current_cost":
                    diamonds = 2
                    coins = 0

                    response = SFSObject()
                    response.put_int("diamond_cost", diamonds)
                    response.put_int("coin_cost", coins)
                    response.put_bool("success", True)

                    await send_extension_response(client, cmd, response)
                elif cmd == "gs_get_memory_game_numbers":
                    response = SFSObject()
                    
                    response.put_int("memoryGameAudioSampleNumber", 100)  # MEMORY_AUDIO_SAMPLE_NUM
                    response.put_float("toneDuration", 2.0)               # MEMORY_TONE_DURATION
                    response.put_float("startGamePauseDuration", 2.0)     # MEMORY_START_GAME_PAUSE_DURATION
                    response.put_float("startSeqPauseDuration", 0.0)      # MEMORY_START_SEQ_PAUSE_DURATION
                    response.put_float("postNotePauseDuration", 0.0)      # MEMORY_POST_NOTE_PAUSE_DURATION
                    response.put_float("postSwapPauseDuration", 0.5)      # MEMORY_POST_SWAP_PAUSE_DURATION
                    response.put_float("failPauseDuration", 1.0)          # MEMORY_FAIL_PAUSE_DURATION
                    
                    # Swap / double tap settings
                    response.put_int("swapBeginStep", -1)                 # MEMORY_SWAP_BEGIN_STEP
                    response.put_float("monsterSwapChance", 0.5)         # MEMORY_MONSTER_SWAP_CHANCE
                    response.put_int("stepDurationOfSwap", 1)            # MEMORY_STEP_DURATION_OF_SWAP
                    response.put_float("swapAnimationSpeed", 5000.0)     # MEMORY_SWAP_ANIM_SPEED
                    response.put_int("doubleTapBeginStep", 10)           # MEMORY_DOUBLE_TAP_BEGIN_STEP
                    response.put_float("doubleTapChance", 0.5)           # MEMORY_DOUBLE_TAP_CHANCE
                    
                    # Tier response levels
                    response.put_int("tier1ResponseLevel", 5)            # MEMORY_TIER1_RESPONSE_LVL
                    response.put_int("tier2ResponseLevel", 10)           # MEMORY_TIER2_RESPONSE_LVL
                    response.put_int("tier3ResponseLevel", 20)           # MEMORY_TIER3_RESPONSE_LVL
                    response.put_int("tier4ResponseLevel", 50)           # MEMORY_TIER4_RESPONSE_LVL
                    
                    # Tone duration mode (fixed or animation-based)
                    response.put_int("fixedToneDuration", 0)             # MEMORY_FIXED_TONE_DURATION
                    
                    # Rewards / pricing (optional but in table)
                    response.put_int("diamondPrice", 2)                  # MEMORY_DIAMOND_PRICE
                    response.put_int("coinPrice", 0)                     # MEMORY_COIN_PRICE
                    response.put_int("diamondReward", 1)                # MEMORY_DIAMOND_REWARD
                    response.put_int("coinReward", 25)                  # MEMORY_COIN_REWARD
                    response.put_int("foodReward", 50)                  # MEMORY_FOOD_REWARD
                    
                    # Reward frequencies
                    response.put_int("coinRewardFreq", 1)               # MEMORY_COIN_REWARD_FREQ
                    response.put_int("foodRewardFreq", 5)               # MEMORY_FOOD_REWARD_FREQ
                    response.put_int("diamondRewardFreq", 1)            # MEMORY_DIAMOND_REWARD_FREQ
                    
                    # Timing before fail
                    response.put_float("timeBeforeFail", 5.0)           # MEMORY_TIME_BEFORE_FAIL

                    response.put_int("prev_highscore", 1200)
                    response.put_int("topscore", 4500)

                    await send_extension_response(client, cmd, response)
                elif cmd == "gs_collect_daily_reward":
                    response = SFSObject()

                    response.put_sfs_array("properties", client.player.get_properties())

                    await send_extension_response(client, cmd, response)
                elif cmd == "gs_player_has_scratch_off":
                    response = SFSObject()

                    response.put_bool("success", False)
                    #response.put_utf_string("type", params.get("type"))

                    await send_extension_response(client, cmd, response)
                elif cmd == "gs_play_scratch_off" or cmd == "gs_purchase_scratch_off":
                    response = SFSObject()

                    response.put_bool("success", False)
                    ticket = SFSObject()
                    ticket.put_int("id", 9)
                    ticket.put_utf_string("type", "C")
                    ticket.put_int("amount", 1000)
                    ticket.put_utf_string("prize", "diamonds")

                    scaled_prizes = SFSObject()
                    scaled_prizes.put_int("tier1", 50)
                    scaled_prizes.put_int("tier2", 100)
                    scaled_prizes.put_int("tier3", 200)

                    response.put_sfs_object("ticket", ticket)
                    response.put_sfs_object("scaled_prizes", scaled_prizes)
                    response.put_sfs_array("properties", client.player.get_properties())

                    await send_extension_response(client, cmd, response)
                elif cmd == "gs_move_monster":
                    user_monster_id = params.get("user_monster_id")
                    new_x = params.get("pos_x")
                    new_y = params.get("pos_y")

                    response = SFSObject()

                    cur_player.execute(
                        """
                        UPDATE player_monsters
                        SET pos_x = ?, pos_y = ?
                        WHERE user_monster_id = ? AND user_island_id = ?
                        """,
                        (new_x, new_y, user_monster_id, client.player.active_island)
                    )
                    db_player.commit()

                    cur_player.execute(
                        """
                        SELECT * FROM player_monsters
                        WHERE user_monster_id = ? AND user_island_id = ?
                        """,
                        (user_monster_id, client.player.active_island)
                    )
                    monster_row = cur_player.fetchone()

                    if not monster_row:
                        response.put_bool("success", False)
                        response.put_utf_string("error", "Invalid monster ID")
                        await send_extension_response(client, cmd, response)
                        continue

                    updatedMonster = Monster(
                        client.player.active_island,
                        user_monster_id,
                        monster_row["monster"],
                        new_x,
                        new_y,
                        monster_row["flip"],
                        monster_row["level"],
                        monster_row["happiness"],
                        monster_row["collected_coins"],
                        monster_row["times_fed"],
                        monster_row["volume"],
                        monster_row["date_created"],
                        monster_row["last_collection"],
                        monster_row["muted"]
                    )

                    response.put_bool("success", True)
                    response.put_long("user_monster_id", user_monster_id)
                    response.put_sfs_object("monster", updatedMonster.get_sfs_object())
                    response.put_int("pos_x", new_x)
                    response.put_int("pos_y", new_y)

                    response2 = SFSObject()
                    response2.put_bool("success", True)

                    await send_extension_response(client, cmd, response2)

                    await send_extension_response(client, "gs_update_monster", response)
                elif cmd == "gs_feed_monster":
                    user_monster_id = params.get("user_monster_id")
                    response = SFSObject()

                    cur_player.execute(
                        "SELECT * FROM player_monsters WHERE user_monster_id = ? AND user_island_id = ?",
                        (user_monster_id, client.player.active_island)
                    )
                    monster_row = cur_player.fetchone()

                    if not monster_row:
                        response.put_bool("success", False)
                        response.put_utf_string("error", "Invalid monster ID")
                        await send_extension_response(client, cmd, response)
                        continue

                    monster_id = monster_row["monster"]
                    current_level = monster_row["level"]

                    cur.execute(
                        "SELECT * FROM monster_levels WHERE monster = ? AND level = ?",
                        (monster_id, current_level)
                    )
                    mlevel = cur.fetchone()

                    if not mlevel:
                        response.put_bool("success", False)
                        response.put_utf_string("error", "Monster level data not found")
                        await send_extension_response(client, cmd, response)
                        continue

                    food_needed = mlevel["food"]

                    success = client.player.add_properties(0, 0, -food_needed, 0)
                    if not success:
                        response.put_bool("success", False)
                        response.put_utf_string("error", "Not enough food")
                        await send_extension_response(client, cmd, response)
                        continue

                    times_fed = (monster_row["times_fed"] or 0) + 1
                    new_level = monster_row["level"]

                    if times_fed >= 4:
                        times_fed = 0
                        new_level += 1

                        cur.execute(
                            "SELECT * FROM monster_levels WHERE monster = ? AND level = ?",
                            (monster_id, new_level)
                        )
                        next_level_data = cur.fetchone()
                        if not next_level_data:
                            new_level -= 1
                            times_fed = 4

                    cur_player.execute(
                        "UPDATE player_monsters SET times_fed = ?, level = ? WHERE user_monster_id = ?",
                        (times_fed, new_level, user_monster_id)
                    )
                    db_player.commit()

                    response = SFSObject()
                    response.put_bool("success", True)
                    await send_extension_response(client, cmd, response)

                    monster_obj = Monster(
                        client.player.active_island,
                        user_monster_id,
                        monster_id,
                        monster_row["pos_x"],
                        monster_row["pos_y"],
                        monster_row["flip"],
                        new_level,
                        100,
                        monster_row["collected_coins"],
                        times_fed,
                        monster_row["volume"],
                        monster_row["date_created"],
                        monster_row["last_collection"],
                        monster_row["muted"]
                    )

                    response2 = SFSObject()
                    response2.put_bool("success", True)
                    response2.put_long("user_monster_id", user_monster_id)
                    response2.put_int("times_fed", times_fed)
                    response2.put_int("level", new_level)
                    response2.put_sfs_object("monster", monster_obj.get_sfs_object())
                    await send_extension_response(client, "gs_update_monster", response2)

                    response3 = SFSObject()
                    response3.put_bool("success", True)
                    response3.put_sfs_array("properties", client.player.get_properties())
                    await send_extension_response(client, "gs_update_properties", response3)
                elif cmd == "gs_mega_monster_message":
                    user_monster_id = params.get("user_monster_id")
                    permanent = params.get("permanent")
                    cost = 20 if permanent else 2
                    duration_ms = 60 * 60 * 24 * 1000

                    cur_player.execute(
                        "DELETE FROM monster_mega_data WHERE finishes_at < ?",
                        (current_time_ms,)
                    )
                    db_player.commit()

                    cur_player.execute(
                        "SELECT * FROM monster_mega_data WHERE user_monster_id = ?",
                        (user_monster_id,)
                    )
                    existing_mega_data = cur_player.fetchone()

                    if existing_mega_data:
                            finishes_at = existing_mega_data["finishes_at"] or 0
                            permamega = existing_mega_data["permamega"]
                            currently_mega = existing_mega_data["currently_mega"]

                            if permamega or finishes_at > current_time_ms:
                                new_mega = 0 if currently_mega else 1
                                cur_player.execute(
                                    "UPDATE monster_mega_data SET currently_mega = ? WHERE user_monster_id = ?",
                                    (new_mega, user_monster_id)
                                )
                                db_player.commit()

                                response2 = SFSObject()
                                response2.put_bool("success", True)
                                response2.put_sfs_array("properties", client.player.get_properties())
                                response2.put_long("user_monster_id", user_monster_id)

                                if new_mega == 0:
                                    megamonster_data = MegaData(
                                        user_monster_id,
                                        permamega,
                                        False,
                                        existing_mega_data["started_at"],
                                        existing_mega_data["finishes_at"]
                                    )
                                    response2.put_sfs_object("megamonster", megamonster_data.get_sfs_object())
                                else:
                                    megamonster_data = MegaData(
                                        user_monster_id,
                                        permamega,
                                        True,
                                        existing_mega_data["started_at"],
                                        existing_mega_data["finishes_at"]
                                    )
                                    response2.put_sfs_object("megamonster", megamonster_data.get_sfs_object())

                                response = SFSObject()
                                response.put_bool("success", True)
                                response.put_long("user_monster_id", user_monster_id)

                                await send_extension_response(client, cmd, response)
                                await send_extension_response(client, "gs_update_monster", response2)
                                return

                    purchase = not existing_mega_data or (existing_mega_data["finishes_at"] or 0) < current_time_ms

                    end_time = current_time_ms + duration_ms if not permanent else None

                    if purchase and client.player.add_properties(0, -cost, 0, 0) != True:
                        return

                    if purchase:
                        if permanent:
                            cur_player.execute(
                                """
                                INSERT INTO monster_mega_data (user_monster_id, permamega, currently_mega)
                                VALUES (?, ?, ?)
                                ON CONFLICT(user_monster_id) DO UPDATE SET permamega=excluded.permamega
                                """,
                                (user_monster_id, 1, 1)
                            )
                        else:
                            cur_player.execute(
                                """
                                INSERT INTO monster_mega_data (user_monster_id, started_at, finishes_at, permamega, currently_mega)
                                VALUES (?, ?, ?, ?, ?)
                                ON CONFLICT(user_monster_id) DO UPDATE SET started_at=excluded.started_at,
                                                                        finishes_at=excluded.finishes_at,
                                                                        permamega=0,
                                                                        currently_mega=0
                                """,
                                (user_monster_id, current_time_ms, end_time, 0, 1)
                            )

                    db_player.commit()

                    response2 = SFSObject()
                    response2.put_bool("success", True)
                    response2.put_sfs_array("properties", client.player.get_properties())
                    response2.put_long("user_monster_id", user_monster_id)

                    megamonster_data = MegaData(user_monster_id, permanent, True, current_time_ms if not permanent else None, end_time if not permanent else None)
                    response2.put_sfs_object("megamonster", megamonster_data.get_sfs_object())

                    response = SFSObject()
                    response.put_bool("success", True)
                    response.put_long("user_monster_id", user_monster_id)

                    await send_extension_response(client, cmd, response)
                    await send_extension_response(client, "gs_update_monster", response2)
                elif cmd == "gs_sell_monster":
                    user_monster_id = params.get("user_monster_id")

                    cur_player.execute(
                        """
                        SELECT monster FROM player_monsters
                        WHERE user_monster_id = ? AND user_island_id = ?
                        """,
                        (user_monster_id, client.player.active_island)
                    )

                    monster_id = cur_player.fetchone()["monster"]

                    cur.execute("SELECT * FROM monsters WHERE monster_id = ?", (monster_id,))
                    row = cur.fetchone()

                    sell_entity(client, row["entity"])

                    cur_player.execute(
                        """
                        DELETE FROM player_monsters
                        WHERE user_monster_id = ? AND user_island_id = ?
                        """,
                        (user_monster_id, client.player.active_island)
                    )
                    db_player.commit()

                    response = SFSObject()
                    response.put_bool("success", True)
                    response.put_long("user_monster_id", user_monster_id)
                    response.put_sfs_array("properties", client.player.get_properties())

                    await send_extension_response(client, cmd, response)
                elif cmd == "gs_sell_structure":
                    user_structure_id = params.get("user_structure_id")

                    cur_player.execute(
                        """
                        SELECT structure FROM player_structures
                        WHERE user_structure_id = ? AND user_island_id = ?
                        """,
                        (user_structure_id, client.player.active_island)
                    )
                    structure_id = cur_player.fetchone()["structure"]

                    cur.execute("SELECT * FROM structures WHERE structure_id = ?", (structure_id,))
                    row = cur.fetchone()

                    sell_entity(client, row["entity"])

                    cur_player.execute(
                        """
                        DELETE FROM player_structures
                        WHERE user_structure_id = ? AND user_island_id = ?
                        """,
                        (user_structure_id, client.player.active_island)
                    )
                    db_player.commit()

                    response = SFSObject()
                    response.put_bool("success", True)
                    response.put_long("user_structure_id", user_structure_id)
                    response.put_sfs_array("properties", client.player.get_properties())

                    await send_extension_response(client, cmd, response)
                elif cmd == "gs_move_structure":
                    user_structure_id = params.get("user_structure_id")
                    new_x = params.get("pos_x")
                    new_y = params.get("pos_y")
                    scale = params.get("scale")

                    cur_player.execute(
                        "UPDATE player_structures SET pos_x = ?, pos_y = ? WHERE user_structure_id = ? AND user_island_id = ?",
                        (new_x, new_y, user_structure_id, client.player.active_island)
                    )
                    db_player.commit()

                    response = SFSObject()

                    properties = client.player.get_properties()

                    cur_player.execute(
                        "SELECT * FROM player_structures WHERE user_structure_id = ? AND user_island_id = ?",
                        (user_structure_id, client.player.active_island)
                    )
                    row = cur_player.fetchone()

                    structure_id = row["structure"]
                    flip = row["flip"]
                    date_created = row["date_created"]
                    last_collection = row["last_collection"]

                    newStructure = Structure(client.player.active_island, user_structure_id, structure_id, new_x, new_y, flip, scale, date_created, last_collection)
                    prop = SFSObject()
                    prop.put_int("pos_x", new_x)
                    properties.add_sfs_object(prop)

                    prop = SFSObject()
                    prop.put_int("pos_y", new_y)
                    properties.add_sfs_object(prop)

                    prop = SFSObject()
                    prop.put_double("scale", scale)
                    properties.add_sfs_object(prop)

                    response.put_sfs_array("properties", properties)

                    response.put_long("user_structure_id", user_structure_id)
                    response.put_sfs_object("user_structure", newStructure.get_sfs_object())
                    response.put_bool("success", True)
                    await send_extension_response(client, cmd, response)
                elif cmd == "gs_flip_structure":
                    user_structure_id = params.get("user_structure_id")

                    cur_player.execute(
                        "SELECT * FROM player_structures WHERE user_structure_id = ? AND user_island_id = ?",
                        (user_structure_id, client.player.active_island)
                    )
                    row = cur_player.fetchone()

                    response = SFSObject()
                    if not row:
                        response.put_bool("success", False)
                        response.put_utf_string("error", "Invalid structure ID")
                        await send_extension_response(client, cmd, response)
                        return

                    new_flip = 0 if row["flip"] else 1

                    cur_player.execute(
                        "UPDATE player_structures SET flip = ? WHERE user_structure_id = ? AND user_island_id = ?",
                        (new_flip, user_structure_id, client.player.active_island)
                    )
                    db_player.commit()

                    newStructure = Structure(
                        client.player.active_island,
                        user_structure_id,
                        row["structure"],
                        row["pos_x"],
                        row["pos_y"],
                        new_flip,
                        row["scale"],
                        row["date_created"],
                        row["last_collection"]
                    )

                    flip_resp = SFSObject()
                    flip_resp.put_bool("success", True)
                    await send_extension_response(client, "gs_flip_structure", flip_resp)

                    props = SFSArray()
                    props.add_sfs_object(SFSObject().put_int("flip", new_flip))

                    update_resp = SFSObject()
                    update_resp.put_long("user_structure_id", user_structure_id)
                    update_resp.put_sfs_object("user_structure", newStructure.get_sfs_object())
                    update_resp.put_sfs_array("properties", props)
                    update_resp.put_bool("success", True)
                    await send_extension_response(client, "gs_update_structure", update_resp)
                elif cmd == "gs_flip_monster":
                    user_monster_id = params.get("user_monster_id")
                    flipped = params.get("flipped")

                    response = SFSObject()

                    cur_player.execute(
                        """
                        SELECT * FROM player_monsters
                        WHERE user_monster_id = ? AND user_island_id = ?
                        """,
                        (user_monster_id, client.player.active_island)
                    )
                    monster_row = cur_player.fetchone()

                    if not monster_row:
                        response.put_bool("success", False)
                        response.put_utf_string("error", "Invalid monster ID")
                        await send_extension_response(client, cmd, response)
                        continue

                    if flipped is not None:
                        new_flip = 1 if flipped else 0
                    else:
                        new_flip = 0 if monster_row["flip"] else 1

                    cur_player.execute(
                        """
                        UPDATE player_monsters
                        SET flip = ?
                        WHERE user_monster_id = ? AND user_island_id = ?
                        """,
                        (new_flip, user_monster_id, client.player.active_island)
                    )
                    db_player.commit()

                    updatedMonster = Monster(
                        client.player.active_island,
                        user_monster_id,
                        monster_row["monster"],
                        monster_row["pos_x"],
                        monster_row["pos_y"],
                        new_flip,
                        monster_row["level"],
                        monster_row["happiness"],
                        monster_row["collected_coins"],
                        monster_row["times_fed"],
                        monster_row["volume"],
                        monster_row["date_created"],
                        monster_row["last_collection"],
                        monster_row["muted"]
                    )

                    flip_resp = SFSObject()
                    flip_resp.put_bool("success", True)
                    await send_extension_response(client, "gs_flip_monster", flip_resp)

                    update_resp = SFSObject()
                    update_resp.put_bool("success", True)
                    update_resp.put_long("user_monster_id", user_monster_id)
                    update_resp.put_int("flip", new_flip)
                    update_resp.put_sfs_object("monster", updatedMonster.get_sfs_object())
                    await send_extension_response(client, "gs_update_monster", update_resp)
                elif cmd == "gs_collect_scratch_off":
                    response = SFSObject()

                    response.put_bool("success", True)
                    response.put_sfs_array("properties", client.player.get_properties())

                    await send_extension_response(client, cmd, response)
                elif cmd == "gs_name_monster":
                    msg = SFSObject()
                    msg.put_bool("force_logout", True)
                    msg.put_utf_string("msg", "go fuck yourself\n\nXOXO: RiotLove")

                    await send_extension_response(client, "gs_display_generic_message", msg)
                elif cmd == "gs_get_torchgifts":
                    response = SFSObject()
                    
                    response.put_bool("success", True)
                    
                    response.put_sfs_array("torch_gifts", SFSArray())
                    
                    properties_array = SFSArray()
                    prop = SFSObject()

                    prop.put_sfs_array("can_gift_torch_times", SFSArray())
                    properties_array.add_sfs_object(prop)
                    
                    response.put_sfs_array("properties", properties_array)

                    await send_extension_response(client, cmd, response)
                elif cmd == "gs_player":
                    response = SFSObject()

                    response.put_sfs_object("player_object", client.player.get_sfs_object())

                    print(response)

                    await send_extension_response(client, cmd, response)
                else:
                
                    response = SFSObject()

                    print(params)

                    await send_extension_response(client, cmd, response)
    except Exception as e:
        print(f"Error with client {client.host}:{client.port}: {e}")
        traceback.print_exc()
    finally:
        CURRENT_PLAYERS -= 1
        print(f"Client {client.host}:{client.port} disconnected")

async def run_server(ip: str, port: int):
    print(f"Began server at {ip}:{port}")
    async for client in server_from_url(f"tcp://{ip}:{port}"):
        print(f"New client connected: {client.host}:{client.port}")
        asyncio.create_task(handle_client(client))

if __name__ == "__main__":
    load_static_data()
    asyncio.run(run_server(GAME_SERVER_IP, 9933))