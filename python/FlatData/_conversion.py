"""Conversion support for encrypted FlatData FlatBuffers object APIs."""

from __future__ import annotations

import base64
import binascii
from contextvars import ContextVar
import copy
from functools import wraps
import struct

import flatbuffers
import xxhash


_UINT32_MASK = 0xFFFFFFFF


def normalize_table_name(name: str) -> str:
    return name.replace("ExcelTable", "").replace("Excel", "")


def _uint32(value: int) -> int:
    return value & _UINT32_MASK


class _MT19937:
    _STATE_SIZE = 624
    _PERIOD = 397

    def __init__(self, seed: int) -> None:
        self._state = [0] * self._STATE_SIZE
        self._state[0] = _uint32(seed)
        self._index = 0
        for index in range(1, self._STATE_SIZE):
            previous = self._state[index - 1]
            self._state[index] = _uint32(
                1812433253 * (previous ^ (previous >> 30)) + index
            )

    def _twist(self) -> None:
        for index in range(self._STATE_SIZE):
            value = (self._state[index] & 0x80000000) | (
                self._state[(index + 1) % self._STATE_SIZE] & 0x7FFFFFFF
            )
            twisted = self._state[(index + self._PERIOD) % self._STATE_SIZE] ^ (
                value >> 1
            )
            if value & 1:
                twisted ^= 0x9908B0DF
            self._state[index] = _uint32(twisted)

    def uint32(self) -> int:
        if self._index == 0:
            self._twist()

        value = self._state[self._index]
        value ^= value >> 11
        value ^= (value << 7) & 0x9D2C5680
        value ^= (value << 15) & 0xEFC60000
        value ^= value >> 18
        self._index = (self._index + 1) % self._STATE_SIZE
        return _uint32(value)

    def bytes(self, length: int) -> bytes:
        result = bytearray()
        while len(result) < length:
            value = self.uint32() >> 1
            for _ in range(4):
                if len(result) == length:
                    break
                result.append(value & 0xFF)
                value >>= 8
        return bytes(result)


def create_table_key(name: str) -> bytes:
    seed = xxhash.xxh32(name.encode("utf-8")).intdigest()
    return _MT19937(seed).bytes(8)


def _xor_bytes(value: bytes, key: bytes) -> bytes:
    if not value or not key:
        return value
    return bytes(byte ^ key[index % len(key)] for index, byte in enumerate(value))


def _convert_integer(value: int, key: bytes, width: int, signed: bool) -> int:
    if value == 0 or not key:
        return value
    mask = (1 << (width * 8)) - 1
    raw = (int(value) & mask).to_bytes(width, "little")
    return int.from_bytes(_xor_bytes(raw, key), "little", signed=signed)


def decrypt_int8(value: int, key: bytes) -> int:
    return _convert_integer(value, key, 1, True)


def encrypt_int8(value: int, key: bytes) -> int:
    return _convert_integer(value, key, 1, True)


def decrypt_uint8(value: int, key: bytes) -> int:
    return _convert_integer(value, key, 1, False)


def encrypt_uint8(value: int, key: bytes) -> int:
    return _convert_integer(value, key, 1, False)


def decrypt_int16(value: int, key: bytes) -> int:
    return _convert_integer(value, key, 2, True)


def encrypt_int16(value: int, key: bytes) -> int:
    return _convert_integer(value, key, 2, True)


def decrypt_uint16(value: int, key: bytes) -> int:
    return _convert_integer(value, key, 2, False)


def encrypt_uint16(value: int, key: bytes) -> int:
    return _convert_integer(value, key, 2, False)


def decrypt_int32(value: int, key: bytes) -> int:
    return _convert_integer(value, key, 4, True)


def encrypt_int32(value: int, key: bytes) -> int:
    return _convert_integer(value, key, 4, True)


def decrypt_int64(value: int, key: bytes) -> int:
    return _convert_integer(value, key, 8, True)


def encrypt_int64(value: int, key: bytes) -> int:
    return _convert_integer(value, key, 8, True)


def decrypt_uint32(value: int, key: bytes) -> int:
    return _convert_integer(value, key, 4, False)


def encrypt_uint32(value: int, key: bytes) -> int:
    return _convert_integer(value, key, 4, False)


def decrypt_uint64(value: int, key: bytes) -> int:
    return _convert_integer(value, key, 8, False)


def encrypt_uint64(value: int, key: bytes) -> int:
    return _convert_integer(value, key, 8, False)


