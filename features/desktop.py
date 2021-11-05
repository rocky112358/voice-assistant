import socket


def wake_on_lan(**kwargs):
    print("Sending magic packet...")
    magic = bytes.fromhex("FF"*6 + "2CF05DEA0A98"*16)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # Broadcast
    sock.sendto(magic, ("192.168.0.255", 7))  # to port 7 of broadcast address


def exec_calc(**kwargs):
    print("Executing calc.exe...")
    pass
