from .base_structure import Base
from enum import StrEnum


class View(StrEnum):
    SURFACE = "SURFACE"
    SLICE = "SLICE"


class Scalar(Base):
    view: View
