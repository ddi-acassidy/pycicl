from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List
import pycicl.instrument as instrument


class Oscilloscope(instrument.Instrument, ABC):
    """
    An object representing a generic oscilloscope
    """

    channel_count = None

    def __init__(self):
        # setup channels
        self.channels = (self.Channel(self, i) for i in range(self.channel_count))

        # setup ch1, ch2, etc. attributes for easy access
        for i, c in enumerate(self.channels, start=1):
            setattr(self, f'ch{i}', c)

    class Channel(ABC):
        """
        An object representing a single channel of an oscilloscope
        """

        def __init__(self, parent, index):
            self._parent = parent
            self._index = index

        @property
        def parent(self) -> Oscilloscope:
            """The oscilloscope this channel is a part of"""
            return self._parent

        @property
        def index(self) -> int:
            """The channel number, generally starting at 1"""
            return self._index



