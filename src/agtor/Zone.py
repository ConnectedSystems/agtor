from __future__ import division
from dataclasses import dataclass
from typing import Dict, List

from agtor import Component
from .consts import ML_to_mm

from .Pump import Pump
from .Field import CropField


from .Manager import Manager

import numpy as np
import pandas as pd

@dataclass
class WaterSource(Component):
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
        self.yearly_timestep = 1

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

    def set_avail_allocation(self, ws_name, value):
        if 'groundwater' in ws_name.lower():
            self.gw_allocation -= value
            return

        lr_tmp = (self.lr_allocation - value)

        if lr_tmp > 0.0:
            self.lr_allocation = lr_tmp
            return

        left_over = abs(lr_tmp)
        self.lr_allocation = 0.0
        self.hr_allocation -= left_over

        if self.hr_allocation < 0.0:
            raise ValueError("HR Allocation cannot be below 0 ML! Currently: {}".format(self.hr_allocation))
    # End set_avail_allocation()

    @property
    def avail_allocation(self):
        """Available water allocation in ML."""
        return round(sum(self._allocation.values()), 4)
    # End avail_allocation()

    @property
    def hr_allocation(self):
        """Available High Reliability water allocation in ML."""
        return self._allocation['HR']
    # End hr_allocation()

    @hr_allocation.setter
    def hr_allocation(self, value):
        """Value to be given in ML."""
        if np.isclose(value, 0.0):
            value = 0.0
        self._allocation['HR'] = value
    # End hr_allocation.setter()

    @property
    def lr_allocation(self):
        """Available Low Reliabiltiy water allocation in ML."""
        return self._allocation['LR']
    # End lr_allocation()

    @lr_allocation.setter
    def lr_allocation(self, value):
        """Value to be given in ML."""
        if np.isclose(value, 0.0):
            value = 0.0
        self._allocation['LR'] = value
    # End lr_allocation.setter()

    @property
    def gw_allocation(self):
        """Available Low Reliabiltiy water allocation in ML."""
        return self._allocation['GW']
    # End gw_allocation()

    @gw_allocation.setter
    def gw_allocation(self, value):
        """Value to be given in ML."""
        if np.isclose(value, 0.0):
            value = 0.0
        self._allocation['GW'] = value
    # End gw_allocation.setter()

    def possible_area_by_allocation(self, field: CropField):
        """Determine the possible irrigation area using water from each water source.
        """
        sw = self.lr_allocation + self.hr_allocation
        gw = self.gw_allocation

        tmp = {}
        for ws in self.water_sources:
            ws_name = ws.name
            if 'groundwater' in ws_name.lower():
                tmp[ws_name] = field.calc_possible_area(gw)
            else:
                tmp[ws_name] = field.calc_possible_area(sw)
        # End for

        return tmp
    # End possible_area_by_allocation()

    @property
    def irrigated_area(self):
        """The total area marked for irrigation.
        """
        fields = self.fields
        return sum([f.irrigated_area for f in fields])
    # End irrigated_area()
    
    def calc_irrigation_water(self, field: CropField):
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

    def apply_irrigation(self, field: CropField, ws_name: str, water_to_apply_mm: float):
        
        vol_ML_ha = (water_to_apply_mm / ML_to_mm)
        field.irrigated_volume += vol_ML_ha

        vol_ML = vol_ML_ha * field.irrigated_area
        self.set_avail_allocation(ws_name, vol_ML)
        field.soil_SWD -= max(0.0, (water_to_apply_mm * field.irrigation.efficiency))
    # End apply_irrigation()

    def calc_cost_of_irrigation(self, req_water_mm, pump):
        """TODO: Pumping costs..."""
        raise NotImplementedError("Not completed")
        return 0.0
    # End calc_cost_of_irrigation()

    @property
    def all_fields_harvested(self):
        all_fields = self.fields

        count = 0
        for f in all_fields:
            count = count + 1 if f.harvested else count
        
        if count == len(all_fields):
            return True
        
        return False
    # End all_fields_harvested()

    def apply_rainfall(self, dt):
        for f in self.fields:
            # get rainfall and et for datetime
            f_name = f.name
            rain_col = f'{f_name}_rainfall'
            et_col = f'{f_name}_ET'
            subset = self.climate.loc[dt, [rain_col, et_col]]
            rainfall, et = subset[rain_col], subset[et_col]

            f.update_SWD(rainfall, et)
        # End for
    # End apply_rainfall()

    def run_timestep(self, farmer: Manager, dt):
        seasonal_ts = self.yearly_timestep
        self.apply_rainfall(dt)
        
        for f in self.fields:
            s_start = f.plant_date
            s_end = None
            try:
                s_end = f.harvest_date
            except AttributeError:
                is_sow_day = (dt.month == s_start.month) and (dt.day == s_start.day)
                if is_sow_day:
                    s_start = s_start.replace(year=dt.year)
                    f.harvest_date = s_start + f.crop.harvest_offset
                    s_end = f.harvest_date
                # End if
            # End try

            if not s_end:
                continue

            crop = f.crop
            if (dt > s_start) and (dt < s_end):
                # in season
                # Get percentage split between water sources
                opt_field_area = self.opt_field_area
                irrigation = farmer.optimize_irrigation(self, dt, seasonal_ts)
                split = farmer.perc_irrigation_sources(f, self.water_sources, irrigation)

                water_to_apply_mm = f.calc_required_water(dt)
                for ws in self.water_sources:
                    ws_proportion = split[ws.name]
                    if ws_proportion == 0.0:
                        continue
                    self.apply_irrigation(f, ws.name, ws_proportion * water_to_apply_mm)                    
                # End for
            elif dt == s_start:
                # cropping for this field begins
                opt_field_area = farmer.optimize_irrigated_area(self, seasonal_ts)
                f.irrigated_area = farmer.get_optimum_irrigated_area(f, opt_field_area)
                f.plant_date = s_start
                f.sowed = True
                crop.update_stages(dt)

                self.opt_field_area = opt_field_area
            elif dt == s_end and f.sowed:
                # end of season

                # growing season rainfall
                gsr_mm = self.climate.get_seasonal_rainfall([f.plant_date, f.harvest_date], f.name)
                gsr_mm += (f.irrigated_volume * ML_to_mm)
                print("GSR:", gsr_mm)

                # The French-Schultz method assumes 30% of previous season's
                # rainfall contributed towards crop growth
                prev = f.plant_date - pd.DateOffset(months=3)
                fs_ssm_assumption = 0.3
                ssm_mm = self.climate.get_seasonal_rainfall([prev, f.plant_date], f.name) * fs_ssm_assumption

                crop_yield = farmer.calc_potential_crop_yield(ssm_mm, gsr_mm, crop)

                print("Estimated crop yield (t/ha):", crop_yield)
                print("Total yield (t):", crop_yield * f.irrigated_area)

                f.set_next_crop()
                
                print(f.name, "Harvested!")
            # End if

        # End for

        if dt.month == 12 and dt.day == 31:
            self.yearly_timestep += 1
        # End if

    # End run_timestep()

# End FarmZone()
