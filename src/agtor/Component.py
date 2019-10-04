from dataclasses import dataclass
from ema_workbench import (CategoricalParameter, Constant, RealParameter)

@dataclass
class Component:

    def __getattribute__(self, attr):
        v = object.__getattribute__(self, attr)
        if isinstance(v, (CategoricalParameter, Constant, RealParameter)):
            try:
                val = v.value
            except AttributeError:
                val = v.default
            # End try

            return val

        return v
    # End __getattribute__()

    def get_nominal(self, item):
        if isinstance(item, (CategoricalParameter, Constant, RealParameter)):
            try:
                val = item.value
            except AttributeError:
                val = item.default
            # End try

            return val

        return item
    # End get_nominal()

# End Component()
