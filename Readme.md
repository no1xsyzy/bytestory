# ByteStory

Unpacking from bytes and packing into bytes, with an object interface.

## Install

```commandline
pip install bytestory
```

## Usage

Unpacking from bytes

```python
import bytestory

class OneByte(bytestory.ByteStory):
    a = bytestory.Char

one_byte = OneByte(b'\x11')

assert one_byte.a == 0x11
```

Packing into bytes

```python
import bytestory

class OneByte(bytestory.ByteStory):
    a = bytestory.Char

one_byte = OneByte(a=0x11)

assert one_byte.pack() == b'\x11'
```

More examples at [tests/test_bytestory.py](tests/test_bytestory.py).
