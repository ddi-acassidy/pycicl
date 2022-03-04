from __future__ import annotations

from abc import ABC, abstractmethod, abstractproperty
import pyvisa



class Instrument(ABC):
    _name: str = ""

    @property
    def name(self):
        """The name of the instrument"""
        return self._name


