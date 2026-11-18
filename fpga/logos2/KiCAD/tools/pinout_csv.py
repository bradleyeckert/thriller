#!/usr/bin/env python3
"""Write hw/module-pinout.csv (the H11 pinout contract) and the FPGA ball table from the assignments in rework_module.py.
Run from fpga/logos2/KiCAD: python3 tools/pinout_csv.py"""
import csv, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import rework_module as rm

GROUP = [('+5V_IN', '5 V in', 'Power'), ('GND', 'Ground', 'Power'), ('VBAT_CELL', 'RTC backup', 'Power'),
         ('HOST_UART', 'Host UART', 'Ciphertext frames; plaintext status in recovery'), ('JTAG', 'JTAG', 'Fixture only'),
         ('SD_', 'MicroSD', 'Ciphertext'), ('ETH_', 'Ethernet MDI / LEDs', 'Ciphertext (PHY link)'),
         ('SENS_', 'Sensor link', "MAC'd frames"), ('PB_N_AO', 'Power button', 'Control'), ('TAMPER_N', 'Enclosure switch', 'Control'),
         ('SEAL_', 'Seal loop', 'Control'), ('CARRIER_ID', 'Carrier identity', 'Control'), ('TPM_PIRQ_N', 'TPM interrupt (observation)', 'Control'),
         ('RTC_INT_N_AO', 'RTC alarm (observation)', 'Control'), ('PWR_HOLD', 'Power hold (observation)', 'Control'),
         ('AUD', 'I2S / CODEC I2C', 'Plaintext'), ('LCD_', 'LCD SPI', 'Plaintext'), ('TP_', 'Touch I2C', 'Plaintext'), ('SPK_PWM', 'Speaker', 'Plaintext'),
         ('CLK_', 'Application clocks', 'Clock, untrusted'), ('GPIO', 'Carrier GPIO', 'Application')]

def classify(net):
    for pre, grp, cls in GROUP:
        if net.startswith(pre): return grp, cls
    return '', ''

def main():
    fa, balls = rm.fpga_assignment()
    ball_of = {a[1]: b for b, a in fa.items() if a[0] == 'g'}
    bank_of = {b: v[0] for b, v in balls.items()}
    out = pathlib.Path(rm.ROOT).parents[2] / 'hw' / 'module-pinout.csv'
    with open(out, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['connector', 'contact', 'net', 'group', 'class', 'fpga_ball', 'fpga_bank', 'note'])
        for conn, A in (('J1', rm.j1_assignment()), ('J2', rm.j2_assignment())):
            for p in range(1, 81):
                a = A[str(p)]
                if a[0] == 'nc':
                    w.writerow([conn, p, '', 'Reserved', '', '', '', 'unconnected on both sides']); continue
                net = a[1]; grp, cls = classify(net)
                b = ball_of.get(net, '')
                note = ''
                if net in ('RTC_INT_N_AO', 'PWR_HOLD', 'VBAT_CELL', 'PB_N_AO'): note = 'not an FPGA pin; see th_base/th_power'
                if net.startswith('ETH_'): note = 'PHY pin (th_ext)'
                if net.startswith('JTAG'): note = 'route on the fixture carrier only'
                w.writerow([conn, p, net, grp, cls, b, bank_of.get(b, ''), note])
    print('wrote', out)
    # FPGA ball table next to the pinout json
    out2 = pathlib.Path(rm.ROOT).parent / 'pinout324-assignment.csv'
    with open(out2, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['ball', 'bank', 'pin_name', 'net'])
        for b in sorted(balls, key=lambda k: (k[0], int(k[1:]))):
            a = fa.get(b, ('nc',))
            w.writerow([b, balls[b][0], balls[b][1], a[1] if a[0] != 'nc' else ''])
    print('wrote', out2)

if __name__ == '__main__':
    main()
