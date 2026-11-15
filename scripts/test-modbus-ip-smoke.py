#!/usr/bin/env python3
"""Offline protocol checks for the read-only Modbus TCP hardware smoke tool."""
import importlib.util
import pathlib
import socket
import struct
import threading
import unittest

script = pathlib.Path(__file__).with_name("modbus-ip-smoke.py")
spec = importlib.util.spec_from_file_location("modbus_ip_smoke", script)
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


class SmokeTests(unittest.TestCase):
    def run_server(self, reply):
        ready = threading.Event()
        info = {}

        def serve():
            with socket.socket() as listener:
                listener.bind(("127.0.0.1", 0))
                listener.listen(1)
                info["port"] = listener.getsockname()[1]
                ready.set()
                connection, _ = listener.accept()
                with connection:
                    connection.settimeout(2)
                    request = smoke.receive_exact(connection, 12)
                    info["request"] = request
                    connection.sendall(reply)

        worker = threading.Thread(target=serve, daemon=True)
        worker.start()
        self.assertTrue(ready.wait(2))
        return info, worker

    def test_success(self):
        pdu = bytes.fromhex("03041234abcd")
        reply = struct.pack(">HHHB", 0xF101, 0, len(pdu) + 1, 17) + pdu
        info, worker = self.run_server(reply)
        result = smoke.exchange("127.0.0.1", info["port"], 2, 17, 3, 52, 2, 0xF101)
        worker.join(2)
        self.assertEqual(result["values"], [0x1234, 0xABCD])
        self.assertEqual(info["request"][-5:], bytes.fromhex("0300340002"))

    def test_exception(self):
        pdu = bytes.fromhex("830b")
        reply = struct.pack(">HHHB", 0xF101, 0, 3, 17) + pdu
        info, worker = self.run_server(reply)
        result = smoke.exchange("127.0.0.1", info["port"], 2, 17, 3, 52, 2, 0xF101)
        worker.join(2)
        self.assertEqual(result["exception"], 11)

    def test_wrong_transaction(self):
        pdu = bytes.fromhex("03020001")
        reply = struct.pack(">HHHB", 0x1234, 0, len(pdu) + 1, 17) + pdu
        info, worker = self.run_server(reply)
        with self.assertRaisesRegex(ValueError, "transaction ID"):
            smoke.exchange("127.0.0.1", info["port"], 2, 17, 3, 52, 1, 0xF101)
        worker.join(2)


if __name__ == "__main__":
    unittest.main()
