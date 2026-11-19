import base64
import pyotp

def get_mfa(key, min_bytes = 16):
    raw = base64.b32decode(key)
    raw = raw.ljust(min_bytes, b"\x00")

    padded_key = base64.b32encode(raw).decode()
    return pyotp.TOTP(padded_key).now()