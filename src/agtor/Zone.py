from dataclasses import dataclass
from typing import Dict, List

from recordclass import recordclass

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
    '''Represents a farm zone.

    May represent an entire catchment. Otherwise, a collection of zones 
    could be used to represent a catchment.
    '''
    name: str
    climate: object
    fields: List[CropField]

    # Current set up assumes 1 pump per water source, per field
    water_sources: List[WaterSource]

    # Initial allocation for each water source
    allocation: Dict[str, float]

    def __post_init__(self):
        self._allocation = self.allocation
        self.yearly_timestep = 1

        ws_obj = recordclass('water_source', 'source allocation')

        self.water_sources = {
            ws.name: ws_obj(ws, self.allocation[ws.name])
            for ws in self.water_sources
        }

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
        ws = self.water_sources[ws_name]
        ws.allocation -= value

        if np.isclose(ws.allocation, 0.0):
            ws.allocation = 0.0

        if ws.allocation < 0.0:
            msg = "Allocation cannot be below 0 ML! Currently: {}\n".format(ws.allocation)
            msg += f"Tried to use: {value}"
            msg += f"From: {ws_name}"
            raise ValueError(msg) 
    # End use_allocation()

    @property
    def avail_allocation(self):
        """Available water allocation in ML."""
        all_allocs = [ws.allocation for ws in self.water_sources.values()]

        return round(sum(all_allocs), 4)
    # End avail_allocation()

    def possible_area_by_allocation(self, field: CropField) -> Dict:
        """Determine the possible irrigation area using water from each water source.

        Parameter
        ---------
        * field : FarmField object

        Returns
        ---------
        * dict : possible area in hectares by water source
        """
        tmp = {}
        for ws_name, ws_obj in self.water_sources.items():
            tmp[ws_name] = field.calc_possible_area(ws_obj.allocation)
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
    
    def calc_irrigation_water(self, field: CropField) -> float:
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

    def possible_irrigation_area(self, vol_ML: float) -> float:
        """Possible irrigation area in hectares.
        """
        if vol_ML == 0.0:
            return 0.0
        
        area = 0.0
        req_water_mm = 0.0
        for f in self.fields:
            area += f.total_area_ha if f.irrigated_area is None else f.irrigated_area
            req_water_mm += f.calc_required_water()
        # End for

        if (area == 0.0) or (req_water_mm == 0.0):
            return 0.0

        # average required water in mm
        req_water_mm = req_water_mm / len(self.fields)
        
        ML_per_ha = (req_water_mm / ML_to_mm)
        perc_area = (vol_ML / (ML_per_ha * area))
        
        return min(perc_area * area, area)
    # End calc_possible_area()

    @property
    def all_fields_harvested(self):
        """True if all fields are harvested, otherwise False.
        """
        count = 0
        for f in self.fields:
            count = count + 1 if f.harvested else count
        return count == len(self.fields)

    def apply_rainfall(self, dt):
        for f in self.fields:
            # get rainfall and et for datetime
            f_name = f.name
            rain_col = f'{f_name}_rainfall'
            et_col = f'{f_name}_ET'

            idx = self.climate._data.index == dt

            subset = self.climate[idx][[rain_col, et_col]]
            # subset = self.climate.loc[dt, [rain_col, et_col]]
            # rainfall, et = subset[rain_col], subset[et_col]
            rainfall, et = subset[rain_col][0], subset[et_col][0]

            f.update_SWD(rainfall, et)
        # End for
    # End apply_rainfall()

    def run_timestep(self, farmer: Manager, dt: object):
        seasonal_ts = self.yearly_timestep
        self.apply_rainfall(dt)

        opt_cache = {}
        zone = self
        irrigation, cost_per_ML = farmer.optimize_irrigation(zone, dt)
        results = {}
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

            in_season = (dt >= s_start) and (dt <= s_end)
            if not in_season:
                continue

            crop = f.crop
            if (dt > s_start) and (dt < s_end):
                # in season
                if f.irrigated_area == 0.0:
                    # no irrigation occurred!
                    continue

                # Get percentage split between water sources
                opt_field_area = self.opt_field_area

                # irrigation, cost_per_ML = farmer.optimize_irrigation(zone, dt)
                # opt_cache[zone.name] = irrigation, cost_per_ML

                split = farmer.perc_irrigation_sources(f, self.water_sources, irrigation)

                water_to_apply_mm = f.calc_required_water(dt)
                for ws_name in self.water_sources:
                    ws_proportion = split[ws_name]
                    if ws_proportion == 0.0:
                        continue
                    mm_vol_to_apply = ws_proportion * water_to_apply_mm

                    # print("water to apply (mm):", water_to_apply_mm)
                    # print("Water to apply (ML):", (mm_vol_to_apply / ML_to_mm) * f.irrigated_area)
                    # print('mm vol to apply', zone.name, f.name, ws_name, mm_vol_to_apply)
                    # print("split:", split)
                    # print("optimal:", irrigation)
                    # print('avail alloc:', self.avail_allocation)
                    # print('WS Alloc:', self._allocation)

                    self.apply_irrigation(f, ws_name, mm_vol_to_apply)

                    tmp = sum([v for k, v in cost_per_ML.items() if (f.name in k) and (ws_name in k)])
                    f.log_irrigation_cost(tmp * (mm_vol_to_apply / ML_to_mm) * f.irrigated_area)
                # End for
            elif dt == s_start:
                # cropping for this field begins
                # print("Cropping started:", f.name, dt.year, "\n")
                if zone.name in opt_cache:
                    opt_field_area = opt_cache[zone.name]
                else:
                    opt_field_area = farmer.optimize_irrigated_area(self)
                    opt_cache[zone.name] = opt_field_area

                f.irrigated_area = farmer.get_optimum_irrigated_area(f, opt_field_area)
                f.plant_date = s_start
                f.sowed = True
                crop.update_stages(dt)

                self.opt_field_area = opt_field_area
            elif (dt == s_end) and f.sowed:
                # end of season

                income = self.net_income(dt, farmer, f)

                # print(f.name, "harvested! -", dt.year)
                # print("Est. Total Income:", income)
                # print("------------------\n")

                results[f.name] = {
                    'datetime': dt,
                    'income': income,
                    'irrigated_area': f.irrigated_area
                }

                f.set_next_crop()
            # End if
        # End for

        if results:
            return results
    # End run_timestep()

    def net_income(self, dt, farmer, field):
        f = field

        # growing season rainfall
        gsr_mm = self.climate.get_seasonal_rainfall([f.plant_date, f.harvest_date], f.name)
        irrig_mm = f.irrigated_vol_mm

        # The French-Schultz method assumes 30% of previous season's
        # rainfall contributed towards crop growth
        prev = f.plant_date - pd.DateOffset(months=3)
        fs_ssm_assumption = 0.3
        ssm_mm = self.climate.get_seasonal_rainfall([prev, f.plant_date], f.name) * fs_ssm_assumption

        crop_yield_calc = farmer.calc_potential_crop_yield
        income = f.gross_income(crop_yield_calc, 
                                ssm_mm,
                                gsr_mm,
                                irrig_mm)

        costs = f.total_costs(dt, self.water_sources, len(self.fields))
        return income - costs
    # End net_income()

# End FarmZone()
