from typing import Optional
from dataclasses import dataclass

from agtor.data_interface import generate_params
from .Component import Component
from .Pump import Pump


@dataclass
class WaterSource(Component):
    """Source of water for a zone."""

    name: str

    # Fees in dollars
    cost_per_ML: float
    cost_per_ha: float
    yearly_costs: float

    # Infrastructure to access resource
    pump: Optional[Pump] = None
    head: Optional[float] = None

    def pump_cost_per_ML(self, flow_rate_Lps):
        return self.pump.pumping_costs_per_ML(flow_rate_Lps, self.head)
    # End pump_cost_per_ML()

    def usage_costs(self, water_used_ML):
        return self.cost_per_ML * water_used_ML

    def total_costs(self, area, water_used_ML):
        usage_fee = self.usage_costs(water_used_ML)
        area_fee = self.cost_per_ha * area
        return self.yearly_costs + usage_fee + area_fee
    # End total_costs()

# End WaterSource()