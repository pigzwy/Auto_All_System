#!/usr/bin/env python3
"""Simple TCP forwarder (no deps).

Used for local dev on Linux to expose host-local-only services (127.0.0.1)
to Docker containers via host network.
"""

from __future__ import annotations

import argparse
import socket
import threading


def _parse_addr(value: str) -> tuple[str, int]:
    if ":" not in value:
        raise argparse.ArgumentTypeError("address must be HOST:PORT")
    host, port_s = value.rsplit(":", 1)
    try:
        port = int(port_s)
    except ValueError as e:
        raise argparse.ArgumentTypeError("invalid port") from e
    return host, port


def _pipe(src: socket.socket, dst: socket.socket):
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except Exception:
        pass
    finally:
        try:
            dst.shutdown(socket.SHUT_WR)
        except Exception:
            pass


def _handle_client(client: socket.socket, target: tuple[str, int], timeout: float):
    try:
        upstream = socket.create_connection(target, timeout=timeout)
    except Exception:
        try:
            client.close()
        except Exception:
            pass
        return

    t1 = threading.Thread(target=_pipe, args=(client, upstream), daemon=True)
    t2 = threading.Thread(target=_pipe, args=(upstream, client), daemon=True)
    t1.start()
    t2.start()

    t1.join()
    t2.join()

    try:
        client.close()
    except Exception:
        pass
    try:
        upstream.close()
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--listen", type=_parse_addr, required=True)
    parser.add_argument("--target", type=_parse_addr, required=True)
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()

    listen_host, listen_port = args.listen
    target = args.target

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((listen_host, listen_port))
    server.listen(128)

    while True:
        client, _ = server.accept()
        threading.Thread(
            target=_handle_client, args=(client, target, args.timeout), daemon=True
        ).start()


if __name__ == "__main__":
    main()
