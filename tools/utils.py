from sfs2x.protocol import Message, ControllerID
from sfs2x.core import SFSObject, SFSArray

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding

import hashlib
import base64
import re
import json

from tools.database import cur_player #type: ignore

def md5_sum(input_string):
    encoded_string = input_string.encode('utf-8')

    md5_hash = hashlib.md5(encoded_string)

    return md5_hash.hexdigest()

def debug_sfsobject(obj, path="root"):
    for key in obj.keys():
        value = obj.get(key)
        if value is None:
            print(f"❌ {path}.{key} is None!")
        elif isinstance(value, SFSObject):
            debug_sfsobject(value, path=f"{path}.{key}")
        elif isinstance(value, SFSArray):
            for i, item in enumerate(value):
                if isinstance(item, SFSObject):
                    debug_sfsobject(item, path=f"{path}.{key}[{i}]")
                elif item is None:
                    print(f"❌ {path}.{key}[{i}] is None!")

async def send_extension_response(client, cmd, params):
    ext_resp = SFSObject()
    ext_resp.put_utf_string("c", cmd)
    ext_resp.put_int("r", -1)
    ext_resp.put_sfs_object("p", params)

    debug_sfsobject(params)

    await client.send(Message(
        controller=ControllerID.EXTENSION,
        action=13,
        payload=ext_resp
    ))

def speedup_cost_diamonds(now_ms: int, end_ms: int) -> int:
    if now_ms >= end_ms:
        return 0
    return round((end_ms - now_ms) / 1_800_000) + 1

def player_exists(bbb_id):
    cur_player.execute("SELECT 1 FROM players WHERE bbb_id = ?", (bbb_id,))
    return cur_player.fetchone() is not None

def encrypt(message, initial_vector, secret_key):
    secret_key = secret_key.encode('utf-8')[:16]
    cipher = Cipher(algorithms.AES(secret_key), modes.CFB8(initial_vector.encode('utf-8')), backend=default_backend())
    padder = padding.PKCS7(128).padder()
    padded_message = padder.update(message.encode('utf-8')) + padder.finalize()
    encryptor = cipher.encryptor()
    encrypted = encryptor.update(padded_message) + encryptor.finalize()
    return base64.b64encode(encrypted).decode('utf-8')

def decrypt(encrypted_message, initial_vector, secret_key):
    secret_key = secret_key.encode('utf-8')[:16]
    cipher = Cipher(algorithms.AES(secret_key), modes.CFB8(initial_vector.encode('utf-8')), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted_padded = decryptor.update(base64.b64decode(encrypted_message)) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()
    return decrypted.decode('utf-8')

def _load_json_no_comments(path):
    with open(path, "r") as f:
        text = f.read()

    text = re.sub(r'//.*', '', text)
    return json.loads(text)

def get_config_value(key):
    config = _load_json_no_comments("config.json")
    return config.get(key)