from __future__ import annotations

from abc import ABC, abstractmethod, abstractproperty
import pycicl.oscilloscope as oscilloscope
import pycicl.scpi as scpi


class RigolMSO5(scpi.SCPIInstrument, oscilloscope.Oscilloscope):
    class Measurement(scpi.SCPIChild):
        def __init__(self, parent: RigolMSO5, name: str, src):
            super().__init__(parent)
            self.name = name
            self.src = src
            try:
                iter(self.src)
            except(TypeError):
                self.src = (self.src,)

        def enable(self):
            self.resource.write(f'MEASURE:ITEM {self._suffix()}')

        def _suffix(self):
            return ",".join((self.name, *self.src))

        @staticmethod
        def _mk_statistic(statistic):
            return lambda obj: ",".join((statistic, obj.name, *obj.src))

        now = scpi.SCPIProperty('MEASURE:ITEM', suffix=lambda obj: ",".join((obj.name, *obj.src)), formatter=scpi.format_real, writable=False)
        max = scpi.SCPIProperty('MEASURE:STATISTIC:ITEM', suffix=_mk_statistic('MAXIMUM'), formatter=scpi.format_real, writable=False)
        min = scpi.SCPIProperty('MEASURE:STATISTIC:ITEM', suffix=_mk_statistic('MINIMUM'), formatter=scpi.format_real, writable=False)
        avg = scpi.SCPIProperty('MEASURE:STATISTIC:ITEM', suffix=_mk_statistic('AVERAGE'), formatter=scpi.format_real, writable=False)

    class Channel(scpi.SCPIChild, oscilloscope.Oscilloscope.Channel, ABC):
        @staticmethod
        def _mk_channel(name):
            return lambda obj: name.format(obj.index)

        bwlimit = scpi.SCPIProperty(_mk_channel('CHANNEL{:d}:BWLIMIT'))
        coupling = scpi.SCPIProperty(_mk_channel('CHANNEL{:d}:COUPLING'))
        display = scpi.SCPIProperty(_mk_channel('CHANNEL{:d}:DISPLAY'), formatter=scpi.format_onoff)
        invert = scpi.SCPIProperty(_mk_channel('CHANNEL{:d}:INVERT'), formatter=scpi.format_onoff)
        offset = scpi.SCPIProperty(_mk_channel('CHANNEL{:d}:OFFSET'), formatter=scpi.format_real)
        tcalibrate = scpi.SCPIProperty(_mk_channel('CHANNEL{:d}:TCALIBRATE'), formatter=scpi.format_real)
        scale_min = 500e-6
        scale_max = 10
        scale = scpi.SCPIProperty(_mk_channel('CHANNEL{:d}:SCALE'), formatter=scpi.format_real)
        probe = scpi.SCPIProperty(_mk_channel('CHANNEL{:d}:PROBE'))  # add support for discretes?
        units = scpi.SCPIProperty(_mk_channel('CHANNEL{:d}:UNITS'))
        vernier = scpi.SCPIProperty(_mk_channel('CHANNEL{:d}:VERNIER'), formatter=scpi.format_onoff)
        position = scpi.SCPIProperty(_mk_channel('CHANNEL{:d}:POSITION'), formatter=scpi.format_real)

        def __init__(self, parent: RigolMSO5, index: int):
            super(oscilloscope.Oscilloscope.Channel).__init__(parent, index)
            super().__init__(parent)

            measurements = [
                'VMAX', 'VMIN', 'VPP', 'VTOP', 'VBASE', 'VAMP', 'VAVG', 'VRMS', 'OVERSHOOT', 'PRESHOOT', 'MAREA', 'MPAREA', 'PERIOD', 'FREQUENCY', 'RTIME',
                'FTIME', 'PWIDTH', 'NWIDTH', 'PDUTY', 'NDUTY', 'TVMAX', 'TVMIN', 'PSLEWRATE', 'NSLEWRATE', 'VUPPER', 'VMID', 'VLOWER', 'VARIANCE', 'PVRMS',
                'PPULSES', 'NPULSES', 'PEDGES', 'NEDGES'
            ]

            for name in measurements:
                setattr(self, name.lower(), RigolMSO5.Measurement(parent, name, self.index))

    timebase = scpi.SCPIProperty('TIMEBASE:SCALE', formatter=scpi.format_real)
    statistics = scpi.SCPIProperty('MEASURE:STATISTIC:DISPLAY', formatter=scpi.format_onoff)

    def reset_statistics(self):
        self.resource.write('MEASURE:STATISTIC:RESET')

    def clear_measurements(self):
        self.resource.write('MEASURE:CLEAR')

    def autoscale(self):
        self.resource.write('AUTOSCALE')

    def clear(self):
        self.resource.write('CLEAR')

    def measure_phase(self, channel_A, channel_B, rising_A=True, rising_B=True):
        fr_a = 'R' if rising_A else 'F'
        fr_b = 'R' if rising_B else 'F'
        return RigolMSO5.Measurement(self, f'{fr_a}{fr_b}PHASE', (channel_A, channel_B))

    def measure_delay(self, channel_A, channel_B, rising_A=True, rising_B=True):
        fr_a = 'R' if rising_A else 'F'
        fr_b = 'R' if rising_B else 'F'
        return RigolMSO5.Measurement(self, f'{fr_a}{fr_b}DELAY', (channel_A, channel_B))
