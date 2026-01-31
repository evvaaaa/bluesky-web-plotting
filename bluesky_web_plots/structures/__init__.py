from typing import Unpack

from .base_structure import Base as Base
from .scalar import Scalar as Scalar
from .array import Array as Array
from plotly import graph_objs as go


def unpack_structures(
    *structures: Base, static_figures: dict[str, go.Figure] | None = None
):
    static_figures = static_figures or {}
    serialzed_static_figures = {n: v.to_json() for n, v in static_figures.items()}
    return {
        "BLUESKY_LIVE_PLOTS": {
            "STRUCTURES": structures,
            "SERIALISED_PLOT": serialzed_static_figures,
        }
    }
