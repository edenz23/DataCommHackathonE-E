import socket
import struct
import threading


def hex_to_binary(data=0xabcddcba, size_in_bytes=4):  # default values refer to the magic cookie
    return format(data, f'0>{size_in_bytes*8}b').encode("utf-8")


def binary_to_hex(b):
    return hex(int(b, 2))


magic_cookie = hex_to_binary()

print(magic_cookie)
print(type(magic_cookie))
print(len(magic_cookie))
print(len(magic_cookie)/8)
print("-------------------")


# construct 'offer' msg (magic cookie, msg_type 0x2,)
msg = hex_to_binary() + hex_to_binary(0x2, 1)

print(f"msg: {msg}")
print(len(msg))
print(f"cookie: {binary_to_hex(msg[:32])}")
print(f"msg_type: {binary_to_hex(msg[32:40])}")

print(f"\u001b[33mMessage here..\u001b[0m")
