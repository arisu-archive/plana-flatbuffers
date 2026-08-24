from contextlib import contextmanager
import importlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import flatbuffers


ROOT = Path(__file__).resolve().parents[2]
PROCESSOR_PATH = ROOT / ".scripts" / "process_python_object_api.py"
FIXTURE_ROOT = ROOT / "tests" / "python" / "fixtures" / "generated"


def run_processor(
    package_dir: Path,
    without_decryption: bool = False,
    package: str = "TestData",
):
    command = [
        sys.executable,
        str(PROCESSOR_PATH),
        "--directory",
        str(package_dir),
        "--package",
        package,
    ]
    if without_decryption:
        command.append("--without-decryption")
    return subprocess.run(command, capture_output=True, text=True, check=False)


def snapshot(directory: Path):
    return {
        path.relative_to(directory): path.read_bytes()
        for path in directory.rglob("*.py")
    }


@contextmanager
def imported_fixture(root: Path):
    prefix = "TestData"
    for name in tuple(sys.modules):
        if name == prefix or name.startswith(prefix + "."):
            del sys.modules[name]
    sys.path.insert(0, str(root))
    try:
        yield
    finally:
        sys.path.remove(str(root))
        for name in tuple(sys.modules):
            if name == prefix or name.startswith(prefix + "."):
                del sys.modules[name]


