
import bytestory


def test_one_byte():
    class OneByte(bytestory.ByteStory):
        a = bytestory.Char

    one_byte = OneByte(b'\x11')

    assert one_byte.a == 0x11

    assert one_byte.pack() == b'\x11'

    assert OneByte(a=0x33).pack() == b'\x33'


def test_referenced():
    class Inner(bytestory.ByteStory):
        data = bytestory.UChar()

    class Outer(bytestory.ByteStory):
        prefix = bytestory.UChar()
        inner = Inner
        suffix = bytestory.UChar()

    outer = Outer(b'pds')

    assert outer.prefix == b'p'[0]
    assert outer.inner.data == b'd'[0]
    assert outer.suffix == b's'[0]

    assert outer.pack() == b'pds'


def test_nested():
    class Outer(bytestory.ByteStory):
        prefix = bytestory.UChar()

        class Inner(bytestory.ByteStory):
            data = bytestory.UChar()

        suffix = bytestory.UChar()

    outer = Outer(b'pds')

    assert outer.prefix == b'p'[0]
    assert outer.Inner.data == b'd'[0]
    assert outer.suffix == b's'[0]

    assert outer.pack() == b'pds'


def test_bytestory_unpack_protocol():
    class OneByte(bytestory.ByteStory):
        a = bytestory.Char

    one_byte, end_offset = OneByte.unpack(b'a')

    assert one_byte.a == b'a'[0]
    assert end_offset == 1


def test_two_bytes():
    class TwoBytes(bytestory.ByteStory):
        a = bytestory.Char
        b = bytestory.Char

    two_bytes = TwoBytes(b'\x11\x55')

    assert two_bytes.a == 0x11
    assert two_bytes.b == 0x55

    assert two_bytes.pack() == b'\x11\x55'


def test_multi_bytes():
    class NBytes(bytestory.ByteStory):
        length = bytestory.Char()
        b = bytestory.FixedLengthBytes(length)

    nb1 = NBytes(b'\x03\xaa\xbb\xcc')

    assert nb1.length == 3
    assert nb1.b == b'\xaa\xbb\xcc'

    assert nb1.pack() == b'\x03\xaa\xbb\xcc'


def test_bytes_ending():
    class ZeroTermBytes(bytestory.ByteStory):
        b = bytestory.BytesEnding(b'\0')

    ztb = ZeroTermBytes(b'\xaa\xbb\0\xcc')
    assert ztb.b == b'\xaa\xbb\0'

    assert ztb.pack() == b'\xaa\xbb\0'


def test_multiple_zero_term_bytes():
    from typing import List

    class ZeroTermBytes(bytestory.ByteStory):
        b = bytestory.BytesEnding(b'\0')

    class MultipleZeroTermBytes(bytestory.ByteStory):
        length = bytestory.Char()
        bs: List[ZeroTermBytes] = bytestory.Multiple(length, ZeroTermBytes)

    result = MultipleZeroTermBytes(b'\x03one\0two\0three\0')
    assert result.bs[0].b == b'one\0'
    assert result.bs[1].b == b'two\0'
    assert result.bs[2].b == b'three\0'

    assert result.pack() == b'\x03one\0two\0three\0'


def test_branching():
    class TypedUnion(bytestory.ByteStory):
        typechar = bytestory.Char()

        @bytestory.branch
        def __then__(so_far):
            if so_far['typechar'] == 1:
                return TUChar
            else:
                return TUZeroTermBytes

    class TUChar(TypedUnion):
        char = bytestory.UChar()

    class TUZeroTermBytes(TypedUnion):
        bs = bytestory.BytesEnding(b'\0')

    tu_char = TypedUnion(b'\x01\xaa')
    assert tu_char.typechar == 1
    assert isinstance(tu_char, TUChar)
    assert tu_char.char == 0xaa

    assert tu_char.pack() == b'\x01\xaa'

    tu_ztb = TypedUnion(b'\x02bytes\0')
    assert tu_ztb.typechar == 2
    assert isinstance(tu_ztb, TUZeroTermBytes)
    assert tu_ztb.bs == b'bytes\0'

    assert tu_ztb.pack() == b'\x02bytes\0'


def test_when():
    class DataUChar(bytestory.ByteStory):
        char = bytestory.UChar()

    class DataZTB(bytestory.ByteStory):
        bs = bytestory.BytesEnding(b'\0')

    class TypedUnion(bytestory.ByteStory):
        typechar = bytestory.Char()
        Data = bytestory.when(typechar == 1, DataUChar, DataZTB)

    tu_char = TypedUnion(b'\x01\xaa')
    assert tu_char.typechar == 1
    assert isinstance(tu_char.Data, DataUChar)
    assert tu_char.Data.char == 0xaa

    assert tu_char.pack() == b'\x01\xaa'

    tu_ztb = TypedUnion(b'\x02bytes\0')
    assert tu_ztb.typechar == 2
    assert isinstance(tu_ztb.Data, DataZTB)
    assert tu_ztb.Data.bs == b'bytes\0'

    assert tu_ztb.pack() == b'\x02bytes\0'
