from sfs2x.core import SFSObject

class GiMonster:
    def __init__(self, parent_id, gi_monster_id):
        self.parent_id = parent_id
        self.gi_monster_id = gi_monster_id

    def get_sfs_object(self):
        obj = SFSObject()
        obj.put_long("user_gi_monster", self.gi_monster_id)
        obj.put_long("user_monster", self.parent_id) # parent
        return obj