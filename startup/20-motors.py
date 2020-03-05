from ophyd import (EpicsSignal, EpicsMotor, Device, Component as Cpt)


class SampleStage(Device):
    x = Cpt(EpicsMotor, '1')
    y = Cpt(EpicsMotor, '2')
    z = Cpt(EpicsMotor, '3')


sample_stage = SampleStage('IOC:m', name='sample_stage')
