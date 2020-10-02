import os
from pprint import pprint


pprint(f'I am in {os.path.abspath(__file__)}')
pprint(sample_stage.read())
pprint(sample_stage.x.component_names)
