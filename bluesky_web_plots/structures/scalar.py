from typing import TypedDict
from .base_structure import BaseStructure
from enum import StrEnum


class PlotAgainst(StrEnum):
    TIME = "TIME"
    SEQ_NUM = "SEQ_NUM"


class Scalar(BaseStructure):
    plot_against: PlotAgainst
