from sfs2x.core import SFSObject, SFSArray
from .island import Island

import time

from tools.database import db_player, cur_player #type: ignore

MAX_RESOURCE = 1_000_000_000

class Player:
    def __init__(self, bbb_id: int, display_name: str, user_id: int):
        self.bbb_id = bbb_id
        self.user_id = user_id
        self.display_name = display_name

        self.islands = []

        self.coins = 5000
        self.diamonds = 20
        self.food = 0
        self.xp = 0
        self.level = 30
        self.shards = 0

        self.active_island = 1

        self.quests = SFSArray()

    def set_quests(self, quests: SFSArray):
        self.quests = quests

    def add_island(self, island: Island):
        self.islands.append(island)

    def get_active_island(self):
        for island in self.islands:
            if island.user_island_id == self.active_island:
                return island
        return None

    def get_properties(self):
        properties = SFSArray()

        self.coins = min(self.coins, MAX_RESOURCE)
        self.diamonds = min(self.diamonds, MAX_RESOURCE)
        self.food = min(self.food, MAX_RESOURCE)

        tmp = SFSObject()
        tmp.put_int("coins", self.coins)
        properties.add_sfs_object(tmp)

        tmp = SFSObject()
        tmp.put_int("diamonds", self.diamonds)
        properties.add_sfs_object(tmp)

        tmp = SFSObject()
        tmp.put_int("food", self.food)
        properties.add_sfs_object(tmp)

        tmp = SFSObject()
        tmp.put_int("xp", self.xp)
        properties.add_sfs_object(tmp)

        tmp = SFSObject()
        tmp.put_int("ethereal_currency", self.shards)
        properties.add_sfs_object(tmp)

        tmp = SFSObject()
        tmp.put_int("level", self.level)
        properties.add_sfs_object(tmp)

        return properties

    def _handle_level_up(self):
        if not self._levels:
            return

        while self.level < 30:
            next_level_data = self._levels.get(self.level + 1)
            if not next_level_data:
                break

            xp_needed = next_level_data.get("xp", 999999999)

            if self.xp >= xp_needed:
                # Level up
                self.level += 1
                self.xp = 0
            else:
                break

    def add_properties(self, coins=0, diamonds=0, food=0, xp=0, shards=0, level=0, set=False):
        coins = round(coins)
        diamonds = round(diamonds)
        food = round(food)
        xp = round(xp)
        shards = round(shards)

        # Check for negative balances
        if self.diamonds + diamonds < 0:
            return False
        if self.coins + coins < 0:
            return False
        if self.food + food < 0:
            return False
        if self.xp + xp < 0:
            return False
        if self.shards + shards < 0:
            return False
        if self.level + level < 0:
            return False

        self.coins += coins
        self.diamonds += diamonds
        self.food += food
        self.xp += xp
        self.shards += shards
        self.level += level

        if set:
            self.coins = coins
            self.diamonds = diamonds
            self.food = food
            self.xp = xp
            self.shards = shards
            self.level = level

        if xp > 0:
            self._handle_level_up()

        self.coins = min(self.coins, MAX_RESOURCE)
        self.diamonds = min(self.diamonds, MAX_RESOURCE)
        self.food = min(self.food, MAX_RESOURCE)
        self.shards = min(self.shards, MAX_RESOURCE)

        cur_player.execute(
            """UPDATE players 
               SET coins = ?, diamonds = ?, food = ?, xp = ?, level = ?, shards = ? 
               WHERE bbb_id = ?""",
            (self.coins, self.diamonds, self.food, self.xp, self.level, self.shards, self.bbb_id)
        )
        db_player.commit()

        return True

    def get_sfs_object(self):
        current_time_ms = int(time.time()) * 1000
        player_object = SFSObject()

        coins = min(self.coins, MAX_RESOURCE)
        diamonds = min(self.diamonds, MAX_RESOURCE)
        food = min(self.food, MAX_RESOURCE)
        shards = min(self.shards, MAX_RESOURCE)

        self.coins = round(coins)
        self.diamonds = round(diamonds)
        self.food = round(food)
        self.xp = round(self.xp)
        self.shards = round(shards)

        player_object.put_int("coins", self.coins)
        player_object.put_int("diamonds", self.diamonds)
        player_object.put_int("food", self.food)
        player_object.put_int("ethereal_currency", self.shards)

        player_object.put_int("premium", 1)

        player_object.put_long("last_login", current_time_ms)

        player_object.put_int("xp", self.xp)
        player_object.put_int("level", self.level)
        player_object.put_int("max_level", 30)

        player_object.put_long("bbb_id", self.bbb_id)
        player_object.put_int("user_id", self.user_id)
        player_object.put_long("referral", 0)
        player_object.put_long("active_island", self.active_island)

        player_object.put_int("fb_invite_reward", 1)
        player_object.put_int("twitter_invite_reward", 1)
        player_object.put_int("email_invite_reward", 1)
        player_object.put_long("last_fb_post_reward", current_time_ms)

        player_object.put_sfs_array("achievements", SFSArray())

        player_object.put_sfs_array("viewable_ads", SFSArray())
        player_object.put_utf_string("extra_ad_params", "")

        player_object.put_bool("third_party_ads", False)
        player_object.put_bool("third_party_video_ads", False)

        player_object.put_utf_string("display_name", self.display_name)

        islands = SFSArray()

        for island in self.islands:
            islands.add_sfs_object(island.get_sfs_object())

        player_object.put_sfs_array("islands", islands)

        #player_object.put_int("daily_bonus_diamonds", 0)
        #player_object.put_int("daily_bonus_coins", 200)
        #player_object.put_int("reward_day", 1)

        player_object.put_utf_string("c", "breedingAddOnBridged")
        player_object.put_utf_string("client_tutorial_setup", "breedingAddOnBridged")

        player_object.put_sfs_array("quests", self.quests)

        return player_object