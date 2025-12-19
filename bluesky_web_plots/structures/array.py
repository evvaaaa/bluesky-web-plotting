from .base_structure import Base
from enum import StrEnum


class View(StrEnum):
    SURFACE = "SURFACE"
    SLICE = "SLICE"


class Array(Base):
    view: View
