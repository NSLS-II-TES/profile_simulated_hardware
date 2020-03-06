from ophyd import (EpicsSignal, EpicsMotor, Device, Component as Cpt)


class EpicsMotorWithLimits(EpicsMotor):
    hlm = Cpt(EpicsSignal, '.HLM', kind='config')
    llm = Cpt(EpicsSignal, '.LLM', kind='config')


class SampleStage(Device):
    # Motor 1 has a higher minimum velocity (2), and a lower upper bound (180),
    # that's why we'll be using motors 2-4 to have a more configurable env.
    x = Cpt(EpicsMotorWithLimits, '2')
    y = Cpt(EpicsMotorWithLimits, '3')
    z = Cpt(EpicsMotorWithLimits, '4')


sample_stage = SampleStage('IOC:m', name='sample_stage')

for cpt in sample_stage.component_names:
    getattr(sample_stage, cpt).llm.put(-1000)
    getattr(sample_stage, cpt).hlm.put(1000)
    getattr(sample_stage, cpt).velocity.put(5.0)
