import numbers
import struct
from abc import ABC, abstractmethod
from functools import partial
from typing import TypeVar, Tuple, Generic, List, Protocol, Union, Optional, Callable

__all__ = (
    'Field',
    'Char', 'UChar', 'Int16', 'UInt16', 'Int32', 'UInt32', 'Int64', 'UInt64',
    'Multiple', 'FixedLengthBytes', 'BytesEnding', 'when',
)

T = TypeVar('T')


def expand_value(value, so_far):
    value = getattr(value, 'value', value)
    if callable(value):
        value = value(so_far)
    return value


class Primitive:
    CMPSS = {
        '<=': (-1, 0),
        '>=': (0, 1),
        '!=': (-1, 1),
        '<>': (-1, 1),
        '==': (0,),
        '=': (0,),
        '<': (-1,),
        '>': (1,),
    }

    def __init__(self, lhs, rhs, symbol):
        self.lhs = lhs
        self.rhs = rhs
        assert symbol in ['<=', '>=', '!=', '<>', '==', '=', '<', '>']
        self.cmps = self.CMPSS[symbol]

    def value(self, so_far) -> bool:
        lhs = expand_value(self.lhs, so_far)
        rhs = expand_value(self.rhs, so_far)
        cmp = -1 if lhs < rhs else 0 if lhs == rhs else 1
        return cmp in self.cmps


class Valuable(Protocol):
    def value(self, so_far: dict) -> Union[int, float]: ...


class SumOfProductOperatorMixin:
    products: List[Tuple[Union[Valuable, int, float], ...]]

    def __add__(self, other):
        if isinstance(other, SumOfProduct):
            return SumOfProduct([*self.products, *other.products])
        else:
            return SumOfProduct([(self,), (other,)])

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        if isinstance(other, SumOfProduct):
            return SumOfProduct([*self.products, *((-1, *p) for p in other.products)])
        else:
            return SumOfProduct([(self,), (other,)])

    def __rsub__(self, other):
        if isinstance(other, SumOfProduct):
            return SumOfProduct([*other.products, *((-1, *p) for p in self.products)])
        else:
            return SumOfProduct([(self,), (other,)])

    def __mul__(self, other):
        if isinstance(other, SumOfProduct):
            return SumOfProduct([(*s, *o) for s in self.products for o in other.products])
        elif isinstance(other, (int, float)):
            return SumOfProduct([(*s, other) for s in self.products])

    def __rmul__(self, other):
        return self.__mul__(other)

    def __lt__(self, other):
        return Primitive(self, other, '<')

    def __gt__(self, other):
        return Primitive(self, other, '>')

    def __le__(self, other):
        return Primitive(self, other, '<=')

    def __ge__(self, other):
        return Primitive(self, other, '>=')

    def __eq__(self, other):
        return Primitive(self, other, '==')

    def __ne__(self, other):
        return Primitive(self, other, '<>')


class Field(Generic[T], ABC):
    __name__: str

    @abstractmethod
    def pack(self, data, *, parent_object: object = None, as_name: str = None) -> bytes:
        pass

    @abstractmethod
    def unpack(self, b: bytes, /, *, so_far: dict = None, offset: int = 0, as_name: str = None) -> Tuple[T, int]:
        pass

    def value(self, so_far: dict, *, as_name: str = None):
        name = as_name or self.__name__
        return so_far[name]


class ReaderIntMixin(SumOfProductOperatorMixin):
    @property
    def products(self):
        return [(self,)]


class StructField(Field):
    def __init__(self, struct_format):
        self.format = struct_format

    def pack(self, data, *, parent_object=None, as_name=None):
        return struct.pack(self.format, data)

    def unpack(self, b, /, *, so_far=None, offset=0, as_name=None):
        unpacked = struct.unpack_from(self.format, b, offset)
        end_offset = offset + struct.calcsize(self.format)
        return self.post_unpack(unpacked), end_offset

    def post_unpack(self, unpacked):
        return unpacked[0]


class Char(StructField, ReaderIntMixin, Field[int]):
    """Signed Char"""

    def __init__(self):
        super().__init__("b")


class UChar(StructField, ReaderIntMixin, Field[int]):
    """Unsigned Char"""

    def __init__(self):
        super().__init__("B")


class Int16(StructField, ReaderIntMixin, Field[int]):
    """Signed Int16"""

    def __init__(self, endian="@"):
        assert endian in "@=<>!", "Endian must be one of @=<>!"
        super().__init__(f"{endian}h")


class UInt16(StructField, ReaderIntMixin, Field[int]):
    """Unsigned Int16"""

    def __init__(self, endian="@"):
        assert endian in "@=<>!", "Endian must be one of @=<>!"
        super().__init__(f"{endian}H")


class Int32(StructField, ReaderIntMixin, Field[int]):
    """Signed Int32"""

    def __init__(self, endian="@"):
        assert endian in "@=<>!", "Endian must be one of @=<>!"
        super().__init__(f"{endian}i")


class UInt32(StructField, ReaderIntMixin, Field[int]):
    """Unsigned Int32"""

    def __init__(self, endian="@"):
        assert endian in "@=<>!", "Endian must be one of @=<>!"
        super().__init__(f"{endian}I")


class Int64(StructField, ReaderIntMixin, Field[int]):
    """Signed Int64"""

    def __init__(self, endian="@"):
        assert endian in "@=<>!", "Endian must be one of @=<>!"
        super().__init__(f"{endian}q")


