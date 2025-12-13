from typing import TypedDict
from plotly import graph_objs
from event_model.documents import DataKey, Event, EventPage, EventDescriptor, RunStart
from bluesky_web_plots.structures.base_structure import BaseStructure
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T", bound=BaseStructure)


class BaseFigure(ABC, Generic[T]):
    structure: T | None
    _figure: graph_objs.Figure

    def add_layout(self): ...

    def figure(self) -> graph_objs.Figure:
        return self._figure

    def run_start(self, run_start: RunStart):
        raise NotImplementedError(
            f"{type(self)} does not have a method to parse run_start data."
        )

    def descriptor(self, descriptor: EventDescriptor):
        raise NotImplementedError(
            f"{type(self)} does not have a method to parse descriptor data."
        )

    def datakey(self, name: str, datakey: DataKey):
        raise NotImplementedError(
            f"{type(self)} does not have a method to parse datakey data."
        )

    def event(self, event: Event):
        raise NotImplementedError(
            f"{type(self)} does not have a method to parse event data."
        )

    def event_page(self, event_page: EventPage):
        raise NotImplementedError(
            f"{type(self)} does not have a method to parse eventpage data."
        )
