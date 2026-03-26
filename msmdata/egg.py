import time
from sfs2x.core import SFSObject

class Egg:
    def __init__(self, island_id: int, laid_on: int, hatches_on: int, monster_id: int, user_egg_id: int, user_structure_id: int):
        self.island_id = island_id
        self.laid_on = laid_on
        self.hatches_on = hatches_on
        self.monster_id = monster_id
        self.user_egg_id = user_egg_id
        self.user_structure_id = user_structure_id

    def get_sfs_object(self):
        egg = SFSObject()
        egg.put_long("island", self.island_id)
        egg.put_int("structure", self.user_structure_id)

        egg.put_int("monster", self.monster_id)
        egg.put_long("user_egg_id", self.user_egg_id)

        egg.put_long("hatches_on", self.hatches_on)
        egg.put_long("laid_on", self.laid_on)

        return egg