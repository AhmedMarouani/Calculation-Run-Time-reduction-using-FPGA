#!/usr/bin/env python3
from migen import *
from migen.genlib.divider import Divider
from migen.genlib.fsm import FSM

class Calculator(Module):
    def __init__(self, width, depth):

        # Submodules
        storage = Memory(width, depth)
        self.specials += storage
        self.submodules.divider = divider = Divider(width)

        # storage Signals
        self.stored = Signal()
        self.recalled = Signal()
        self.where_to_store_or_recall = Signal(width)
        self.number_to_store = Signal(width)
        self.number_recalled = Signal(width)
        self.store_now_active = Signal()
        self.recall_now_active = Signal()

        # calculation Signals
        self.calculate_now_active = Signal()
        self.summed_number = Signal(width)
        self.calculated = Signal()
        self.result = Signal(width)

        # division Signals
        self.start_division = Signal()
        self.division_finished = Signal()
        self.result = Signal(width)
        self.leftover = Signal(width)
        self.dividing = Signal()
        self.divide_by = Signal(width)

        #internal signals
        write_port = storage.get_port(write_capable = True)
        read_port = storage.get_port(has_re=True)
        number_recalled_internal = Signal(width)
        counter = Signal(width)

        ###

        self.comb += [
            write_port.adr.eq(self.where_to_store_or_recall),
            read_port.adr.eq(self.where_to_store_or_recall),
            write_port.dat_w.eq(self.number_to_store),
            self.number_recalled.eq(write_port.dat_r)
        ]


        self.sync += [
            If(self.store_now_active & ~self.recall_now_active,
                self.stored.eq(1),
                write_port.we.eq(1),
            ).Else(
                self.stored.eq(0),
                write_port.we.eq(0)
            )
        ]


        self.sync += [
            If(self.recall_now_active & ~self.store_now_active,
                self.recalled.eq(1),
                read_port.re.eq(1),
            ).Else(
                self.recalled.eq(0),
                read_port.re.eq(0)
            )
        ]

#        self.sync += [
#            If(self.summed_number == 24,[
#                If(self.start_division & ~self.dividing, [
#                   divider.start_i.eq(1), # start the divider module
#                   divider.dividend_i.eq(self.summed_number),
#                   divider.divisor_i.eq(3),
#                   self.dividing.eq(1),
#                ]).Else([
#                    divider.start_i.eq(0),
#                ]),
#                If(self.divider.ready_o & self.dividing & ~self.start_division, [
#                   self.result.eq(divider.quotient_o),
#                   self.leftover.eq(divider.remainder_o),
#                   self.division_finished.eq(1),
#                   self.dividing.eq(0),
#                ])
#            ])
#        ]


        ###

        # FSM
        fsm = FSM(reset_state="RESET")
        self.submodules += fsm

        fsm.act("RESET",
                NextState("INACTIVE")
        )

        fsm.act("INACTIVE",
            NextValue(counter,0),
            NextValue(self.calculated,0),
            NextValue(self.summed_number,0),
            NextValue(self.result,0),
            If((self.store_now_active == 1) & (self.recall_now_active == 0),
               NextState("storing"),
            ).Elif((self.recall_now_active == 1) & (self.store_now_active == 0),
               NextState("recalling"),
            ).Elif((self.calculate_now_active == 1),
                NextState("calculating"),
            ),
        )

        #calculation
        #addition, assuming recall is done in one cycle!
        fsm.act("calculating",
            NextValue(self.recall_now_active,0),
            NextState("summing"),
        )

        fsm.act("summing",
            If(self.recalled == 0,
                NextValue(self.recall_now_active,1),
                NextValue(self.store_now_active,0),
                NextValue(counter,counter+1),
                NextValue(self.where_to_store_or_recall,0),
            ).Elif((counter < self.divide_by),
                If(self.recalled==1,
                   number_recalled_internal.eq(self.number_recalled),
                   NextValue(self.summed_number,self.summed_number + number_recalled_internal),
                   NextValue(self.where_to_store_or_recall,self.where_to_store_or_recall + 1),
                   If(self.where_to_store_or_recall == 4,
                       NextValue(self.recalled,0),
                   ),
                ),
            ).Elif((counter == self.divide_by),
                NextValue(self.calculated,0),
                NextValue(self.start_division,1),
                NextValue(self.dividing,0),
                NextState("division"),
            ),
        )


        fsm.act("division",
            NextValue(divider.start_i,1),
            NextValue(divider.dividend_i,self.summed_number),
            NextValue(divider.divisor_i,self.divide_by),
            NextValue(self.dividing,1),
            NextValue(self.start_division,0),
            NextState("dividing"),
        )

        fsm.act("dividing",
                NextValue(divider.start_i,0),
                If(self.divider.ready_o & ~divider.start_i,
                   NextState("output_is_ready"),
                   NextValue(self.result,divider.quotient_o),
               )
        )
        fsm.act("output_is_ready",
            NextValue(divider.start_i,0),
            NextValue(self.dividing,0),
            NextValue(self.calculated,1),
            NextValue(self.recall_now_active,0),
            NextValue(self.number_to_store,self.result),
            NextState("storing_result"),
        )

        fsm.act("storing_result",
            NextValue(self.recall_now_active,0),
            NextValue(self.store_now_active,1),
            NextValue(self.where_to_store_or_recall,4),
            If(self.where_to_store_or_recall == 4,
                If(self.stored == 1,
                    NextValue(self.store_now_active,0),
                    NextState("INACTIVE"),
                ),
            ),
        )

        #storing
        fsm.act("storing",
            If((self.stored == 1) | (self.store_now_active == 0) & (self.recall_now_active == 0),
                NextState("INACTIVE"),
            ),
        )

        #recalling
        fsm.act("recalling" ,
            If(self.recalled == 1 | (self.store_now_active == 0) & (self.recall_now_active == 0),
                NextState("INACTIVE"),
            ),
        )