class ObjectApiProcessorTests(unittest.TestCase):
    def copy_fixture(self, temp_dir: str):
        destination = Path(temp_dir) / "TestData"
        shutil.copytree(FIXTURE_ROOT / "TestData", destination)
        object_api_template = destination / "ObjectApiSample.py.fixture"
        object_api_template.replace(destination / "ObjectApiSample.py")
        return destination

    def test_encrypted_object_api_round_trip_uses_root_key_without_mutation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = self.copy_fixture(temp_dir)
            result = run_processor(package_dir)
            self.assertEqual(result.returncode, 0, result.stderr)

            with imported_fixture(Path(temp_dir)):
                child_module = importlib.import_module("TestData.Child")
                sample_module = importlib.import_module("TestData.ObjectApiSample")
                helper = importlib.import_module("TestData.flatdatas_helper")

                model = sample_module.ObjectApiSampleT(
                    count=123456789,
                    total=-123456789012345,
                    unsignedCount=4000000000,
                    bigCount=12345678901234567890,
                    smallCount=42,
                    ratio=-1.25,
                    preciseRatio=-2.5,
                    title="Arona",
                    enabled=True,
                    self_=True,
                    kind=1,
                    values=[1, 0, 2],
                    labels=["Arona", "アロナ"],
                    child=child_module.ChildT(amount=77),
                    children=[child_module.ChildT(amount=99)],
                )

                builder = flatbuffers.Builder(0)
                builder.Finish(model.Pack(builder))
                packed = bytes(builder.Output())

                raw = sample_module.ObjectApiSample.GetRootAs(packed)
                self.assertEqual(raw.Count(), 1304623542)
                self.assertNotEqual(raw.Title(), b"Arona")
                self.assertEqual(raw.Child().Amount(), 1251554542)
                self.assertTrue(raw.Enabled())
                self.assertTrue(raw.Self())

                self.assertEqual(model.count, 123456789)
                self.assertEqual(model.title, "Arona")
                self.assertEqual(model.values, [1, 0, 2])
                self.assertEqual(model.child.amount, 77)

                unpacked = sample_module.ObjectApiSampleT.InitFromPackedBuf(packed)
                self.assertEqual(unpacked.count, 123456789)
                self.assertEqual(unpacked.total, -123456789012345)
                self.assertEqual(unpacked.unsignedCount, 4000000000)
                self.assertEqual(unpacked.bigCount, 12345678901234567890)
                self.assertEqual(unpacked.smallCount, 42)
                self.assertAlmostEqual(unpacked.ratio, -1.25, places=6)
                self.assertEqual(unpacked.preciseRatio, -2.5)
                self.assertEqual(unpacked.title, "Arona")
                self.assertTrue(unpacked.enabled)
                self.assertTrue(unpacked.self_)
                self.assertEqual(unpacked.kind, 1)
                self.assertEqual(unpacked.values, [1, 0, 2])
                self.assertEqual(unpacked.labels, ["Arona", "アロナ"])
                self.assertEqual(unpacked.child.amount, 77)
                self.assertEqual(unpacked.children[0].amount, 99)

                fresh = helper.get_flat_data_by_name("objectapisample")
                self.assertIsInstance(fresh, sample_module.ObjectApiSampleT)
                self.assertIsNone(helper.get_flat_data_by_name("missing"))

    def test_pythonic_bytes_api_encrypts_and_decrypts_without_mutation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = self.copy_fixture(temp_dir)
            result = run_processor(package_dir)
            self.assertEqual(result.returncode, 0, result.stderr)

            with imported_fixture(Path(temp_dir)):
                child_module = importlib.import_module("TestData.Child")
                sample_module = importlib.import_module("TestData.ObjectApiSample")
                model = sample_module.ObjectApiSampleT(
                    count=123456789,
                    title="Arona",
                    child=child_module.ChildT(amount=77),
                )

                packed = model.to_bytes()

                self.assertIsInstance(packed, bytes)
                raw = sample_module.ObjectApiSample.GetRootAs(packed)
                self.assertEqual(raw.Count(), 1304623542)
                self.assertNotEqual(raw.Title(), b"Arona")
                self.assertEqual(raw.Child().Amount(), 1251554542)
                self.assertEqual(model.count, 123456789)
                self.assertEqual(model.title, "Arona")
                self.assertEqual(model.child.amount, 77)

                unpacked = sample_module.ObjectApiSampleT.from_bytes(packed)
                self.assertEqual(unpacked.count, 123456789)
                self.assertEqual(unpacked.title, "Arona")
                self.assertEqual(unpacked.child.amount, 77)

    def test_self_field_is_sanitized_to_a_compilable_object_attribute(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = self.copy_fixture(temp_dir)
            result = run_processor(package_dir, without_decryption=True)
            self.assertEqual(result.returncode, 0, result.stderr)

            compile_result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "py_compile",
                    str(package_dir / "ObjectApiSample.py"),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)

    def test_without_decryption_keeps_generated_object_api_plain(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = self.copy_fixture(temp_dir)
            result = run_processor(package_dir, without_decryption=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((package_dir / "_conversion.py").exists())

            with imported_fixture(Path(temp_dir)):
                sample_module = importlib.import_module("TestData.ObjectApiSample")
                helper = importlib.import_module("TestData.flatdatas_helper")
                model = sample_module.ObjectApiSampleT(count=42, title="plain")
                builder = flatbuffers.Builder(0)
                builder.Finish(model.Pack(builder))
                packed = bytes(builder.Output())

                raw = sample_module.ObjectApiSample.GetRootAs(packed)
                self.assertEqual(raw.Count(), 42)
                self.assertEqual(raw.Title(), b"plain")
                self.assertIsInstance(
                    helper.get_flat_data_by_name("objectapisample"),
                    sample_module.ObjectApiSampleT,
                )

    def test_processing_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = self.copy_fixture(temp_dir)
            first = run_processor(package_dir)
            self.assertEqual(first.returncode, 0, first.stderr)
            first_snapshot = snapshot(package_dir)

            second = run_processor(package_dir)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(snapshot(package_dir), first_snapshot)

    def test_validation_failure_does_not_partially_modify_package(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = self.copy_fixture(temp_dir)
            broken = package_dir / "Broken.py"
            broken.write_text(
                "class Broken:\n"
                "    pass\n\n"
                "class BrokenT:\n"
                "    def _UnPack(self, broken):\n"
                "        pass\n",
                encoding="utf-8",
            )
            before = snapshot(package_dir)

            result = run_processor(package_dir)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Broken.py", result.stderr)
            self.assertEqual(snapshot(package_dir), before)
            self.assertFalse((package_dir / "_conversion.py").exists())
            self.assertFalse((package_dir / "flatdatas_helper.py").exists())

    def test_invalid_package_name_is_rejected_without_writes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = self.copy_fixture(temp_dir)
            before = snapshot(package_dir)

            result = run_processor(
                package_dir,
                package="TestData\nraise RuntimeError('injected')\n#",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("package", result.stderr.lower())
            self.assertEqual(snapshot(package_dir), before)
            self.assertFalse((package_dir / "_conversion.py").exists())
            self.assertFalse((package_dir / "flatdatas_helper.py").exists())


if __name__ == "__main__":
    unittest.main()
