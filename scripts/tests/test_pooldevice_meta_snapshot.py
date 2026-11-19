"""Test that the PoolDevice Web metadata route can read all slots under one lock."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.tests.test_io_boot_binding import function

ROOT = Path(__file__).resolve().parents[2]


class PoolDeviceMetaSnapshotTests(unittest.TestCase):
    def test_snapshot_is_equivalent_to_individual_metadata(self):
        production = (ROOT / "src/Modules/PoolDeviceModule/PoolDeviceControl.cpp").read_text()
        harness = (ROOT / "test/host/pool_device_meta_snapshot.cpp").read_text()
        definitions = "\\n".join(
            function(production, signature) for signature in (
                "void PoolDeviceModule::fillMetaLocked_",
                "PoolDeviceSvcStatus PoolDeviceModule::svcMetaImpl_",
                "PoolDeviceSvcStatus PoolDeviceModule::svcSnapshotMetaImpl_"
            )
        )
        harness = harness.replace("// PRODUCTION_METHODS", definitions)
        with tempfile.TemporaryDirectory(prefix="flow-poolmeta-") as directory:
            source = Path(directory) / "main.cpp"
            binary = Path(directory) / "test"
            source.write_text(harness)
            for command in (
                ["c++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                 "-Itest/host/stubs", "-Isrc", "-Iinclude",
                 str(source), "-o", str(binary)],
                [str(binary)],
            ):
                result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
