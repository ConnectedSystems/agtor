from __future__ import division
from dataclasses import dataclass
from typing import Dict, List

from .Pump import Pump
from .Field import CropField
from .consts import ML_to_mm

@dataclass
class WaterSource:
    name: str
    head: float

    # Fees in dollars
    cost_per_ML: float
    yearly_costs: float
    pump: Pump

    def calc_pump_cost_per_ML(self, flow_rate_Lps):
        return self.pump.pumping_costs_per_ML(flow_rate_Lps, self.head)
    # End calc_pump_cost_per_ML()

# End WaterSource()

@dataclass
class FarmZone:
    '''Class representing a farm zone.'''
    name: str
    climate: object
    fields: List[CropField]

    # Current set up assumes 1 pump per water source, per field
    water_sources: List[WaterSource]
    allocation: Dict[str, float]

    def __post_init__(self):
        self._allocation = self.allocation

        assert 'HR' in self._allocation.keys(),\
            "High reliability allocation not specified"

        assert 'LR' in self._allocation.keys(),\
            "Low reliability allocation not specified"

        assert 'GW' in self._allocation.keys(),\
            "Groundwater allocation not specified"

        assert len(set([f.name for f in self.fields])) == len(self.fields),\
            "Names of fields have to be unique"
    # End __post_init__()

    @property
    def total_area_ha(self):
        return sum([f.total_area_ha for f in self.fields])
    # End total_area_ha()

    @property
    def avail_allocation(self):
        return sum(self._allocation.values())

    @property
    def hr_allocation(self):
        """Available water allocation in mm."""
        return self._allocation['HR']
    # End hr_allocation()

    @hr_allocation.setter
    def hr_allocation(self, value):
        """Value to be given in ML."""
        self._allocation['HR'] = value
    # End hr_allocation.setter()

    @property
    def lr_allocation(self):
        """Available water allocation in mm."""
        return self._allocation['LR']
    # End lr_allocation()

    @lr_allocation.setter
    def lr_allocation(self, value):
        """Value to be given in ML."""
        self._allocation['LR'] = value
    # End lr_allocation.setter()

    def calc_total_costs(self, year: int) -> float:
        fields = self.fields
        zonal_costs = 0.0
        for field in fields.values():
            # tally all costs incurred for a season
            zonal_costs += field.calc_field_cost(year)

        return zonal_costs
    # End calc_total_costs()

    @property
    def irrigated_area(self):
        fields = self.fields
        return sum([f.irrigated_area for f in fields.values()])
    # End irrigated_area()
    
    def calc_irrigation_water(self, field):
        """Calculate ML per ha to apply.
        """
        req_water_ML = field.calc_required_water() / ML_to_mm

        # Can only apply water that is available
        ML_per_ha = self.avail_allocation / field.irrigated_area
        if req_water_ML <= ML_per_ha:
            irrig_water = req_water_ML
        else:
            irrig_water = ML_per_ha
        # End if

        return irrig_water
    # End calc_irrigation_water()

    def apply_irrigation(self, field, water_to_apply_mm):
        self.avail_allocation -= water_to_apply_mm
        field.soil_SWD -= water_to_apply_mm
    # End apply_irrigation()

    def calc_cost_of_irrigation(self, req_water_mm, pump):
        """TODO: Pumping costs..."""
        return 0.0
    # End calc_cost_of_irrigation()

    @property
    def all_fields_harvested(self):
        all_fields = list(self.fields.values())

        count = 0
        for f in all_fields:
            count = count + 1 if f.harvested else count
        
        if count == len(all_fields):
            return True
        
        return False
    # End all_fields_harvested()

    def run_timestep(self):
        for f in self.fields.values():
            water_to_apply = self.calc_irrigation_water(f)
            irrig_cost = self.calc_cost_of_irrigation(water_to_apply)

            self.apply_irrigation(f, water_to_apply)
        # End for
    # End run_timestep()

# End FarmZone()
