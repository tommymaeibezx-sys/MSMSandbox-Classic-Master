from sfs2x.core import SFSObject

class Breeding:
    def __init__(self, user_island_id, user_breeding_id, user_structure_id,
                 monster_1, monster_2, result,
                 started_on, completes_on):
        
        self.island_id = user_island_id
        self.user_breeding_id = user_breeding_id
        self.structure_id = user_structure_id
        self.monster_1 = monster_1
        self.monster_2 = monster_2
        self.new_monster = result
        self.started_on = started_on
        self.complete_on = completes_on

    def get_sfs_object(self):
        s = SFSObject()

        s.put_long("island", self.island_id)
        s.put_long("user_breeding_id", self.user_breeding_id)
        s.put_long("structure", self.structure_id)

        s.put_int("monster_1", self.monster_1)
        s.put_int("monster_2", self.monster_2)
        s.put_int("new_monster", self.new_monster)

        s.put_long("started_on", self.started_on)
        s.put_long("complete_on", self.complete_on)

        return s