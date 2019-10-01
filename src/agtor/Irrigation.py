from dataclasses import dataclass
from .FieldComponent import Infrastructure

@dataclass
class Irrigation(Infrastructure):
    efficiency: float = 0.5
    flow_ML_day: float = 12.0
    head_pressure: float = 10.0

    def cost_per_ha(self, year: int, area: float) -> float:
        return self.maintenance_cost(year) / area
    # End cost_per_ha()

    @property
    def flow_rate_Lps(self) -> float:
        """Calculate flow rate in litres per second.
        """
        ML = 1e6  # Litres in a megaliter
        SEC_IN_DAY = 86400.0

        return (self.flow_ML_day * ML) / SEC_IN_DAY
    # End flow_rate_Lps()

# End Irrigation()