from sfs2x.core import SFSObject, SFSArray

import time

from .structure import Structure #type: ignore
from .monster import Monster #type: ignore
from .egg import Egg #type: ignore
from .megadata import MegaData # type: ignore

from tools.database import db_player, cur_player # type: ignore

class Island:
    def __init__(self, bbb_id: int, island_id: int, user_island_id: int):
        self.bbb_id = bbb_id
        self.island_id = island_id
        self.user_island_id = user_island_id

        self.warp_speed = 1.0

        self.structures = []
        self.monsters = []
        self.eggs = []

        self.dislikes = 0
        self.likes = 0

    def add_structure(self, structure):
        self.structures.append(structure)

    def add_monster(self, monster):
        self.monsters.append(monster)

    def add_egg(self, egg):
        self.eggs.append(egg)

    def get_sfs_object(self):
        island = SFSObject()

        island.put_long("user_island_id", self.user_island_id)
        island.put_long("user", self.bbb_id)
        island.put_long("upgrading_until", 0)
        island.put_long("upgrade_started", 0)

        island.put_int("likes", self.likes)
        island.put_int("dislikes", self.dislikes)
        island.put_int("level", 1)
        island.put_int("island", self.island_id)

        island.put_double("warp_speed", self.warp_speed)

        monsters = SFSArray()
        structures = SFSArray()
        eggs = SFSArray()

        for monster in self.monsters:
            monsters.add_sfs_object(monster.get_sfs_object())

        for structure in self.structures:
            structures.add_sfs_object(structure.get_sfs_object())

        for egg in self.eggs:
            eggs.add_sfs_object(egg.get_sfs_object())

        island.put_sfs_array("structures", structures)

        island.put_sfs_array("monsters", monsters)

        island.put_sfs_array("breeding", SFSArray())
        #island.put_sfs_object("buyback", SFSObject())
        island.put_sfs_array("torches", SFSArray())
        island.put_sfs_array("eggs", eggs)
        island.put_sfs_array("baking", SFSArray())

        island.put_sfs_array("gi_mappings", SFSArray())

        last_bred = SFSObject()
        last_bred.put_long("user_monster_1", 0)
        last_bred.put_long("user_monster_2", 0)

        island.put_sfs_object("last_bred", last_bred)

        return island
    
    def add_player_monsters(self):
        cur_player.execute("""
            SELECT * FROM player_monsters WHERE user_island_id = ?
        """, (self.user_island_id,))
        monsters = cur_player.fetchall()

        for monsterData in monsters:
            monster = Monster(self.user_island_id, monsterData["user_monster_id"], monsterData["monster"], monsterData["pos_x"], monsterData["pos_y"], monsterData["flip"], monsterData["level"], 50, monsterData["collected_coins"], monsterData["times_fed"], monsterData["volume"], monsterData["date_created"], monsterData["last_collection"], monsterData["muted"])

            cur_player.execute("""
                SELECT * FROM monster_mega_data WHERE user_monster_id = ?
            """, (monsterData["user_monster_id"],))
            mega_data = cur_player.fetchone()

            if mega_data:
                monster.mega_data = MegaData(
                    user_monster_id=monsterData["user_monster_id"],
                    permamega=mega_data["permamega"],
                    currently_mega=mega_data["currently_mega"],
                    started_at=mega_data["started_at"] or None,
                    finishes_at=mega_data["finishes_at"] or None
                )

            self.add_monster(monster)

    def add_player_structures(self):
        cur_player.execute("""
            SELECT * FROM player_structures WHERE user_island_id = ?
        """, (self.user_island_id,))
        structures = cur_player.fetchall()

        for structureData in structures:
            structure = Structure(self.user_island_id, structureData["user_structure_id"], structureData["structure"], structureData["pos_x"], structureData["pos_y"], structureData["flip"], structureData["scale"], structureData["date_created"], structureData["building_completed"])

            self.add_structure(structure)

    def add_player_eggs(self):
        cur_player.execute("""
            SELECT * FROM player_eggs WHERE user_island_id = ?
        """, (self.user_island_id,))
        eggs = cur_player.fetchall()
        for eggData in eggs:
            egg = Egg(self.user_island_id, eggData["laid_on"], eggData["hatches_on"], eggData["monster"], eggData["user_egg_id"])

            self.add_egg(egg)

    def create_structures(self):
        current_time = int(time.time() * 1000)
        
        nx, ny = 35, 17
        cid, cx, cy = 7, 29, 9

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
            self.user_island_id,
            current_time,
            nx,
            ny,
            0,
            0,
            1,
            0,
            1,
            1.0,
            current_time,
            current_time,
            0,
            0
        ))

        new_structure_id = cur_player.lastrowid

        self.add_structure(Structure(
            self.user_island_id,
            new_structure_id,
            1,
            nx,
            ny,
            0,
            1.0,
            current_time,
            current_time
        ))

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
            self.user_island_id,
            current_time,
            cx,
            cy,
            0,
            0,
            1,
            0,
            cid,
            1.0,
            current_time,
            current_time,
            0,
            0
        ))

        new_structure_id = cur_player.lastrowid

        self.add_structure(Structure(
            self.user_island_id,
            new_structure_id,
            cid,
            cx,
            cy,
            0,
            1.0,
            current_time,
            current_time
        ))

        db_player.commit()