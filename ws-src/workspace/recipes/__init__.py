from .recipe import Recipe
from .llvm import LLVM
from .z3 import Z3
from .klee_uclibc import KLEE_UCLIBC
from .minisat import MINISAT
from .stp import STP
from .klee import KLEE

from typing import Type, Dict

all: Dict[str, Type[Recipe]] = {
    name: cls
    for name, cls in globals().items() if isinstance(cls, type) and issubclass(cls, Recipe) and not cls == Recipe
}
"""all true subclasses of 'Recipe' that are in the current module"""
