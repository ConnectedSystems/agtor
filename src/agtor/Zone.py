from dataclasses import dataclass
from typing import Dict, List

from agtor import Component
from .consts import ML_to_mm

from .Pump import Pump
from .Field import CropField


from .Manager import Manager
from .WaterSource import WaterSource

import numpy as np
import pandas as pd


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

    def use_allocation(self, ws_name, value):
        """Use allocation volume from a particular water source.

        If surface water, uses Low Reliability first, then
        High Reliability allocations.
        """
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
    # End use_allocation()

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
        vol_ML = vol_ML_ha * field.irrigated_area
        self.use_allocation(ws_name, vol_ML)
        field.soil_SWD -= max(0.0, (water_to_apply_mm * field.irrigation.efficiency))

        field.irrigated_volume = (ws_name, vol_ML)
    # End apply_irrigation()

    def calc_cost_of_irrigation(self, req_water_mm, pump):
        """TODO: Pumping costs..."""
        raise NotImplementedError("Not completed")
        return 0.0
    # End calc_cost_of_irrigation()

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
        
        zone = self
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
                if f.irrigated_area == 0.0:
                    # no irrigation occurred!
                    continue

                # Get percentage split between water sources
                opt_field_area = self.opt_field_area
                irrigation, cost_per_ML = farmer.optimize_irrigation(zone, dt)

                split = farmer.perc_irrigation_sources(f, self.water_sources, irrigation)

                water_to_apply_mm = f.calc_required_water(dt)
                for ws in self.water_sources:
                    ws_name = ws.name
                    ws_proportion = split[ws_name]
                    if ws_proportion == 0.0:
                        continue
                    vol_to_apply = ws_proportion * water_to_apply_mm
                    self.apply_irrigation(f, ws_name, vol_to_apply)

                    tmp = sum([v for k, v in cost_per_ML.items() if (f.name in k) and (ws_name in k)])
                    f.log_irrigation_cost(tmp * (vol_to_apply / ML_to_mm) * f.irrigated_area)
                # End for
            elif dt == s_start:
                # cropping for this field begins
                print("Cropping started:", f.name, dt.year, "\n")
                opt_field_area = farmer.optimize_irrigated_area(self)
                f.irrigated_area = farmer.get_optimum_irrigated_area(f, opt_field_area)
                f.plant_date = s_start
                f.sowed = True
                crop.update_stages(dt)

                self.opt_field_area = opt_field_area
            elif dt == s_end and f.sowed:
                # end of season
                print(f.name, "harvested! -", dt.year)

                # growing season rainfall
                gsr_mm = self.climate.get_seasonal_rainfall([f.plant_date, f.harvest_date], f.name)
                irrig_mm = f.irrigated_vol_mm

                # The French-Schultz method assumes 30% of previous season's
                # rainfall contributed towards crop growth
                prev = f.plant_date - pd.DateOffset(months=3)
                fs_ssm_assumption = 0.3
                ssm_mm = self.climate.get_seasonal_rainfall([prev, f.plant_date], f.name) * fs_ssm_assumption

                crop_yield_calc = farmer.calc_potential_crop_yield
                nat = ssm_mm+gsr_mm
                income = f.total_income(crop_yield_calc, 
                               ssm_mm,
                               gsr_mm,
                               irrig_mm,
                               (dt, self.water_sources))

                # crop_yield = farmer.calc_potential_crop_yield(ssm_mm, gsr_mm+irrig_mm, crop)
                # Unfinished - not account for cost of pumping water
                print("Est. Total Income:", income)
                print("------------------\n")

                f.set_next_crop()
            # End if
        # End for

    # End run_timestep()

# End FarmZone()