def _calculate_modulus(key: bytes) -> int:
    if not key:
        return 1
    modulus = key[0] % 10
    if modulus <= 1:
        modulus = 7
    if key[0] & 1:
        modulus = -modulus
    return modulus


def decrypt_float64(value: float, key: bytes) -> float:
    modulus = _calculate_modulus(key)
    if value > 0 and modulus != 1:
        return value / modulus / 10000
    return value


def encrypt_float64(value: float, key: bytes) -> float:
    modulus = _calculate_modulus(key)
    encoded = value * modulus * 10000
    if encoded > 0 and modulus != 1:
        return encoded
    return value


def _float32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


def decrypt_float32(value: float, key: bytes) -> float:
    value = _float32(value)
    modulus = _calculate_modulus(key)
    if value > 0 and modulus != 1:
        value = _float32(value / _float32(modulus))
        return _float32(value / _float32(10000))
    return value


def encrypt_float32(value: float, key: bytes) -> float:
    value = _float32(value)
    modulus = _calculate_modulus(key)
    encoded = _float32(_float32(value * _float32(modulus)) * _float32(10000))
    if encoded > 0 and modulus != 1:
        return encoded
    return value


def decrypt_string(value: str | bytes, key: bytes) -> str:
    if not value:
        return ""
    original = (
        value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value
    )
    if isinstance(value, bytes):
        encoded = value.replace(b"\r", b"").replace(b"\n", b"")
    else:
        encoded = value.replace("\r", "").replace("\n", "")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        return original
    decoded = _xor_bytes(raw, key)
    decoded = decoded[: len(decoded) // 2 * 2]
    return decoded.decode("utf-16-le", errors="replace")


def encrypt_string(value: str, key: bytes) -> str:
    if not value:
        return ""
    raw = value.encode("utf-16-le")
    return base64.b64encode(_xor_bytes(raw, key)).decode("ascii")


_ACTIVE_TABLE_KEY = ContextVar("plana_flatbuffer_table_key", default=None)


def _convert_model_value(value, codec_name: str, key: bytes, encrypt: bool):
    if value is None:
        return None
    direction = "encrypt" if encrypt else "decrypt"
    codec = globals()[f"{direction}_{codec_name}"]
    return codec(value, key)


def _convert_model_fields(model, fields, key: bytes, encrypt: bool) -> None:
    for field_name, codec_name, is_vector in fields:
        value = getattr(model, field_name)
        if value is None:
            continue
        if is_vector:
            converted = [
                _convert_model_value(item, codec_name, key, encrypt) for item in value
            ]
        else:
            converted = _convert_model_value(value, codec_name, key, encrypt)
        setattr(model, field_name, converted)


def install_object_api(model_type, table_name: str, fields) -> None:
    """Install directional conversion around a generated FlatBuffers `*T` API."""

    if getattr(model_type, "_plana_conversion_installed", False):
        return

    original_unpack = model_type._UnPack
    original_pack = model_type.Pack

    @wraps(original_unpack)
    def unpack_with_conversion(self, table):
        table_key = _ACTIVE_TABLE_KEY.get()
        token = None
        if table_key is None:
            table_key = create_table_key(normalize_table_name(table_name))
            token = _ACTIVE_TABLE_KEY.set(table_key)
        try:
            original_unpack(self, table)
            _convert_model_fields(self, fields, table_key, encrypt=False)
        finally:
            if token is not None:
                _ACTIVE_TABLE_KEY.reset(token)

    @wraps(original_pack)
    def pack_with_conversion(self, builder):
        table_key = _ACTIVE_TABLE_KEY.get()
        token = None
        if table_key is None:
            table_key = create_table_key(normalize_table_name(table_name))
            token = _ACTIVE_TABLE_KEY.set(table_key)
        try:
            converted_model = copy.copy(self)
            _convert_model_fields(converted_model, fields, table_key, encrypt=True)
            return original_pack(converted_model, builder)
        finally:
            if token is not None:
                _ACTIVE_TABLE_KEY.reset(token)

    @classmethod
    def from_bytes(cls, data, offset=0):
        return cls.InitFromPackedBuf(data, offset)

    def to_bytes(self):
        builder = flatbuffers.Builder(0)
        builder.Finish(self.Pack(builder))
        return bytes(builder.Output())

    model_type._UnPack = unpack_with_conversion
    model_type.Pack = pack_with_conversion
    model_type.from_bytes = from_bytes
    model_type.to_bytes = to_bytes
    model_type._plana_conversion_installed = True
