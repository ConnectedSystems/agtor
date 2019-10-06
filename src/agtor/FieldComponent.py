from typing import Tuple
from dataclasses import dataclass

from .Component import Component

@dataclass
class Infrastructure(Component):
    """Represents generic farm infrastructure."""
    name: str
    capital_cost_per_ha: float
    # num years maintenance occurs, and 
    # assumed proportion of capital cost
    minor_maintenance_schedule: float
    major_maintenance_schedule: float
    minor_maintenance_rate: float
    major_maintenance_rate: float
    implemented: bool

    def __post_init__(self):
        minor_mr = self.minor_maintenance_rate
        major_mr = self.major_maintenance_rate

        self.maintenance_year = {
            'minor': self.minor_maintenance_schedule,
            'major': self.major_maintenance_schedule
        }

        self.minor_maintenance_cost = self.capital_cost_per_ha * minor_mr
        self.major_maintenance_cost = self.capital_cost_per_ha * major_mr
    # End __post_init__()

    def maintenance_cost(self, year_step: int) -> float:
        """Calculate total maintenance costs.
        """
        mr = self.maintenance_year

        if year_step % mr['major'] == 0:
            maintenance_cost = self.major_maintenance_cost
        elif year_step % mr['minor'] == 0:
            maintenance_cost = self.minor_maintenance_cost
        # End if

        return maintenance_cost
    # End maintenance_cost()

    def cost_per_ha(self):
        raise NotImplementedError("To be implemented elsewhere.")

# End FieldComponent()