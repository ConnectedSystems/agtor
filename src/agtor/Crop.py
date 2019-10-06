from typing import Optional
from dataclasses import dataclass
from .Component import Component

import pandas as pd

@dataclass
class Crop(Component):
    name: str
    crop_type: str
    plant_date: object

    # Growth pattern
    growth_stages: Optional[dict] = None
    growth_coefficients: Optional[dict] = None

    # Crop properties
    yield_per_ha: Optional[float] = None
    price_per_yield: Optional[float] = None
    variable_cost_per_ha: Optional[float] = None
    water_use_ML_per_ha: Optional[float] = None
    root_depth_m: Optional[float] = None
    et_coef: Optional[float] = None
    wue_coef: Optional[float] = None
    rainfall_threshold: Optional[float] = None
    ssm_coef: Optional[float] = None
    effective_root_zone: Optional[float] = None

    def __post_init__(self):
        sow_date = self.plant_date
        self.plant_date = pd.to_datetime('1900-'+sow_date)

        h_day = sum(self.get_nominal(v['stage_length']) 
                    for k, v in self.growth_stages.items())
        
        offset = 0
        start_date = self.plant_date
        self._stages = {}
        for k, v in self.growth_stages.items():

            offset = self.get_nominal(v['stage_length'])
            end_of_stage = start_date + pd.DateOffset(days=offset)
            self._stages[k] = {
                'start': start_date,
                'end': end_of_stage
            }

            start_date = start_date + pd.DateOffset(days=offset+1)
        # End for

        self.harvest_offset = pd.DateOffset(days=h_day)
    # End __post_init__()

    def update_stages(self, dt):
        stages = self._stages
        start_date = self.plant_date.replace(year=dt.year)
        for k, v in self.growth_stages.items():
    
            offset = self.get_nominal(v['stage_length'])
            end_of_stage = start_date + pd.DateOffset(days=offset)

            stages[k] = {
                'start': start_date,
                'end': end_of_stage
            }

            start_date = start_date + pd.DateOffset(days=offset+1)
        # End for
    # End update_stages()

    def get_stage_coefs(self, dt):
        if dt is None:
            return self.growth_stages['initial']

        for k, v in self._stages.items():
            s, e = v['start'], v['end']
            in_season = False
            same_month = s.month == dt.month
            if same_month:
                in_day = s.day >= dt.day
                in_season = same_month and in_day
            elif (s.month <= dt.month):
                if (dt.month <= e.month):
                    in_season = dt.day <= e.day
                # End if
            # End if

            if in_season:
                return self.growth_stages[k]
        # End for

        # Not in season so just return initial growth stage
        return self.growth_stages['initial']
    # End get_stage_coefs()

    def estimate_income_per_ha(self):
        """Naive estimation of net income."""
        income = (self.price_per_yield * self.yield_per_ha) \
                 - self.variable_cost_per_ha
        return income
    # End estimate_income_per_ha()

    def total_costs(self, area):
        return self.variable_cost_per_ha * area
    # End total_costs()

# End Crop()
