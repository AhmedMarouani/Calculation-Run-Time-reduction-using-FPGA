#
# This file is part of LiteX-Boards.
#
# Copyright (c) 2021 Giray Pultar <giray@pultar.org>
# Copyright (c) 2015-2019 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

from litex.build.generic_platform import *
from litex.build.xilinx import XilinxPlatform, VivadoProgrammer
from litex.build.openocd import OpenOCD

# IOs ----------------------------------------------------------------------------------------------

_io = [
    # Clk / Rst   # Not Tested
    ("clk50",    0, Pins("N11"), IOStandard("LVCMOS33")),
    # ("cpu_reset", 0, Pins("H10"), IOStandard("LVCMOS33")), # Or L9 ??

    # Leds  # Not Tested
    ("user_led", 0, Pins("C8"),  IOStandard("LVCMOS33")),

    # Buttons  # Not Tested
    ("user_btn", 0, Pins("A8"), IOStandard("LVCMOS33")),

    # Serial  # Not Tested
    ("serial", 0,
        Subsignal("rx", Pins("M16")),
        Subsignal("tx", Pins("N13")),
        IOStandard("LVCMOS33")
    ),

    # SDRAM  # Not Tested
    ("sdram_clock", 0, Pins("B14"),IOStandard("LVCMOS33"), Misc("SLEW=FAST")),
    ("sdram", 0,
        Subsignal("a", Pins(
            "C13 A15 C12 C11  A9  B9 A10 B10",
            "B11 A12 B15 B12")),
        Subsignal("dq", Pins(
            "H12 H13 J15 H14 J16 H16 G14 G12",
            "C16 D15 D16 E15 E16 F15 G15 G16")),
        Subsignal("ba",  Pins("D13 C14")),
        Subsignal("we_n",  Pins("F14")),
        Subsignal("ras_n", Pins("E13")),
        Subsignal("cas_n", Pins("F13")),
        Subsignal("cs_n",  Pins("D14")),
        Subsignal("dm", Pins("F12 B16")),# DQML, DQMH
        Subsignal("cke",   Pins("A14")),
        Misc("SLEW=FAST"),
        IOStandard("LVCMOS33"),
     ),

    # SDCard
    ("spisdcard", 0,
        Subsignal("clk",  Pins("N16")),
        Subsignal("mosi", Pins("R12"), Misc("PULLMODE=UP")),
        Subsignal("cs_n", Pins("P16"), Misc("PULLMODE=UP")),
        Subsignal("miso", Pins("R13"), Misc("PULLMODE=UP")),
        Misc("SLEW=FAST"),
        IOStandard("LVCMOS33"),
    ),
    ("sdcard", 0,
        Subsignal("clk", Pins("N16")),
        Subsignal("data", Pins("R13 T15 R16 P16"), Misc("PULLUP True")),
        Subsignal("cd", Pins("P14")),
        Subsignal("cmd", Pins("R12"), Misc("PULLUP True")),
        Misc("SLEW=FAST"),
        IOStandard("LVCMOS33")
    ),

]

# Connectors ---------------------------------------------------------------------------------------

_connectors = [
    # Pins on connector are labeled from 1, so first pin is a dummy
    # U7 located close to jtag connector.
    ("U7",
     "- - - - - - - ", #  Pins 1,2,5,6 are GND. Pins 3,4 are VCCO_34_35, connected collectively to A6,B3,D7,E4,F1,J2,M3,R4,T1
     "B7 A7 B6 B5 E6 K5 J5 J4 G5 G4" # Connectors Pin 7-16
     "C7 C6 D6 D4 A5 A4 B4 A3 D4 C4 C3 C2 B2 A2 C1 B1", # Connectors Pin 17-32
     "E2 D1 E3 D3 F5 E5 F2 E1 F4 F3 G2 G1 H2 H1 K1 J1", # Connectors Pin 33-48
     "H5 H4 J3 H3 K3 K2 L4 M4 N3 N2", # Connectors Pin 49-60
     "- - - - ", # pins 61-62 are GND, pins 63-64 are 5V_IN
     ),
    # U8 located close to 5V connector
    ("U8",
     "- - - - - - " #  Pins 1,2,5,6 are GND. Pins 3,4 are 3V3
     "M16 N13 N14 N16 P15 P16 R15 R16 T14 T15" # Connectors Pin 7-16
     "M12 P14 T13 R13 T12 R12 N12 P13 K12 K13 P10 P11 N9 P9 T10 R11", # Connectors Pin 17-32
     "T9 R10 T8 R8 T7 R7 T5 R6 M6 R5 N6 P6 L5 P5 T4 T3", # Connectors Pin 33-48
     "R3 T2 R2 R1 M5 N4 P4 P3 N1 P1 M2 M1", # Connectors Pin 49-60
     "- - - - ", # pins 61-62 are GND, pins 63-64 are 5V_IN
     ),
]

# Platform -----------------------------------------------------------------------------------------

class Platform(XilinxPlatform):
    default_clk_name   = "clk50"
    default_clk_period = 1e9/50e6

    def __init__(self, toolchain="vivado"):
        device = "xc7a35tftg256-1"
        XilinxPlatform.__init__(self, device, _io, _connectors, toolchain=toolchain)
        self.toolchain.bitstream_commands = \
            ["set_property BITSTREAM.CONFIG.SPI_BUSWIDTH 4 [current_design]"]
        self.toolchain.additional_commands = \
            ["write_cfgmem -force -format bin -interface spix4 -size 16 "
             "-loadbit \"up 0x0 {build_name}.bit\" -file {build_name}.bin"]
        self.add_platform_command("set_property INTERNAL_VREF 0.675 [get_iobanks 34]")
        self.add_platform_command("set_property CLOCK_DEDICATED_ROUTE FALSE [get_nets clk50_IBUF]")

    def create_programmer(self):
        # bscan_spi = "bscan_spi_xc7a35t.bit"
        # return OpenOCD("openocd_xc7_ft2232.cfg", bscan_spi)
        return VivadoProgrammer()

    def do_finalize(self, fragment):
        XilinxPlatform.do_finalize(self, fragment)
        from litex.build.xilinx import symbiflow
        self.add_period_constraint(self.lookup_request("clk50", loose=True), 1e9/50e6)# No ba...  Subsignal("ba",    Pins("R1 P4 P2"),
