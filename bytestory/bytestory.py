from typing import Tuple

from .fields import Field

__all__ = ('ByteStory', 'ByteStoryMeta', 'branch')


class ByteStoryMeta(type, Field):
    def __new__(mcs, name, bases, dct):
        for key in dct:
            try:
                if isinstance(dct[key], type) and issubclass(dct[key], Field):
                    dct[key] = dct[key]()
                if isinstance(dct[key], Field) and not hasattr(dct[key], '__name__'):
                    dct[key].__name__ = key
            except:
                pass
        cls = super().__new__(mcs, name, bases, dct)
        return cls

    def pack(cls, self, *, parent_object: object = None, as_name: str = None) -> bytes:
        return cls.pack(self, parent_object=parent_object, as_name=as_name)

    def unpack(cls, b: bytes, /, *, so_far=None, offset=0, as_name=None) -> Tuple['ByteStory', int]:
        result = cls(b, offset)
        return result, offset + len(result)


class ByteStory(metaclass=ByteStoryMeta):
    def __new__(cls, b: bytes = None, offset=0, /, **kwargs):
        if b is None:
            self = super().__new__(cls)
            for k, v in kwargs.items():
                setattr(self, k, v)
            return self
        start_offset = offset
        so_far = {}
        continues = True
        while continues:
            continues = False
            for k, v in cls.__dict__.items():
                if getattr(v, '__is_bytestory_branch__', False):
                    new_cls = v(so_far)
                    if new_cls is None:
                        break
                    else:
                        cls = new_cls
                        continues = True
                        break
                elif k.startswith("_"):
                    continue
                elif isinstance(v, Field):
                    if k not in so_far:
                        data, offset = v.unpack(b, so_far=so_far, offset=offset, as_name=k)
                        so_far[k] = data
        self = super().__new__(cls)
        for k, v in so_far.items():
            setattr(self, k, v)
        self._start_offset = start_offset
        self._end_offset = offset
        return self

    def __repr__(self):
        parts = []
        for k in self.__dict__:
            if k in self.__class__.__dict__:
                parts.append(f"{k}={self.__dict__[k]!r}")
        return f"{self.__class__.__name__}({', '.join(parts)})"

    def pack(self, *, parent_object=None, as_name=None):
        parts = []
        for cls in reversed(self.__class__.mro()):
            for k, v in cls.__dict__.items():
                if k in self.__dict__:
                    parts.append(v.pack(getattr(self, k), parent_object=self, as_name=k))
        return b''.join(parts)

    def __len__(self):
        return self._end_offset - self._start_offset


def branch(func, /):
    func.__is_bytestory_branch__ = True
    return func
