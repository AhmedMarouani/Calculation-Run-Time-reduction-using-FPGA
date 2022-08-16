#!/usr/bin/env python3
from migen import *

class Mem(Module):
    def __init__(self, width, depth):
        storage = Memory(width, depth)
        self.specials += storage

        self.stored = Signal()
        self.recalled = Signal()
        self.where_to_store_or_recall = Signal(8)
        self.number_to_store = Signal(16)
        self.number_recalled = Signal(16)
        self.store_now_active = Signal()
        self.recall_now_active = Signal()

        ###

        #internal signals
        write_port = storage.get_port(write_capable = True)
        read_port = storage.get_port(has_re=True)

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


def tick():
    global t
    t=t+1
    yield

def simulation_story(dut):

    global t
    t = 0
    # if it needs it, here is some empty startup time
    for i in range(5):
        yield from tick()




    # see if storage can handle more than 50 locations
    for i in range (50):
        yield dut.where_to_store_or_recall.eq(i+20)
        yield dut.number_to_store.eq(i)
        yield dut.store_now_active.eq(1)
        yield from tick()
    # wait until stored
        for i in range(50):
            if ((yield dut.stored) == 1):
                break
            yield from tick()
        if i>=49:
            raise Exception("Error, did not get stored signal")

        yield dut.store_now_active.eq(0)
        print("stored number is ",(yield dut.where_to_store_or_recall))
        yield from tick()





    # store a number
    yield dut.where_to_store_or_recall.eq(90)
    yield dut.number_to_store.eq(0x5665)
    yield dut.store_now_active.eq(1)
    yield from tick()

    # wait until storage is done
    for i in range(50):
        if ((yield dut.stored) == 1):
            break
        yield from tick()
    if i>=49:
        raise Exception("Error, did not get stored signal")

    yield dut.store_now_active.eq(0)
    yield from tick()

    # Let's wait until, the storage allows for another storage
    # That is until dut.stored is back to zero



    # store another number in storage 2
    yield dut.where_to_store_or_recall.eq(91)
    yield dut.number_to_store.eq(0x8888)
    yield dut.store_now_active.eq(1)
    yield from tick()

    # wait until storage is done
    for i in range(50):
        if ((yield dut.stored) == 1):
            break
        yield from tick()
    if i>=49:
        raise Exception("Error, did not get stored signal")

    yield dut.store_now_active.eq(0)
    yield from tick()

    # lets get our first number
    yield dut.where_to_store_or_recall.eq(90)
    yield dut.recall_now_active.eq(1)
    yield from tick()

    # Let's wait until, the storage recalls the number
    # That is until dut.recalled is 1

    for i in range(50):
        if ((yield dut.recalled) == 1):
            break
        yield from tick()
    if i>=49:
        raise Exception("Error, did not see recalled signal back to 0")

    # Lets make sure the number is the same
    print("Received number is ",(yield dut.number_recalled))
    assert( 0x5665 == (yield dut.number_recalled))

    yield dut.recall_now_active.eq(0)
    yield from tick()

    # lets get our second number
    yield dut.where_to_store_or_recall.eq(91)
    yield dut.recall_now_active.eq(1)
    yield from tick()
    # ...

    # wait until recalled
    for i in range(50):
        if ((yield dut.recalled) == 1):
            break
        yield from tick()
    if i>=49:
        raise Exception("Error, did not see recalledsignal back to 0")

    # assert number is 0x222
    print("Received number is ",(yield dut.number_recalled))
    assert( 0x8888 == (yield dut.number_recalled))

    yield dut.recall_now_active.eq(0)
    yield from tick()
    # store another number in location 1
    #
    yield dut.where_to_store_or_recall.eq(90)
    yield dut.number_to_store.eq(0x7474)
    yield dut.store_now_active.eq(1)
    yield from tick()



    # wait until stored
    for i in range(50):
        if ((yield dut.stored) == 1):
            break
        yield from tick()
    if i>=49:
        raise Exception("Error, did not get stored signal")

    yield dut.store_now_active.eq(0)
    yield from tick()

    # lets get our second number again, to make sure it is still there
    yield dut.where_to_store_or_recall.eq(91)
    yield dut.recall_now_active.eq(1)
    yield from tick()
    # ...

    # wait until recalled
    for i in range(50):
        if ((yield dut.recalled) == 1):
            break
        yield from tick()
    if i>=49:
        raise Exception("Error, did not see recalledsignal back to 0")

    # assert number is 0x222
    print("Received number is ",(yield dut.number_recalled))
    assert( 0x8888 == (yield dut.number_recalled))

    yield dut.recall_now_active.eq(0)
    yield from tick()


    # get number in location 1
    yield dut.where_to_store_or_recall.eq(90)
    yield dut.recall_now_active.eq(1)
    yield from tick()

    # wait until recalled
    for i in range(50):
        if ((yield dut.recalled) == 1):
            break
        yield from tick()
    if i>=49:
        raise Exception("Error, did not see recalledsignal back to 0")

    # make sure it is now 0x3333
    print("Received number is ",(yield dut.number_recalled))
    assert( 0x7474 == (yield dut.number_recalled))

    yield dut.recall_now_active.eq(0)
    yield from tick()

    print("Simulation finished")
    yield from [None] * 4095

if __name__ == "__main__":
    dut = Mem(16, 16)
    run_simulation(dut, simulation_story(dut), vcd_name="test_memoryy.vcd")
