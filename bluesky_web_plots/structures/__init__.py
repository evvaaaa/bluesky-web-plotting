from typing import Unpack

from .base_structure import Base as Base
from .scalar import Scalar as Scalar


def unpack_structures(*structures: Unpack[tuple[Base]]):
    return {
        "WEB_PLOT_STRUCTURES": {
            structure["name"]: structure for structure in structures
        }
    }
