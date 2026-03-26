from sfs2x.core import SFSObject, SFSArray
import time
import sqlite3
import json
import random 

conn = sqlite3.connect("static_dbs.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

skip_monster_ids = [30, 79, 80]
skip_structure_ids = [232,233,234,235,236]

def get_genes():
    genes = SFSArray()

    cur.execute("SELECT * FROM genes")
    rows = cur.fetchall()

    current_time_ms = int(time.time()) * 1000

    for row in rows:
        gene = SFSObject()

        gene.put_utf_string("gene_letter", row["gene_letter"])
        gene.put_utf_string("gene_graphic", row["gene_graphic"])
        gene.put_utf_string("min_server_version", row["min_server_version"])
        gene.put_int("gene_id", row["gene_id"])
        gene.put_long("last_changed", current_time_ms)

        genes.add_sfs_object(gene)

    return genes

def get_quests():
    quests = SFSArray()

    cur.execute("SELECT * FROM quests")
    rows = cur.fetchall()

    current_time_ms = int(time.time() * 1000)

    for row in rows:
        quest = SFSObject()

        quest.put_int("id", row["id"])
        quest.put_int("quest_id", row["id"])
        quest.put_utf_string("name", row["name"])
        quest.put_utf_string("description", row["description"])
        quest.put_utf_string("type", row["type"])
        quest.put_utf_string("min_server_version", row["min_server_version"])
        quest.put_long("last_changed", current_time_ms)

        # --- GOALS ---
        goals_array = SFSArray()
        goals_data = json.loads(row["goals"]) if row["goals"] else []

        for g in goals_data:
            goal = SFSObject()
            for k, v in g.items():
                # Convert stringified lists to SFSArray of Ints
                if isinstance(v, str) and v.startswith("[") and v.endswith("]"):
                    try:
                        arr = json.loads(v)
                        sfs_arr = SFSArray()
                        for item in arr:
                            if isinstance(item, int):
                                sfs_arr.add_int(item)
                            else:
                                sfs_arr.add_utf_string(str(item))
                        goal.put_sfs_array(k, sfs_arr)
                    except Exception:
                        goal.put_utf_string(k, v)  # fallback if parsing fails
                elif isinstance(v, int):
                    goal.put_int(k, v)
                elif isinstance(v, float):
                    goal.put_double(k, v)
                else:
                    goal.put_utf_string(k, str(v))
            goals_array.add_sfs_object(goal)

        quest.put_sfs_array("goals", goals_array)

        # --- REWARDS ---
        rewards = SFSObject()
        rewards_data = json.loads(row["rewards"]) if row["rewards"] else []

        for reward_dict in rewards_data:
            if isinstance(reward_dict, dict):
                for k, v in reward_dict.items():
                    if isinstance(v, int):
                        rewards.put_int(k, v)
                    elif isinstance(v, float):
                        rewards.put_double(k, v)
                    else:
                        rewards.put_utf_string(k, str(v))

        quest.put_sfs_object("rewards", rewards)

        # --- NEXT ---
        next_array = SFSArray()
        next_data = json.loads(row["next"]) if row["next"] else []
        for n in next_data:
            if isinstance(n, int):
                next_array.add_int(n)
            else:
                next_array.add_utf_string(str(n))
        quest.put_sfs_array("next", next_array)

        quests.add_sfs_object(quest)

    return quests

def get_islands():
    islands = SFSArray()

    cur.execute("SELECT * FROM islands")
    rows = cur.fetchall()

    current_time_ms = int(time.time()) * 1000

    for row in rows:
        island = SFSObject()
        island_id = row["island_id"]

        # basic info
        island.put_int("id", island_id)
        island.put_int("island_id", island_id)
        island.put_int("island_type", island_id)
        island.put_utf_string("name", row["name"])
        island.put_utf_string("description", row["description"])
        island.put_utf_string("genes", row["genes"])
        island.put_utf_string("midi", row["midi"])
        island.put_utf_string("min_server_version", row["min_server_version"])

        island.put_long("last_changed", current_time_ms)

        island.put_utf_string("fb_object_id", "")

        # status
        island.put_int("enabled", 1)

        # costs / level
        island.put_int("level", row["level"])
        island.put_int("cost_coins", row["cost_coins"])
        island.put_int("cost_diamonds", row["cost_diamonds"])

        # castle
        island.put_int("castle_structure_id", row["castle_structure_id"])

        # remix links
        island.put_utf_string("remix_url", row["remix_url"])
        island.put_utf_string("remix_url_2", row["remix_url_2"])

        # ----------------
        # GRAPHIC
        # ----------------
        graphic_data = json.loads(row["graphic"])
        graphic = SFSObject()
        graphic.put_utf_string("file", graphic_data["file"])
        graphic.put_utf_string("tileset", graphic_data["tileset"])
        graphic.put_utf_string("grid", "main_grid.bin")
        island.put_sfs_object("graphic", graphic)

        # ----------------
        # MONSTERS
        # ----------------
        monsters = SFSArray()

        cur.execute("SELECT * FROM island_monsters WHERE island = ?", (island_id,))
        monster_rows = cur.fetchall()

        for m in monster_rows:
            if m["monster"] in skip_monster_ids:
                continue
            mo = SFSObject()
            mo.put_int("monster", m["monster"])
            mo.put_utf_string("instrument", m["instrument"])
            monsters.add_sfs_object(mo)

        island.put_sfs_array("monsters", monsters)

        # ----------------
        # STRUCTURES
        # ----------------
        structures = SFSArray()

        cur.execute("SELECT * FROM island_structures WHERE island = ?", (island_id,))
        structure_rows = cur.fetchall()

        for s in structure_rows:
            so = SFSObject()
            so.put_int("structure", s["structure"])
            so.put_utf_string("instrument", s["instrument"])
            structures.add_sfs_object(so)

        island.put_sfs_array("structures", structures)

        islands.add_sfs_object(island)

    return islands

def get_structures():
    structures = SFSArray()

    cur.execute("SELECT * FROM structures")
    rows = cur.fetchall()

    current_time_ms = int(time.time()) * 1000

    for row in rows:
        if row["structure_id"] in skip_structure_ids:
            continue

        structure = SFSObject()

        # identifiers
        structure.put_int("structure_id", row["structure_id"])
        structure.put_int("id", row["structure_id"])
        structure.put_int("entity_id", row["entity"])
        structure.put_utf_string("structure_type", row["structure_type"])

        # upgrade chain
        structure.put_int("upgrades_to", row["upgrades_to"])

        # sound
        structure.put_utf_string("sound", row["sound"])

        structure.put_long("last_changed", current_time_ms)

        # island restriction
        structure.put_int("limit_to_island", row["limit_to_island"])

        # extra data
        extra = SFSObject()
        if row["extra"]:
            extra_data = json.loads(row["extra"])
            for k, v in extra_data.items():
                if k == "beds":
                    v = 999
                if isinstance(v, int):
                    extra.put_int(k, v)
                elif isinstance(v, float):
                    extra.put_double(k, v)
                else:
                    extra.put_utf_string(k, str(v))

        structure.put_sfs_object("extra", extra)

        # ---------------------------
        # ENTITY LOOKUP
        # ---------------------------
        cur.execute("SELECT * FROM entities WHERE entity_id = ?", (row["entity"],))
        entity = cur.fetchone()

        if entity:
            structure.put_utf_string("entity_type", entity["entity_type"])
            structure.put_utf_string("name", entity["name"])
            structure.put_utf_string("description", entity["description"])
            structure.put_utf_string("keywords", entity["keywords"] or "[]")
            graphic_data = json.loads(entity["graphic"])
            graphic = SFSObject()
            for key, value in graphic_data.items():
                graphic.put_utf_string(key, str(value))
            structure.put_sfs_object("graphic", graphic)

            structure.put_int("size_x", entity["size_x"])
            structure.put_int("size_y", entity["size_y"])

            structure.put_int("cost_coins", entity["cost_coins"])
            structure.put_int("cost_eth_currency", entity["cost_eth_currency"])
            structure.put_int("cost_diamonds", entity["cost_diamonds"])
            structure.put_int("cost_sale", entity["cost_sale"])

            structure.put_int("buildTime", entity["build_time"])
            structure.put_int("level", entity["level"])

            requirements_array = SFSArray()
            for req in json.loads(entity["requirements"]):
                r = SFSObject()
                for k, v in req.items():
                    r.put_int(k, v)
                requirements_array.add_sfs_object(r)
            structure.put_sfs_array("requirements", requirements_array)

            structure.put_int("movable", entity["movable"])
            structure.put_int("xp", entity["xp"])
            structure.put_int("y_offset", entity["y_offset"])

            structure.put_int("view_in_market", entity["view_in_market"])
            structure.put_int("premium", entity["premium"])

            structure.put_utf_string("min_server_version", entity["min_server_version"])

        structures.add_sfs_object(structure)

    return structures

bbs_urls = {
    "BBS 1: Found You!": "https://www.youtube.com/watch?v=LBGxp0tVfcc",
    "BBS 2: Dodge or die!": "https://www.youtube.com/watch?v=gkdlsbMgyjA",
    "BBS 3: We will Escape.": "https://www.youtube.com/watch?v=FrVFegLNZGg",
    "BBS 4: Mayday! Going Down!": "https://www.youtube.com/watch?v=pdcPSe0qDGE",
    "BBS 10b: Theft and Bakery": "https://www.youtube.com/watch?v=dnGjugGffO4",
    "BBS 11: Up, up and away!": "https://www.youtube.com/watch?v=iNuC_uSYnDc"
}

extra_monsters = [

]

'''
    {
        # --- MONSTER TABLE ---
        "monster_id": 9991,
        "entity": 101,
        "genes": "abc123",
        "beds": 2,
        "happiness": [],
        "names": ["Testy", "Debuggo"],
        "level_up_xp": 50,
        "levelup_island": "starter",
        "link_title": "",
        "link_address": "",

        # --- ENTITY TABLE ---
        "entity_data": {
            "entity_type": "monster",
            "name": "Test Monster",
            "description": "A debug creature.",
            "keywords": "test,debug",

            "graphic": {
                "idle": "test_idle",
                "icon": "test_icon"
            },

            "size_x": 1,
            "size_y": 1,

            "cost_coins": 100,
            "cost_eth_currency": 0,
            "cost_diamonds": 0,
            "cost_sale": 0,

            "build_time": 5,
            "level": 1,

            "requirements": [],

            "movable": 1,
            "xp": 10,
            "y_offset": 0,

            "view_in_market": 1,
            "premium": 0,

            "min_server_version": "1.0"
        },

        # --- LEVELS TABLE ---
        "levels": [
            {
                "max_coins": 100,
                "coins": 10,
                "level": 1,
                "monster_level_id": 1,
                "food": 5,
                "ethereal_currency": 0,
                "max_ethereal": 0
            },
            {
                "max_coins": 200,
                "coins": 20,
                "level": 2,
                "monster_level_id": 2,
                "food": 10,
                "ethereal_currency": 0,
                "max_ethereal": 0
            }
        ],

        "is_extra": True
    }
'''

def get_monsters():
    monsters = SFSArray()

    # --- DB monsters ---
    cur.execute("SELECT * FROM monsters")
    rows = cur.fetchall()

    # convert each tuple row into a dict
    db_rows = [dict(zip([col[0] for col in cur.description], r)) for r in rows]

    # merge with extra monsters (empty list works fine)
    all_rows = db_rows + extra_monsters

    current_time_ms = int(time.time()) * 1000

    for row in all_rows:
        monster = SFSObject()

        if row["monster_id"] in skip_monster_ids:
            continue

        is_extra = row.get("is_extra", False)

        # ---------------------------
        # BASIC MONSTER DATA
        # ---------------------------
        monster.put_int("monster_id", row["monster_id"])
        monster.put_int("id", row["monster_id"])
        monster.put_int("entity_id", row["entity"])
        monster.put_utf_string("genes", row["genes"])
        monster.put_utf_string("common_name", "Monster")
        monster.put_utf_string("spore_graphic", f"spore_{row['genes']}")
        monster.put_int("time_availability", 255)
        monster.put_long("last_changed", current_time_ms)

        monster.put_int("beds", row["beds"])

        # ---------------------------
        # HAPPINESS
        # ---------------------------
        happiness_data = row["happiness"] if is_extra else (json.loads(row["happiness"]) if row["happiness"] else [])
        happiness_array = SFSArray()

        for h in happiness_data:
            h_obj = SFSObject()
            h_obj.put_int("entity", h["entity"])
            h_obj.put_int("value", h["value"])
            happiness_array.add_sfs_object(h_obj)

        monster.put_sfs_array("happiness", happiness_array)

        # ---------------------------
        # NAMES
        # ---------------------------
        names_data = row["names"] if is_extra else (json.loads(row["names"]) if row["names"] else [])
        names_array = SFSArray()

        for name in names_data:
            names_array.add_utf_string(name)

        monster.put_sfs_array("names", names_array)

        # ---------------------------
        # LEVEL / LINKS
        # ---------------------------
        monster.put_int("level_up_xp", row["level_up_xp"])
        monster.put_utf_string("levelup_island", row["levelup_island"])
        title, url = random.choice(list(bbs_urls.items()))

        monster.put_utf_string("link_title", title)
        monster.put_utf_string("link_address", url)
        #monster.put_utf_string("link_title", row["link_title"])
        #monster.put_utf_string("link_address", row["link_address"])

        # ---------------------------
        # ENTITY DATA
        # ---------------------------
        if is_extra:
            entity = row["entity_data"]
        else:
            cur.execute("SELECT * FROM entities WHERE entity_id = ?", (row["entity"],))
            entity = cur.fetchone()

        if entity:
            monster.put_utf_string("entity_type", entity["entity_type"])
            monster.put_utf_string("name", entity["name"])
            monster.put_utf_string("description", entity["description"])
            monster.put_utf_string("keywords", entity.get("keywords", "") if is_extra else (entity["keywords"] or ""))

            # Graphic
            graphic_data = entity["graphic"] if is_extra else json.loads(entity["graphic"])
            graphic = SFSObject()
            for k, v in graphic_data.items():
                graphic.put_utf_string(k, v)
            monster.put_sfs_object("graphic", graphic)

            # Size
            monster.put_int("size_x", entity["size_x"])
            monster.put_int("size_y", entity["size_y"])

            # Costs
            monster.put_int("cost_coins", entity["cost_coins"])
            monster.put_int("cost_eth_currency", entity["cost_eth_currency"])
            monster.put_int("cost_diamonds", entity["cost_diamonds"])
            monster.put_int("cost_sale", entity["cost_sale"])

            # Build / level
            monster.put_int("buildTime", entity["build_time"])
            monster.put_int("level", entity["level"])

            monster.put_bool("box_monster", entity["entity_type"] == "box_monster")

            # Requirements
            requirements = entity["requirements"] if is_extra else json.loads(entity["requirements"])
            requirements_array = SFSArray()

            for req in requirements:
                ro = SFSObject()
                for k, v in req.items():
                    if isinstance(v, int):
                        ro.put_int(k, v)
                    else:
                        ro.put_utf_string(k, str(v))
                requirements_array.add_sfs_object(ro)

            monster.put_sfs_array("requirements", requirements_array)

            # Misc
            monster.put_int("movable", entity["movable"])
            monster.put_int("xp", entity["xp"])
            monster.put_int("y_offset", entity["y_offset"])
            monster.put_int("sticker_offset", entity["y_offset"])

            monster.put_int("view_in_market", entity["view_in_market"])
            monster.put_int("premium", entity["premium"])

            monster.put_utf_string("min_server_version", entity["min_server_version"])

        # ---------------------------
        # LEVELS
        # ---------------------------
        if is_extra:
            lvl_data = row["levels"]
        else:
            cur.execute("SELECT * FROM monster_levels WHERE monster = ?", (row["monster_id"],))
            lvl_data = cur.fetchall()

        levels_array = SFSArray()

        for lvl in lvl_data:
            lo = SFSObject()
            lo.put_int("max_coins", lvl["max_coins"])
            lo.put_int("coins", lvl["coins"])
            lo.put_int("level", lvl["level"])
            lo.put_int("monster_level_id", lvl["monster_level_id"])
            lo.put_int("food", lvl["food"])
            lo.put_int("ethereal_currency", lvl["ethereal_currency"])
            lo.put_int("max_ethereal", lvl["max_ethereal"])
            levels_array.add_sfs_object(lo)

        monster.put_sfs_array("levels", levels_array)

        monsters.add_sfs_object(monster)

    return monsters

def get_levels():
    levels = SFSArray()

    cur.execute("SELECT * FROM level_xp")
    rows = cur.fetchall()

    for row in rows:
        level = SFSObject()

        level.put_int("level", row["level"])
        level.put_int("xp", row["xp"])
        level.put_int("max_bakeries", row["max_bakeries"])

        levels.add_sfs_object(level)

    return levels

def get_scratchoffs():
    scratchoffs = SFSArray()

    cur.execute("SELECT * FROM scratch_offs")
    rows = cur.fetchall()

    for row in rows:
        scratch_offer = SFSObject()

        scratch_offer.put_int("id", row["id"])
        scratch_offer.put_int("scratch_id", row["id"])
        scratch_offer.put_utf_string("type", row["type"])
        scratch_offer.put_utf_string("prize", row["prize"])
        scratch_offer.put_int("amount", row["amount"])
        scratch_offer.put_int("probability", row["probability"])
        scratch_offer.put_int("is_top_prize", row["is_top_prize"])
        scratch_offer.put_utf_string("min_server_version", row["min_server_version"])

        scratchoffs.add_sfs_object(scratch_offer)

    return scratchoffs

def get_game_settings():
    # 1. Fetch existing settings from DB
    cur.execute("SELECT setting, value FROM game_settings")
    rows = cur.fetchall()

    # Build a dict from DB for quick lookup (key = setting name)
    existing = {row["setting"]: row["value"] for row in rows}

    # 2. Define defaults/fallbacks for the ones the client expects
    #    (based on your DB dump + the ones the client code checks for)
    #    Use the same values as in your dump when possible, or safe defaults
    defaults = {
        # Economy / progression related (high risk if missing → parsed as 0 → exploits/crashes)
        "USER_SELLING_PERCENTAGE":                  "0.75",
        "USER_MAX_NUM_TORCHES_PER_ISLAND":          "10",
        "USER_DIAMOND_COST_PER_LIT_TORCH":          "2",
        "USER_DIAMOND_COST_PER_PERMALIT_TORCH":     "100",
        "USER_DIAMOND_COST_PER_DAILY_MEGAFY":       "50",     # example safe-ish value
        "USER_DIAMOND_COST_PER_PERMALIT_MEGAMONSTER":"20",   # example
        "USER_COIN_COST_PER_DAILY_MEGAMONSTER":     "25000",  # example
        "USER_COIN_COST_PER_PERMALIT_MEGAMONSTER":  "250000", # example
        "USER_ETHEREAL_ISLAND_HATCH_XP_MODIFIER":   "0.027",

        "MEMORY_DIAMOND_PRICE":                     "2",
        "MEMORY_COIN_PRICE":                        "0",

        # Scratchoff / monetization
        "USER_SCRATCHOFF_PRICE":                    "2",
        "USER_MONSTER_SCRATCHOFF_PRICE":            "10",

        # More games / cross-promo (usually safe to miss, but client expects)
        "USER_MORE_GAMES_IOS":                      "playhaven",
        "USER_MORE_GAMES_ANDROID":                  "playhaven",
        "USER_MORE_GAMES_AMAZON":                   "chartboost",

        # Facebook / social (usually safe, empty string is ok)
        "USER_FB_ACHIEVEMENTS_URL":                 "http://www.bbbarcade.com/mysingingmonsters/msm_facebook/admin/post_achievement.php",
        "USER_FB_MONSTERS_URL":                     "http://www.bbbarcade.com/mysingingmonsters/msm_facebook/content/monsters/jpg/",
        "USER_FB_CUSTOM_EVENTS_URL":                "http://www.mysingingmonsters.com/facebook/actions/",
        "USER_FB_PLATFORM_REDIRECT_URL":            "http://www.bbbarcade.com/mysingingmonsters/msm_facebook/platform_redirect.php",
        "USER_FB_POST_REWARD_REFRESH":              "24",

        # Exchange rates (old NFT stuff - can be fake/safe values)
        "USER_COIN_ETH_EXCHANGE_RATE":              "500000,50",
        "USER_DIAMOND_ETH_EXCHANGE_RATE":           "50,100",
        "USER_ETH_DIAMOND_EXCHANGE_RATE":           "30000,1",

        # Others that are nice to have
        "USER_NEWS_DATA":                           "0",      # or some timestamp/int
        # "USER_OFFER_WALL_1":                      ""        # usually safe to omit
        # "USER_OFFER_WALL_2":                      ""
    }

    # 3. Build the final array
    game_settings = SFSArray()

    # First add all existing DB entries
    for setting_name, value in existing.items():
        obj = SFSObject()
        obj.put_utf_string("key", setting_name)
        obj.put_utf_string("value", str(value))  # make sure it's string
        game_settings.add_sfs_object(obj)

    # Then add the missing ones (only if not already present)
    for key, default_value in defaults.items():
        if key not in existing:
            obj = SFSObject()
            obj.put_utf_string("key", key)
            obj.put_utf_string("value", default_value)
            game_settings.add_sfs_object(obj)

    return game_settings

def get_torch_data():
    torch_data = SFSArray()

    cur.execute("SELECT * FROM island_torches")
    rows = cur.fetchall()

    for row in rows:
        torch = SFSObject()

        torch.put_int("island_id", row["island_id"])
        torch.put_utf_string("torch_graphic", row["torch_graphic"])
        torch.put_long("last_changed", int(time.time() * 1000))

        torch_data.add_sfs_object(torch)

    return torch_data

def get_timed_events():
    timed_events = SFSArray()

    cur.execute("SELECT * FROM entities")
    rows = cur.fetchall()

    current_time_ms = int(time.time()) * 1000

    end_date = current_time_ms + (((60 * 60) * 24) * 365) * 100

    for row in rows:
        if row["view_in_market"] == 1:
            continue

        event = SFSObject()

        event.put_long("end_date", end_date)
        event.put_long("last_updated", current_time_ms)
        event.put_utf_string("event_type", "EntityStoreAvailability")
        event.put_int("event_id", 3)

        timed_event_data_array = SFSArray()

        timed_entity_data = SFSObject()
        timed_entity_data.put_int("entity", row["entity_id"])

        timed_event_data_array.add_sfs_object(timed_entity_data)

        event.put_sfs_array("data", timed_event_data_array)

        event.put_long("id", 200000 + row["entity_id"])
        event.put_long("start_date", current_time_ms)

        timed_events.add_sfs_object(event)

    return timed_events