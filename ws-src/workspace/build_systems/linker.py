import enum


class Linker(enum.Enum):
    LD = "ld"
    GOLD = "gold"
    LLD = "lld"
