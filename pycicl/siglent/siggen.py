from __future__ import annotations

from abc import ABC, abstractmethod, abstractproperty
import pycicl.instrument as instrument
import pycicl.scpi as scpi
import parse


class SiglentProperty:
    """The SDG does something weird to bind commands together so we have to do this"""

    def __init__(self, command, name, formatter: scpi.SCPIFormatter = scpi.format_str, offset=0):
        self._command = command
        self._name = name
        self._offset = offset

        self.formatter = formatter

    @property
    def command(self):
        return self._command

    @property
    def name(self):
        return self._name

    def eval_command(self, obj):
        if callable(self._command):
            return self._command(obj)
        else:
            return self._command

    def __get__(self, obj, objtype=None):
        # query the resource for the value and parse it
        response = obj.resource.query(f'{self.eval_command(obj)}?').strip()
        values = response.split(' ')[1]
        split = values.split(',')

        if self._name is None:
            raw = split[self._offset]
        else:
            d = dict(zip(split[self._offset::2], split[(self._offset + 1)::2]))
            raw = d[self._name]

        value = self.formatter.parse(raw)
        return value

    def __set__(self, obj, value):

        output = self.formatter.format(value)

        if self._name is None:
            command = f'{self.eval_command(obj)} {output}'

        else:
            command = f'{self.eval_command(obj)} {self._name}, {output}'

        obj.resource.write(command)


class SiglentSDG(scpi.SCPIInstrument, instrument.SigGen):
    class Channel(scpi.SCPIChild, instrument.SigGen.Channel):
        @staticmethod
        def _mk_channel(name):
            return lambda obj: name.format(obj.index)

        def get_bswv(self):
            response = self.resource.query(f'C{self.index}:BSWV?').strip()
            values = response.split(' ')[1]
            split = values.split(',')
            return dict(zip(split[0::2], split[1::2]))

        def set_bswv(self, key, value):
            self.resource.write(f'C{self.index}:BSWV {key}, {value}')

        _format_volt = scpi.SCPIFormatter('{:f}V')
        _format_hz = scpi.SCPIFormatter('{:f}HZ')
        _format_inverted = scpi.SCPIFormatter(parser=lambda v: v.upper() == 'INVT', formatter=lambda v: 'INVT' if v else 'NOR')

        type = SiglentProperty(_mk_channel('C{:d}:BSWV'), 'WVTP')
        vpp = SiglentProperty(_mk_channel('C{:d}:BSWV'), 'AMP', _format_volt)
        frequency = SiglentProperty(_mk_channel('C{:d}:BSWV'), 'FRQ', _format_hz)
        phase = SiglentProperty(_mk_channel('C{:d}:BSWV'), 'PHSE', scpi.format_float)
        offset = SiglentProperty(_mk_channel('C{:d}:BSWV'), 'OFST', _format_volt)
        low = SiglentProperty(_mk_channel('C{:d}:BSWV'), 'LLEV', _format_volt)
        high = SiglentProperty(_mk_channel('C{:d}:BSWV'), 'LLEV', _format_volt)

        output = SiglentProperty(_mk_channel('C{:d}:OUTP'), None, scpi.format_onoff, offset=0)
        load = SiglentProperty(_mk_channel('C{:d}:OUTP'), 'LOAD', offset=1)
        invert = SiglentProperty(_mk_channel('C{:d}:OUTP'), 'PLRT', _format_inverted, offset=1)

        def __init__(self, parent: SiglentSDG, index: int):
            super(instrument.SigGen.Channel).__init__(parent, index)
            super().__init__(parent)
