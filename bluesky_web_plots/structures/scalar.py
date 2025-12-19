from .base_structure import Base
from enum import StrEnum


class PlotAgainst(StrEnum):
    TIME = "TIME"
    SEQ_NUM = "SEQ_NUM"


class Scalar(Base):
    plot_against: PlotAgainst
