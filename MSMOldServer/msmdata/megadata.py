import time
from sfs2x.core import SFSObject

class MegaData:
    def __init__(self, user_monster_id: int, permamega: bool = True, currently_mega: bool = False, started_at: int = None, finishes_at: int = None):
        self.user_monster_id = user_monster_id
        self.permamega = permamega
        self.currently_mega = currently_mega
        self.started_at = started_at
        self.finishes_at = finishes_at
    def get_sfs_object(self) -> SFSObject:
        mega_data_obj = SFSObject()

        #mega_data_obj.put_long("user_monster_id", self.user_monster_id)
        mega_data_obj.put_bool("permamega", self.permamega)
        mega_data_obj.put_bool("currently_mega", self.currently_mega)

        if not self.permamega and self.started_at is not None and self.finishes_at is not None:
            mega_data_obj.put_long("started_at", self.started_at)
            mega_data_obj.put_long("finished_at", self.finishes_at)

        return mega_data_obj