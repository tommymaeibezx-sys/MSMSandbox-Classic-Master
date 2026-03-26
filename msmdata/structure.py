import time
from sfs2x.core import SFSObject, SFSArray
import json

def sfs_to_plain(value):
    # SFSArray → list
    if value.__class__.__name__ == "SFSArray":
        return [sfs_to_plain(v) for v in value.value]

    # SFSObject → dict
    if value.__class__.__name__ == "SFSObject":
        return {k: sfs_to_plain(v) for k, v in value.value.items()}

    # Field → unwrap .value
    if hasattr(value, "value"):
        return sfs_to_plain(value.value)

    # Primitive
    return value

def sfs_to_json(sfs_array):
    return json.dumps(sfs_to_plain(sfs_array), indent=2)

class Structure:
    def __init__(self, user_island_id: int, user_structure_id: int, structure_id: int, x: int, y: int, flip: int, scale: float, date_created: int, building_completed: int):
        self.user_island_id = user_island_id
        self.user_structure_id = user_structure_id
        self.structure_id = structure_id
        self.x = x
        self.y = y
        self.flip = flip
        self.scale = scale
        self.date_created = date_created
        self.building_completed = building_completed

    def get_sfs_object(self):
        structure_obj = SFSObject()

        structure_obj.put_long("user_structure_id", self.user_structure_id)
        structure_obj.put_long("user_island_id", self.user_island_id)

        structure_obj.put_int("pos_x", self.x)
        structure_obj.put_int("pos_y", self.y)
        structure_obj.put_int("flip", self.flip)
        structure_obj.put_int("muted", 0)
        structure_obj.put_int("is_complete", 1)
        structure_obj.put_int("is_upgrading", 0)
        structure_obj.put_int("structure", self.structure_id)

        inventory = SFSArray()
        m = SFSObject()

        m.put_int("m", 68)

        inventory.add_sfs_object(m)

        structure_obj.put_sfs_array("inv", inventory)
        structure_obj.put_utf_string("req", sfs_to_json(inventory))
        structure_obj.put_float("scale", self.scale)

        if self.date_created != -1:
            structure_obj.put_long("date_created", self.date_created)
            structure_obj.put_long("building_completed", self.building_completed)

        if hasattr(self, "obj_data") and self.obj_data is not None:
            structure_obj.put_int("obj_data", self.obj_data)

        if hasattr(self, "obj_end") and self.obj_end is not None:
            structure_obj.put_long("obj_end", self.obj_end)

        return structure_obj