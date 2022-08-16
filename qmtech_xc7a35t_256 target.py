#!/usr/bin/env python3

#
# This file is part of LiteX-Boards.
#
# Copyright (c) 2021 Giray Pultar <giray@pultar.org>

# SPDX-License-Identifier: BSD-2-Clause

import os
import argparse

from migen import *

from platforms import qmtech_xc7a35t_256

from litex.soc.cores.clock import *
from litex.soc.integration.soc_core import *
from litex.soc.integration.soc import *
from litex.soc.integration.soc_sdram import *
from litex.soc.integration.builder import *
from led_from_uart import *
from litedram.modules import MT41J128M16
from litedram.phy import GENSDRPHY
from litex.soc.cores.led import LedChaser
from litex.soc.cores.spi import SPIMaster
from litesdcard.phy import SDPHY
from litesdcard.core import SDCore

from litex.build.generic_platform import *

# CRG ----------------------------------------------------------------------------------------------

class _CRG(Module):
    def __init__(self, platform, sys_clk_freq):
        self.rst = Signal()
        self.clock_domains.cd_sys    = ClockDomain()
        self.clock_domains.cd_sys2x  = ClockDomain(reset_less=True)
        self.clock_domains.cd_sys4x  = ClockDomain(reset_less=True)
        self.clock_domains.cd_idelay = ClockDomain()

        # # #

        toolchain = "vivado"
        if toolchain == "vivado":
            self.submodules.pll = pll = S7MMCM(speedgrade=-1)
        else:
            self.submodules.pll = pll = S7PLL(speedgrade=-1)
        self.comb += pll.reset.eq(self.rst)
        pll.register_clkin(platform.request("clk50"), 50e6)
        pll.create_clkout(self.cd_sys,    sys_clk_freq)
        pll.create_clkout(self.cd_sys4x,  4*sys_clk_freq)
        pll.create_clkout(self.cd_idelay, 200e6)
        platform.add_false_path_constraints(self.cd_sys.clk, pll.clkin) # Ignore sys_clk to pll.clkin path created by SoC's rst.

        self.submodules.idelayctrl = S7IDELAYCTRL(self.cd_idelay)
        
        # sdram_clock
        sdram_clock = platform.request("sdram_clock")


# BaseSoC ------------------------------------------------------------------------------------------

class BaseSoC(SoCCore):
    def __init__(self, sys_clk_freq=int(50e6),  **kwargs):
        platform = qmtech_xc7a35t_256.Platform()

        # SoCCore ----------------------------------------------------------------------------------
        SoCCore.__init__(self, platform, sys_clk_freq,
            ident          = "LiteX SoC on QMTECH XC7A35T 256MB SDRAM",
            ident_version  = True,
            **kwargs)


        # #  SDRAM ----------------------------------------------------------------------------------

        ## not tested
        if not self.integrated_main_ram_size:
            self.submodules.sdrphy = GENSDRPHY(platform.request("sdram"), sys_clk_freq)
            self.add_sdram("sdram",
                phy           = self.sdrphy,
                module        = MT41J128M16(sys_clk_freq, "1:1"),
                l2_cache_size = kwargs.get("l2_size", 8192)
            )

        # CRG --------------------------------------------------------------------------------------
        self.submodules.crg = _CRG(platform, sys_clk_freq)

        # SDCARD --------------------------------------------------------------------------------------
 
        def add_spi_sdcard(self, software_debug=True, spi_clk_freq=25e6):
            spisdcard_pads = self.platform.request("spisdcard")
            
            if hasattr(spisdcard_pads, "rst"):
                self.comb += spisdcard_pads.rst.eq(0)
                
            self.submodules.spisdcard = SPIMaster(spisdcard_pads, 8, self.sys_clk_freq, 25e6)
            self.submodules.spisdcard.add_clk_divider()
            
            # Debug.
            if software_debug:
                self.add_constant("SPISDCARD_DEBUG")
                
            self.add_csr("spisdcard")


        def add_sdcard(self, software_debug=True ):
            sdcard_pads = self.platform.request("sdcard")
            
            if hasattr(sdcard_pads, "rst"):
                self.comb += sdcard_pads.rst.eq(0)
                
            self.submodules.sd_phy = SDPHY(sdcard_pads, self.platform.device, 25e6)
            self.submodules.sdcore = SDCore(self.sd_phy)
            
            # Debug.
            if software_debug:
                self.add_constant("SDCARD_DEBUG")

            self.add_csr("sd_phy")

        # Leds -------------------------------------------------------------------------------------
        pads = platform.request_all("user_led")

        import pprint
        
        pp = pprint.PrettyPrinter()
        pp.pprint(platform)

        self.submodules.leds = LedFromUart(
            pads=pads, uart=pads
            )
        self.add_csr("leds")
        
# Build --------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LiteX SoC on QMTECH XC7A35T 256MB SDRAM")
    parser.add_argument("--build",         action="store_true", help="Build bitstream")
    parser.add_argument("--load",          action="store_true", help="Load bitstream")
    parser.add_argument("--sys-clk-freq",  default=50e6,       help="System clock frequency (default: 50MHz)")
    ethopts = parser.add_mutually_exclusive_group()
    sdopts = parser.add_mutually_exclusive_group()
    sdopts.add_argument("--with-spi-sdcard",        action="store_true", help="Enable SPI-mode SDCard support")
    sdopts.add_argument("--with-sdcard",            action="store_true", help="Enable SDCard support")
    viopts = parser.add_mutually_exclusive_group()

    builder_args(parser)
    soc_core_args(parser)
    args = parser.parse_args()

    s_args  = soc_core_argdict(args)
    s_args["with_uart"]=True

    soc = BaseSoC(
        sys_clk_freq  = int(float(args.sys_clk_freq)),
        **s_args)

    if args.with_spi_sdcard:
        soc.add_spi_sdcard()
    if args.with_sdcard:
        soc.add_sdcard()
    


    builder = Builder(soc, **builder_argdict(args))
    builder.build(run=args.build)

    if args.load:
        prog = soc.platform.create_programmer()
        prog.load_bitstream(os.path.join(builder.gateware_dir, soc.build_name + ".bit"))

if __name__ == "__main__":
    main()
