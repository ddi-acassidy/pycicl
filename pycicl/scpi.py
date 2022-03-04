from __future__ import annotations

from abc import ABC, abstractmethod, abstractproperty
from parse import Parser
import pyvisa
import time

import pycicl.instrument as instrument

MBR = pyvisa.resources.MessageBasedResource


class SCPIFormatter:
    def __init__(self, parser=None, formatter=None, bidirectional=True):
        self.parser = parser
        if bidirectional and formatter is None:
            self.formatter = parser
        else:
            self.formatter = formatter

        if type(self.parser) is str:
            # compile a parser object
            self.parser = Parser(self.parser)

        assert ((self.parser is None) or (type(self.parser) is Parser) or (callable(self.parser)))
        assert (self.formatter is None or type(self.formatter) is str or callable(self.formatter))

    def format(self, value) -> str:
        """
        Format the input values as a string
        :param value: input values to format
        :return: The resulting formatted string
        """
        if self.formatter is None:
            # formatter is None, so treat it as a no-op.
            # if multiple inputs are passed, return them as a space-seperated list.
            # All values are converted to strings using str()
            return str(value)
        elif callable(self.formatter):
            # formatter is a function, so pass the input values and return the result
            return self.formatter(value)
        else:
            # formatter is a format string, so pass it through format()
            return self.formatter.formatter(value)

    def parse(self, raw: str):
        """
        Parse the input value and return the result
        :param raw: Input string to parse
        :return: The resulting value(s) from the parse operation
        """
        if self.parser is None:
            # parser is None, so treat it as a no-op
            return raw
        elif callable(self.parser):
            # parser is a function, so pass the input value and return the result
            return self.parser(raw)
        elif type(self.parser) is Parser:
            # parser is a Parser object from a formatter string, so run the parse operation
            result = self.parser.parse(raw.strip())
            # Parser returns a Result object containing a tuple of values
            # If there's only one match, we should return it on its own. otherwise, return the tuple
            if len(result.fixed) == 0:
                raise ValueError(f'Unable to parse value "{raw}" with parser "{self.parser}"')
            elif len(result.fixed) == 1:
                return result.fixed[0]
            else:
                return result.fixed
        else:
            raise TypeError('Parser is of unknown type')


format_str = SCPIFormatter()
format_onoff = SCPIFormatter(parser=lambda v: v.upper() in ('ON', '1'), formatter=lambda v: 'ON' if v else 'OFF')
format_int = SCPIFormatter('{:d}')
format_real = SCPIFormatter('{:e}')


class SCPIProperty:
    def __init__(self, name, readable: bool = True, writable: bool = True, delay=None,
                 formatter: SCPIFormatter = format_str, suffix=None, memoized=False):
        self._name = name
        self._readable = readable
        self._writable = writable
        self._delay = delay
        self._suffix = suffix
        self._memoized = memoized
        self._memo_value = None

        self.formatter = formatter

    @property
    def name(self):
        return self._name

    @property
    def readable(self):
        return self._readable

    @property
    def writable(self):
        return self._writable

    def eval_name(self, obj):
        if callable(self._name):
            return self._name(obj)
        else:
            return self._name

    def eval_suffix(self, obj):
        if callable(self._suffix):
            return self._suffix(obj)
        else:
            return self._suffix

    def __get__(self, obj, objtype=None):
        if not self._readable:
            raise PermissionError('Reading is not allowed for this SCPI property')

        # if we are memoizing this property and have a cached value, return it
        if self._memoized and self._memo_value is not None:
            return self._memo_value

        # query the resource for the value and parse it
        query = f'{self.eval_name(obj)}?'
        if self._suffix is not None:
            query += ' ' + self.eval_suffix(obj)
        raw = obj.resource.query(query, delay=self._delay).strip()
        value = self.formatter.parse(raw)

        # if we are momoizing this property, set the cached value
        if self._memoized and self._memo_value is None:
            self._memo_value = value

        return value

    def __set__(self, obj, value):
        if not self._writable:
            raise PermissionError('Writing is not allowed for this SCPI property')

        # if we are momoizing this property, set the cached value
        if self._memoized and self._memo_value is None:
            self._memo_value = value

        output = self.formatter.format(value)
        command = f'{self.eval_name(obj)}'
        if self._suffix is not None:
            command += ' ' + self.eval_suffix(obj)
        command += ' ' + output
        obj.resource.write(command)


class SCPIObject(ABC):
    _resource: MBR = None

    @property
    def resource(self):
        return self._resource


class SCPIChild(SCPIObject, ABC):
    def __init__(self, parent: SCPIObject):
        self.parent = parent

    @property
    def resource(self):
        return self.parent.resource


class SCPIInstrument(SCPIObject, instrument.Instrument, ABC):
    id = SCPIProperty('*IDN', writable=False)

    def __init__(self, address, rm):
        self.address = address
        self._resource = rm.open_resource(address)

    def reset(self) -> None:
        """Reset the instrument to factory settings"""
        self._resource.write('*RST')
