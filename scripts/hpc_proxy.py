#!/usr/bin/env python3
"""SSH ProxyCommand that uses small TCP segments. The VPN to the Bocconi cluster drops full-size
packets, so small commands work but uploads stall. Capping the segment size avoids that without
admin rights.

Usage: ssh -o ProxyCommand="python3 scripts/hpc_proxy.py %h %p" ...
"""
import os
import select
import socket
import sys

SEGMENT = 1100

connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_MAXSEG, SEGMENT)
connection.settimeout(25)
connection.connect((sys.argv[1], int(sys.argv[2])))
connection.settimeout(None)
incoming, outgoing = sys.stdin.fileno(), sys.stdout.fileno()
watching = [connection, incoming]
while watching:
    ready, _, _ = select.select(watching, [], [])
    if connection in ready:
        data = connection.recv(65536)
        if not data:
            break
        view = memoryview(data)
        while view:
            view = view[os.write(outgoing, view):]
    if incoming in ready:
        data = os.read(incoming, 65536)
        if data:
            connection.sendall(data)
        else:
            watching.remove(incoming)
            connection.shutdown(socket.SHUT_WR)
