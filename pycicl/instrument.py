from __future__ import annotations

import math
from abc import ABC, abstractmethod, abstractproperty
import pyvisa


class Instrument(ABC):
    name: str = ""


class MultiChannelInstrument(Instrument, ABC):
    """
    An instrument with multiple channels
    """
    channel_count = None

    class Channel(ABC):
        """
        A single channel of an instrument
        """

        def __init__(self, parent, index):
            self._parent = parent
            self._index = index

        @property
        def parent(self):
            """The instrument this channel is a part of"""
            return self._parent

        @property
        def index(self) -> int:
            """The channel number, generally starting at 1"""
            return self._index

    def __init__(self):
        # setup channels
        self.channels = (self.Channel(self, i) for i in range(self.channel_count))

        # setup ch1, ch2, etc. attributes for easy access
        for i, c in enumerate(self.channels, start=1):
            setattr(self, f'ch{i}', c)


class Oscilloscope(MultiChannelInstrument, ABC):
    pass


class SigGen(MultiChannelInstrument, ABC):
    class Channel(MultiChannelInstrument.Channel, ABC):
        frequency = None
        vpp = None

        @property
        def vrms(self) -> float:
            return self.vpp / (2 * math.sqrt(2))

        @vrms.setter
        def vrms(self, value: float):
            self.vpp = value * (2 * math.sqrt(2))
