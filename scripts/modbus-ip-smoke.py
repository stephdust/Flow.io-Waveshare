#!/usr/bin/env python3
"""Read-only, dependency-free Modbus TCP smoke test against a real Flow.io gateway."""
import argparse
import socket
import struct
import sys


def receive_exact(sock, count):
    data = bytearray()
    while len(data) < count:
        chunk = sock.recv(count - len(data))
        if not chunk:
            raise ConnectionError("connection closed while reading Modbus response")
        data.extend(chunk)
    return bytes(data)


def exchange(host, port, timeout, unit, function, address, count, transaction):
    pdu = struct.pack(">BHH", function, address, count)
    request = struct.pack(">HHHB", transaction, 0, len(pdu) + 1, unit) + pdu
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.settimeout(timeout)
        sock.sendall(request)
        header = receive_exact(sock, 7)
        rx_transaction, protocol, length, rx_unit = struct.unpack(">HHHB", header)
        if protocol != 0 or not 2 <= length <= 254:
            raise ValueError("invalid MBAP header")
        if rx_transaction != transaction or rx_unit != unit:
            raise ValueError("transaction ID or unit ID mismatch")
        payload = receive_exact(sock, length - 1)
        if len(payload) == 2 and payload[0] == (function | 0x80):
            return {"exception": payload[1], "values": None}
        if len(payload) != 2 + 2 * count or payload[0] != function or payload[1] != 2 * count:
            raise ValueError("invalid read response function, byte count or length")
        return {"exception": None, "values": list(struct.unpack(">" + "H" * count, payload[2:]))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, help="Flow.io ESP32-S3 IP address")
    parser.add_argument("--port", type=int, default=502)
    parser.add_argument("--unit", type=int, required=True, help="Modbus RTU unit ID, 1..247")
    parser.add_argument("--address", type=int, default=0, help="Zero-based register address")
    parser.add_argument("--count", type=int, default=1, help="Register count, 1..32")
    parser.add_argument("--function", type=int, choices=(3, 4), default=3)
    parser.add_argument("--timeout", type=float, default=6.0)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535 or not 1 <= args.unit <= 247:
        parser.error("port must be 1..65535 and unit must be 1..247")
    if not 0 <= args.address <= 65535 or not 1 <= args.count <= 32 or args.address + args.count > 65536:
        parser.error("invalid register address/count")
    if args.timeout <= 0:
        parser.error("timeout must be positive")
    try:
        result = exchange(args.host, args.port, args.timeout, args.unit,
                          args.function, args.address, args.count, 0xF101)
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 2
    if result["exception"] is not None:
        print(f"MODBUS EXCEPTION: 0x{result['exception']:02X}")
        return 1
    print("OK: " + " ".join(f"0x{value:04X}" for value in result["values"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