class UInt64(StructField, ReaderIntMixin, Field[int]):
    """Unsigned Int64"""

    def __init__(self, endian="@"):
        assert endian in "@=<>!", "Endian must be one of @=<>!"
        super().__init__(f"{endian}Q")


T2 = TypeVar('T2')


class Multiple(Field[List[T2]]):
    """Read multiple fields of same type"""

    def __init__(self, length, base_type: Field[T2]):
        self.length = length
        self.base_type = base_type

    def pack(self, data, *, parent_object=None, as_name=None):
        name = as_name or self.__name__
        if parent_object is not None:
            assert getattr(parent_object, name) is data
            length = expand_value(self.length, parent_object.__dict__)
            assert len(data) == length, f"expect length {length}, actual length {len(data)}"
        return b''.join(self.base_type.pack(datum) for datum in data)

    def unpack(self, b, /, *, so_far=None, offset=0, as_name=None) -> Tuple[List[T2], int]:
        length = expand_value(self.length, so_far)
        lst = []
        n = offset
        for _ in range(length):
            t, n = self.base_type.unpack(b, so_far=so_far, offset=n, as_name=as_name)
            lst.append(t)
        return lst, n


class AliasField(Field, Generic[T]):
    def __init__(self, apparent_type):
        self.apparent_type = apparent_type

    def pack(self, data, *, parent_object=None, as_name=None):
        return self.apparent_type.pack(data, parent_object=parent_object, as_name=as_name)

    def unpack(self, b, /, *, so_far=None, offset=0, as_name=None):
        unpacked, end_offset = self.apparent_type.unpack(b, so_far=so_far, offset=offset, as_name=as_name)
        return self.post_unpack(unpacked), end_offset

    def post_unpack(self, unpacked):
        return unpacked[0]


class FixedLengthBytes(AliasField[bytes]):
    def __init__(self, length):
        super().__init__(Multiple(length, UChar()))

    def post_unpack(self, unpacked):
        return bytes(unpacked)


class BytesEnding(Field[List[int]]):
    def __init__(self, ending: bytes):
        self.ending = ending

    def pack(self, data: List[int], *, parent_object=None, as_name=None):
        result = bytes(data)
        assert result.endswith(self.ending)
        return result

    def unpack(self, b, /, *, so_far=None, offset=0, as_name=None):
        ending = list(self.ending)
        from collections import deque
        dq = deque(maxlen=len(ending))
        g = []
        while True:
            dq.append(b[offset])
            g.append(b[offset])
            offset += 1
            if list(dq) == ending:
                return bytes(g), offset


class Nothing(Field[None]):
    def __init__(self):
        pass

    def pack(self, data, *, parent_object=None, as_name=None):
        return b''

    def unpack(self, b, /, *, so_far=None, offset=0, as_name=None) -> Tuple[None, int]:
        return None, offset


T3 = TypeVar('T3')
T3E = TypeVar('T3E')


class When(Field[Optional[Union[T3, T3E]]]):
    def __init__(self, primitive, then_type: T3, else_type: T3E = None):
        self.primitive = primitive
        self.then_type = then_type
        if else_type is None:
            else_type = Nothing()
        self.else_type = else_type

    def otherwise(self, else_type: T3E):
        self.else_type = else_type

    def pack(self, data, *, parent_object=None, as_name=None):
        name = as_name or self.__name__
        then = expand_value(self.primitive, parent_object.__dict__)
        expect_type = self.then_type if then else self.else_type
        if parent_object is not None:
            assert getattr(parent_object, name) is data
            assert isinstance(data, expect_type), f"expected type {expect_type}, got {data.__class__}"
        return expect_type.pack(data)

    def unpack(self, b, /, *, so_far=None, offset=0, as_name=None) -> Tuple[Optional[Union[T3, T3E]], int]:
        then = expand_value(self.primitive, so_far)
        if then:
            return self.then_type.unpack(b, so_far=so_far, offset=offset, as_name=as_name)
        elif self.else_type is not None:
            return self.else_type.unpack(b, so_far=so_far, offset=offset, as_name=as_name)


def when(primitive, then_type: T3 = None, else_type: T3E = None) -> Union[When, Callable[[T3], When]]:
    if then_type is None:
        return partial(When, primitive)
    else:
        return When(primitive, then_type, else_type)


class SumOfProduct(SumOfProductOperatorMixin):
    def __init__(self, products):
        self.products = self.simplify(products)

    @staticmethod
    def simplify(products: List[Tuple[Union[Valuable, int, float], ...]]):
        from collections import defaultdict
        bases = []
        coefficients = defaultdict(int)
        for product in products:
            coefficient = 1
            variables = []
            for p in product:
                if isinstance(p, (int, float)):
                    coefficient *= p
                else:
                    variables.append(p)
            vt = tuple(variables)
            bases.append(vt)
            coefficients[vt] += coefficient
        result: List[Tuple[Union[Valuable, int, float], ...]] = []
        for vt in bases:
            if coefficients[vt] == 1:
                result.append(vt)
            elif coefficients[vt] != 0:
                result.append((coefficients[vt], *vt))
        return result

    def value(self, so_far):
        result_of_sum = 0
        for products in self.products:
            result_of_product = 1
            for value in products:
                result_of_product *= expand_value(value, so_far)
            result_of_sum += result_of_product
        return result_of_sum
