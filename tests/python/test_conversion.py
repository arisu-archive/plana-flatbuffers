import importlib.util
import math
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
CONVERSION_PATH = ROOT / ".scripts" / "python_conversion.py"


def load_conversion():
    if not CONVERSION_PATH.exists():
        raise AssertionError(f"missing conversion runtime: {CONVERSION_PATH}")
    spec = importlib.util.spec_from_file_location("python_conversion", CONVERSION_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ConversionTests(unittest.TestCase):
    def test_create_table_key_matches_go_compatibility_vector(self):
        conversion = load_conversion()

        self.assertEqual(
            conversion.create_table_key("BlendInfo"),
            bytes.fromhex("88d55a64b5c6ea3d"),
        )

    def test_table_name_normalization_matches_go_generator(self):
        conversion = load_conversion()

        self.assertEqual(
            conversion.normalize_table_name("AddressableBlackListExcelTable"),
            "AddressableBlackList",
        )

    def test_integer_codecs_match_go_compatibility_vectors(self):
        conversion = load_conversion()
        key = bytes.fromhex("88d55a64b5c6ea3d")
        cases = (
            (conversion.decrypt_int32, conversion.encrypt_int32, 123456789, 1661016221),
            (
                conversion.decrypt_int64,
                conversion.encrypt_int64,
                -123456789012345,
                -4461579582404233969,
            ),
            (
                conversion.decrypt_uint32,
                conversion.encrypt_uint32,
                4000000000,
                2318531976,
            ),
            (
                conversion.decrypt_uint64,
                conversion.encrypt_uint64,
                12345678901234567890,
                10862241644271755098,
            ),
        )

        for decrypt, encrypt, plain, encoded in cases:
            with self.subTest(codec=decrypt.__name__):
                self.assertEqual(decrypt(encoded, key), plain)
                self.assertEqual(encrypt(plain, key), encoded)

    def test_integer_zero_preserves_go_sentinel_behavior(self):
        conversion = load_conversion()
        key = bytes.fromhex("88d55a64b5c6ea3d")

        self.assertEqual(conversion.decrypt_int32(0, key), 0)
        self.assertEqual(conversion.encrypt_int32(0, key), 0)

    def test_integer_codecs_cover_flatbuffers_narrow_widths(self):
        conversion = load_conversion()
        key = bytes.fromhex("88d55a64b5c6ea3d")
        cases = (
            ("int8", 42, -94),
            ("uint8", 42, 162),
            ("int16", 12345, -6735),
            ("uint16", 60000, 16360),
        )

        for codec, plain, encoded in cases:
            with self.subTest(codec=codec):
                self.assertTrue(
                    hasattr(conversion, f"decrypt_{codec}"),
                    f"missing decrypt_{codec}",
                )
                self.assertTrue(
                    hasattr(conversion, f"encrypt_{codec}"),
                    f"missing encrypt_{codec}",
                )
                decrypt = getattr(conversion, f"decrypt_{codec}")
                encrypt = getattr(conversion, f"encrypt_{codec}")
                self.assertEqual(decrypt(encoded, key), plain)
                self.assertEqual(encrypt(plain, key), encoded)

    def test_string_codec_is_directional_and_unicode_safe(self):
        conversion = load_conversion()
        key = bytes.fromhex("88d55a64b5c6ea3d")

        self.assertEqual(conversion.encrypt_string("Arona", key), "ydUoZNrGhD3p1Q==")
        self.assertEqual(conversion.decrypt_string(b"ydUoZNrGhD3p1Q==", key), "Arona")
        self.assertEqual(
            conversion.decrypt_string(conversion.encrypt_string("アロナ", key), key),
            "アロナ",
        )

    def test_invalid_base64_string_is_left_readable(self):
        conversion = load_conversion()
        key = bytes.fromhex("88d55a64b5c6ea3d")

        self.assertEqual(conversion.decrypt_string(b"not-base64", key), "not-base64")

    def test_base64_string_accepts_crlf_like_go(self):
        conversion = load_conversion()
        key = bytes.fromhex("88d55a64b5c6ea3d")

        self.assertEqual(
            conversion.decrypt_string(b"ydUoZN\r\nrGhD3p1Q==", key),
            "Arona",
        )

    def test_float_codec_reverses_positive_wire_values(self):
        conversion = load_conversion()
        positive_modulus_key = bytes.fromhex("88d55a64b5c6ea3d")
        negative_modulus_key = b"\x05\0\0\0\0\0\0\0"

        self.assertEqual(conversion.decrypt_float64(60000.0, positive_modulus_key), 1.0)
        self.assertEqual(conversion.encrypt_float64(1.0, positive_modulus_key), 60000.0)
        self.assertEqual(
            conversion.decrypt_float64(100000.0, negative_modulus_key), -2.0
        )
        self.assertEqual(
            conversion.encrypt_float64(-2.0, negative_modulus_key), 100000.0
        )

    def test_float32_codec_retains_float32_precision(self):
        conversion = load_conversion()
        key = bytes.fromhex("88d55a64b5c6ea3d")

        encoded = conversion.encrypt_float32(1.25, key)
        decoded = conversion.decrypt_float32(encoded, key)

        self.assertTrue(math.isclose(decoded, 1.25, rel_tol=1e-6))


if __name__ == "__main__":
    unittest.main()