def tick():
    yield

# Helper functions for simulation
def wait_for(cycles):
    print(f'Waiting for {cycles} cycles')
    for i in range(cycles):
        yield from tick()

def wait_storage_available(dut):
    print(f'Waiting for storage to be available')
    # Wait until the number storage facility is available
    MAX_WAIT_CYCLES=20
    for i in range(MAX_WAIT_CYCLES):
        if ((yield dut.stored == 0) and (yield dut.store_now_active == 0) and
            (yield dut.recalled == 0) and (yield dut.recall_now_active == 0)):
            break
        yield from tick()
    if i==(MAX_WAIT_CYCLES-1):
        raise Exception("Timeout waiting for storage to become available")

def wait_calculator_available(dut):
    print(f'Waiting for calculator to be available')
    # Wait until the calculator is available
    MAX_WAIT_CYCLES=20
    for i in range(MAX_WAIT_CYCLES):
        if ((yield dut.calculate_now_active == 0) and (yield dut.calculated == 0)):
            break
        yield from tick()
    if i==(MAX_WAIT_CYCLES-1):
        raise Exception("Timeout waiting for calculator to become available")


def calculate(dut):
    yield from wait_calculator_available(dut)
    print(f'Doing calculation')

    yield dut.calculate_now_active.eq(1)
    yield dut.divide_by.eq(3)
    # Wait until calculation is done
    MAX_WAIT_CYCLES=100
    for i in range(MAX_WAIT_CYCLES):
        if (yield dut.calculated == 1):
            break
        yield from tick()
    if i==(MAX_WAIT_CYCLES-1):
        raise Exception("Timeout waiting for calculation to be done")


    yield dut.calculate_now_active.eq(0)
    yield from tick()


def store_number(dut, number_to_store, location):
    yield from wait_storage_available(dut)
    print(f'Storing { number_to_store} in location { location}.')
    # Load a number into storage
    yield dut.where_to_store_or_recall.eq(location)
    yield dut.number_to_store.eq(number_to_store)
    yield from tick()
    yield dut.store_now_active.eq(1)
    yield from tick()

    # Wait until number is loaded
    MAX_WAIT_CYCLES=10
    for i in range(MAX_WAIT_CYCLES):
        if (yield dut.stored == 1):
            break
        yield from tick()
    if i==(MAX_WAIT_CYCLES-1):
        raise Exception("Timeout waiting for number to be stored")

    yield dut.store_now_active.eq(0)
    yield from tick()

def recall_number(dut,location):
    yield from wait_storage_available(dut)
    print(f'Recalling number in location { location}.')
    # Load a number into storage
    yield dut.where_to_store_or_recall.eq(location)
    yield dut.recall_now_active.eq(1)
    yield from tick()

    # Wait until number is loaded
    MAX_WAIT_CYCLES=10
    for i in range(MAX_WAIT_CYCLES):
        if (yield dut.recalled == 1):
            break
    if i>=MAX_WAIT_CYCLES:
        raise Exception("Timeout waiting for number to be recalled")

    number_recalled =     yield dut.number_recalled
    print(f'Recalled number in location { location} is { number_recalled }.')

    yield dut.recall_now_active.eq(0)
    yield from tick()

    return (yield dut.number_recalled)

def simulation_story(dut):
    print('Starting simulation')

    # Lets give a few cycles to allow the board to startup
    yield from wait_for(5)

    # Store numbers
    yield from store_number(dut, 5, location=1)
    yield from store_number(dut, 7, location=2)
    yield from store_number(dut, 9, location=4)

    # Try to get the numbers to make sure they are stored
    if ((yield from recall_number(dut, location=1)) != 5):
        raise Exception("stored number in location 1 does not match")

    if ((yield from recall_number(dut, location=2)) != 7):
        raise Exception("stored number in location 2  does not match")

    if ((yield from recall_number(dut, location=4)) != 9):
        raise Exception("stored number in location 4  does not match")


    # Store 3rd number
    yield from store_number(dut, 12, location=3)

    # Calculate average
    yield from calculate(dut)

    # Get the number from location 4 and see if the average is correct
    r = yield from recall_number(dut,location=4)
    if (r != 8):
        raise Exception(f"average is not calculated correctly. Got {r} but was expecting 8")

    print('First simulation ended successfully')


    # Another test with different numbers
    yield from store_number(dut, 3, location=1)
    yield from store_number(dut, 10, location=2)
    yield from store_number(dut, 20, location=3)

    # Calculate average
    yield from calculate(dut)

    # Get the number from location 4 and see if the average is correct
    r = yield from recall_number(dut,location=4)
    if (r != 11):
        raise Exception(f"average is not calculated correctly. Got {r} but was expecting 11")

    print('Final simulation ended successfully')


    # Another test with different numbers
    yield from store_number(dut, 300, location=1)
    yield from store_number(dut, 403, location=2)
    yield from store_number(dut, 203, location=3)

    # Calculate average
    yield from calculate(dut)

    # Get the number from location 4 and see if the average is correct
    r = yield from recall_number(dut,location=4)
    if (r != 302):
        raise Exception(f"average is not calculated correctly. Got {r} but was expecting 11")

    print('Final simulation ended successfully')

dut = Calculator(16,5)
run_simulation(dut, simulation_story(dut), vcd_name="test_average_mem.vcd")
