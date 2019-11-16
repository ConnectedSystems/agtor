from typing import Optional, Dict
from dataclasses import dataclass

from agtor.data_interface import load_yaml, generate_params, sort_param_types
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

        if self.growth_stages:
            h_day = sum(self.get_nominal(v['stage_length'])
                        for k, v in self.growth_stages.items())
        
        offset = 0
        start_date = self.plant_date
        self._stages = {}
        if self.growth_stages:
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

        if self.growth_stages:
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

    def total_costs(self, year):
        # cost of production is handled by factoring in
        # water application costs and other maintenance costs.
        # The variable_cost_per_ha is only used to inform estimates.
        return 0.0
    # End total_costs()

    @classmethod
    def collate_data(cls, data: Dict):
        """Produce flat lists of crop-specific parameters.

        Parameters
        ----------
        * data : Dict, of crop data

        Returns
        -------
        * tuple[List] : (uncertainties, categoricals, and constants)
        """
        unc, cats, consts = sort_param_types(data['properties'], unc=[], cats=[], consts=[])

        growth_stages = data['growth_stages']
        unc, cats, consts = sort_param_types(growth_stages, unc, cats, consts)

        return unc, cats, consts
    # End collate_data()

    @classmethod
    def create(cls, data, override=None):
        tmp = data.copy()
        name = tmp.pop('name')
        prop = tmp.pop('properties')
        crop_type = tmp.pop('crop_type')
        growth_stages = tmp.pop('growth_stages')

        prefix = f"Crop___{name}__{{}}"
        props = generate_params(prefix.format('properties'), prop, override)
        stages = generate_params(prefix.format('growth_stages'), growth_stages, override)

        return cls(name, crop_type, growth_stages=stages, **props)
    # End create()

# End Crop()
