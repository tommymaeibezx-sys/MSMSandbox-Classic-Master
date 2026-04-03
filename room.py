from sfs2x.core import SFSArray

class Room:
    def __init__(self, room_id=0, name="Limbo", room_type="default", is_hidden=False, 
                 is_password_protected=True, is_game=False, user_count=1, max_players=1000):
        self.room_id = room_id
        self.name = name
        self.room_type = room_type
        self.is_hidden = is_hidden
        self.is_password_protected = is_password_protected
        self.is_game = is_game
        self.user_count = user_count
        self.max_players = max_players
        self.vars = []

    def add_var(self, var):
        self.vars.append(var)

    def to_sfs_array(self):
        sfs_room = SFSArray()
        sfs_room.add_int(self.room_id)
        sfs_room.add_utf_string(self.name)
        sfs_room.add_utf_string(self.room_type)
        sfs_room.add_bool(self.is_game)
        sfs_room.add_bool(self.is_hidden)
        sfs_room.add_bool(self.is_password_protected)
        sfs_room.add_short(self.user_count)
        sfs_room.add_short(self.max_players)

        vars_array = SFSArray()
        for var in self.vars:
            vars_array.add_sfs_object(var)

        sfs_room.add_sfs_array(vars_array)
        return sfs_room
