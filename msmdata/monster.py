import time
from sfs2x.core import SFSObject

class Monster:
    def __init__(
        self,
        user_island_id: int,
        user_monster_id: int,
        monster_id: int,
        x: int = 1,
        y: int = 1,
        flip: int = 0,
        level: int = 1,
        happiness: int = 50,
        collected_coins: int = 0,
        times_fed: int = 0,
        volume: float = 1.0,
        date_created: int = None,
        last_collection: int = None,
        muted: int = 0,
        mega_data: dict = None
    ):
        self.user_island_id = user_island_id
        self.user_monster_id = user_monster_id
        self.monster_id = monster_id
        self.x = x
        self.y = y
        self.flip = flip
        self.level = level
        self.happiness = happiness
        self.collected_coins = collected_coins
        self.times_fed = times_fed
        self.volume = volume
        self.date_created = date_created or int(time.time() * 1000)
        self.last_collection = int(time.time() * 1000)
        self.muted = muted

        self.mega_data = mega_data or None

    def get_sfs_object(self):
        monster_obj = SFSObject()

        monster_obj.put_long("user_monster_id", self.user_monster_id)
        monster_obj.put_long("user_island_id", self.user_island_id)
        monster_obj.put_long("island", self.user_island_id)

        monster_obj.put_long("monster", self.monster_id)

        monster_obj.put_int("pos_x", self.x)
        monster_obj.put_int("pos_y", self.y)
        monster_obj.put_int("flip", self.flip)

        monster_obj.put_int("level", self.level)
        monster_obj.put_int("happiness", 100)

        monster_obj.put_int("collected_coins", self.collected_coins)
        monster_obj.put_int("collected_ethereal", 0)
        monster_obj.put_int("collected_diamonds", 0)
        monster_obj.put_int("collected_food", 0)

        monster_obj.put_int("times_fed", self.times_fed)

        monster_obj.put_double("volume", float(self.volume))
        monster_obj.put_int("muted", self.muted)
        monster_obj.put_int("in_hotel", 0)

        monster_obj.put_long("last_feeding", self.date_created)
        monster_obj.put_long("date_created", self.date_created)
        monster_obj.put_long("last_collection", self.last_collection)

        monster_obj.put_utf_string("name", "made by @riotlove_official on YouTube")

        if self.mega_data:
            monster_obj.put_sfs_object("megamonster", self.mega_data.get_sfs_object())

        monster_obj.put_utf_string("boxed_eggs", "[]")

        return monster_obj