from dataclasses import dataclass

from agtor.data_interface import load_yaml, generate_params, sort_param_types
from .FieldComponent import Infrastructure

@dataclass
class Irrigation(Infrastructure):
    efficiency: float
    flow_ML_day: float
    head_pressure: float

    def cost_per_ha(self, year_step: int, area: float) -> float:
        return self.maintenance_cost(year_step) * area
    # End cost_per_ha()

    def total_costs(self, year_step: int):
        """Calculate total costs.
        """
        # cost per ha divides maintenance costs by the
        # area considered, so simply use 1 to get total.
        return self.cost_per_ha(year_step, 1)
    # End total_costs()

    @property
    def flow_rate_Lps(self) -> float:
        """Calculate flow rate in litres per second.
        """
        ML = 1e6  # Litres in a megaliter
        SEC_IN_DAY = 86400.0

        return (self.flow_ML_day * ML) / SEC_IN_DAY
    # End flow_rate_Lps()

# End Irrigation()