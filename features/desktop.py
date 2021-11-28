from base64 import b64decode
import os
import socket

import paramiko
from pypsexec.client import Client


def wake_on_lan(**kwargs):
    print("Sending magic packet...")
    magic = bytes.fromhex("FF"*6 + "2CF05DEA0A98"*16)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # Broadcast
    sock.sendto(magic, ("192.168.0.255", 7))  # to port 7 of broadcast address


def exec_program(**kwargs):
    program_map = {
        "메모장": ("notepad.exe", ""),
        "매트랩": ("cmd.exe", "/c \"C:\\Program Files\\MATLAB\\R2021a\\bin\\matlab.exe\""),
        "철권": ("cmd.exe", "/c start steam://rungameid/389730"),
        "이터널 리턴": ("cmd.exe", "/c start steam://rungameid/1049590"),
        #"계산기": ("cmd.exe", "/c calc.exe"),
        #"넷플릭스": ("cmd.exe", "/c explorer.exe shell:appsFolder\4DF9E0F8.Netflix_mcm4njqhnhss8!Netflix.App"),
    }
    print(f"Executing {kwargs['program_name']}...")
    c = Client("192.168.0.3", username="Dongmin", password=b64decode(os.getenv("DESKTOP_PASSWORD")))
    try:
        c.connect()
        c.create_service()
        command, args = program_map[kwargs['program_name']]
        stdout, stderr, rc = c.run_executable(command, arguments=args, interactive=True, interactive_session=1, use_system_account=True)
    except Exception as e:
        pass
    finally:
        c.remove_service()
        c.disconnect()
