from __future__ import annotations

import click
import time
import numpy as np
import pandas as pd
import pyvisa
from pycicl.rigol.oscilloscope import RigolMSO5
from pycicl.siglent.siggen import SiglentSDG

@click.command()
@click.option('--siggen_id', '-g', prompt='DS1022 VISA ID', help='VISA ID of the DS1022 signal generator')
@click.option('--scope_id', '-s', prompt='DS2302A VISA ID', help='VISA ID of the DS2302A oscilloscope')
@click.option('--output', '-o', default='linearity.csv', help='Output CSV file', type=click.Path(exists=False, dir_okay=False, writable=True))
@click.option('--frequency', '-f', default=13.56e6, help='frequency')
@click.option('--min_vrms', '-m', default=0.3535, help='Starting Vrms')
@click.option('--max_vrms', '-x', default=3.535, help='Ending Vrms')
@click.option('--count', '-c', default=20, help='Harmonic steps')
@click.option('--load', '-l', default=50, type=float, help='Current load')
def run(siggen_id, scope_id, output, frequency, min_vrms, max_vrms, count, load):
    rm = pyvisa.ResourceManager()

    siggen = SiglentSDG(siggen_id, rm)
    scope = RigolMSO5(scope_id, rm)

    print(f'Signal Generator found: {siggen.id}')
    print(f'Oscilloscope found: {scope.id}')
    # print(siggen.ch2.voltage)
    # print(siggen.ch2.voltage_high)
    # # # siggen.ch2.output = True
    # # print(siggen.ch2.output)
    #
    #
    # siggen.channels[0].voltage = 1
    # # siggen.reset()

    # List of frequencies in logarithmic space, plus all extra frequencies we requested
    voltages = np.linspace(min_vrms, max_vrms, count)
    siggen.ch1.enabled = True
    siggen.ch1.voltage_unit = 'VRMS'

    data = []

    scope.clear_measurements()

    def format_freq(freq):
        if freq is None:
            return ''
        elif freq < 1e3:
            return f'{freq:.3f} Hz'
        elif freq < 1e6:
            return f'{freq/1e3:.3f} kHz'
        elif freq < 1e9:
            return f'{freq/1e6:.3f} Mhz'
        else:
            return f'{freq/1e9:.3f} Ghz'

    with click.progressbar(voltages, label='Performing voltage sweep') as bar:
        for v in bar:
            pvrms1 = scope.ch1.pvrms
            pvrms2 = scope.ch2.pvrms
            pvrms3 = scope.ch3.pvrms

            pvrms1.display = True
            pvrms2.display = True
            pvrms3.display = True
            scope.statistics = True


            siggen.ch1.frequency = frequency
            siggen.ch1.load = '50'
            # periods = 2
            # scope.timebase = (periods / f) / scope.timebase_divisions
            # time.sleep(0.1)
            siggen.ch1.vrms = v # 50 ohm impedence
            time.sleep(0.1)

            scope.autoscale()
            scope.reset_statistics()

            time.sleep(4)
            vout = pvrms3.avg
            if vout > 10e10 or vout < 2e-3:
                scope.ch3.scale = 1e-3


            time.sleep(6)
            vin = pvrms1.avg
            iin = vin / load
            vout_i = pvrms2.avg
            vout_v = pvrms3.avg
            gain_i = vout_i / iin
            gain_v = vout_v / vin
            data.append((frequency, v, vin, iin, vout_i, vout_v, gain_i, gain_v))

    print('Current harmonics:')
    for row in data:
        print(f'{row[2]}, {row[4]}')

    print('Voltage harmonics:')
    for row in data:
        print(f'{row[3]}, {row[5]}')

    df = pd.DataFrame(data=data, columns=['Frequency', 'VinTarget', 'Vin', 'Iin', 'Vout_I', 'Vout_V', 'Gain_I', 'Gain_V'])
    df.to_csv(output)
    print(f'wrote to {output}')


if __name__ == '__main__':
    run()
