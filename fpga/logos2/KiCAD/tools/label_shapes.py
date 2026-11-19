#!/usr/bin/env python3
"""Set every global label's shape (input / output / bidirectional) and text size in the module schematic.

The shape is the signal's direction relative to the sheet the label sits on: a label on the sheet whose part
drives the net is an output there and an input where the net is received; bidirectional nets are bidirectional
at both ends. Directions are declared per net below from what the parts do (the FPGA symbol's pins are all
bidirectional, so they say nothing). Idempotent; run from fpga/logos2/KiCAD after rework_module.py.
"""
import glob, re, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from ksch import *

PRJ = pathlib.Path(__file__).resolve().parents[1] / 'thriller'
FPGA_SHEETS = {'th_userA', 'th_userB', 'th_fpga'}
SIZE = '1.143'   # 45 mil

# Nets with the FPGA at one end: direction as seen from the FPGA.
FPGA_OUT = {
    'FLASH_CS_N', 'FLASH_CLK_USR', 'CFG_CLK', 'CFG_DONE',
    'TPM_CLK', 'TPM_CS_N', 'TPM_MOSI', 'TPM_RST_N',
    'PSRAM_CLK', 'PSRAM_CS_N',
    'RTC_SCL',
    'ETH_MDC', 'ETH_TXD0', 'ETH_TXD1', 'ETH_TXEN', 'ETH_RST_N',
    'SD_CLK',
    'HOST_UART_TX', 'SENS_TX', 'SENS_PWR_EN', 'SEAL_OUT', 'PWR_HOLD',
    'AUD1_MCLK', 'AUD1_BCLK', 'AUD1_FS', 'AUD1_DACIN', 'AUD1_SCL',
    'AUD2_MCLK', 'AUD2_BCLK', 'AUD2_FS', 'AUD2_DACIN', 'AUD2_SCL',
    'LCD_SCK', 'LCD_MOSI', 'LCD_DC', 'LCD_CS_N', 'LCD_RST_N', 'LCD_BL_PWM',
    'TP_SCL', 'SPK_PWM', 'JTAG_TDO',
}
FPGA_IN = {
    'SYS_CLK', 'TPM_MISO', 'TPM_PIRQ_N', 'RTC_INT_N',
    'ETH_REFCLK', 'ETH_CRS_DV', 'ETH_RXD0', 'ETH_RXD1', 'ETH_RXER',
    'SD_CD_N', 'HOST_UART_RX', 'SENS_RX', 'SENS_DET',
    'PB_N', 'TAMPER_N', 'SEAL_IN', 'CARRIER_ID', 'PGOOD',
    'AUD1_ADCOUT', 'AUD2_ADCOUT', 'TP_INT_N',
    'CLK_REF10M', 'CLK_SI0', 'CLK_SI1',
    'JTAG_TCK', 'JTAG_TMS', 'JTAG_TDI',
    'CFG_MODE0', 'CFG_MODE1', 'CFG_MODE2', 'FPGA_RST_N', 'IO_STATUS_C',
    'ADC_5V_MON', 'VCCB', 'VCCADC',          # analog and supply inputs to the FPGA
}
FPGA_BIDI = {
    'FLASH_D0', 'FLASH_D1', 'FLASH_D2', 'FLASH_D3',
    'PSRAM_D0', 'PSRAM_D1', 'PSRAM_D2', 'PSRAM_D3',
    'RTC_SDA', 'ETH_MDIO', 'SD_CMD', 'SD_D0', 'SD_D1', 'SD_D2', 'SD_D3',
    'AUD1_SDA', 'AUD2_SDA', 'TP_SDA', 'CFG_INIT_N',
} | {f'GPIO{i}' for i in range(32)}

# Nets that do not reach the FPGA: the sheet whose part drives them.
SOURCE = {
    '+5V_IN': 'th_conn', 'VBAT_CELL': 'th_conn', 'PB_N_AO': 'th_conn',
    'RTC_INT_N_AO': 'th_base',                     # RTC alarm, to power control and to J1
    'ETH_TXP': 'th_ext', 'ETH_TXN': 'th_ext', 'ETH_LED1': 'th_ext', 'ETH_LED2': 'th_ext',
    'ETH_RXP': 'th_conn', 'ETH_RXN': 'th_conn',
}

def shape_for(net, sheet):
    if net in FPGA_BIDI: return 'bidirectional'
    if net in FPGA_OUT: return 'output' if sheet in FPGA_SHEETS else 'input'
    if net in FPGA_IN: return 'input' if sheet in FPGA_SHEETS else 'output'
    if net in SOURCE: return 'output' if sheet == SOURCE[net] else 'input'
    return None

def main():
    unknown = set(); counts = {}
    for f in sorted(glob.glob(str(PRJ / '*.kicad_sch'))):
        sheet = pathlib.Path(f).stem
        text = open(f).read(); sh = Sheet(text); changed = False
        for l in sh.items('global_label'):
            net = unq(l[1]); shp = shape_for(net, sheet)
            if shp is None: unknown.add(net); continue
            sp = find1(l, 'shape')
            if sp[1] != shp: sp[1] = shp; changed = True
            font = find1(find1(l, 'effects'), 'font'); sz = find1(font, 'size')
            if sz[1:] != [SIZE, SIZE]: sz[1:] = [SIZE, SIZE]; changed = True
            counts[shp] = counts.get(shp, 0) + 1
        if changed: open(f, 'w').write(sh.dump())
    print('shapes:', counts)
    if unknown: print('UNCLASSIFIED (left as they were):', sorted(unknown)); sys.exit(1)

if __name__ == '__main__':
    main()
