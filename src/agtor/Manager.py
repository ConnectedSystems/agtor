from typing import Dict, List, Optional

from optlang import Constraint, Model, Objective, Variable

from .Component import Component
from .consts import *


class Manager(object):

    def __init__(self):
        self.opt_model = Model(name='Farm Decision model')
    # End __init__()

    def optimize_irrigated_area(self, zone, year_step: int) -> Dict:
        """Apply Linear Programming to naively optimize irrigated area.
        
        Occurs at start of season.
        """
        calc = []
        areas = []
        constraints = []
        zone_ws = zone.water_sources
        for f in zone.fields:
            area_to_consider = f.total_area_ha
            did = f"{f.name}__".replace(" ", "_")

            naive_crop_income = f.crop.estimate_income_per_ha()
            
            # factor in cost of water
            water_cost = self.ML_water_application_cost(zone, f, 
                                                        f.crop.water_use_ML_per_ha)

            field_areas = {
                ws.name: Variable(f"{did}{ws.name}", 
                                  lb=0,
                                  ub=area_to_consider)
                for ws in zone_ws
            }

            total_pump_cost = sum([ws.pump.maintenance_cost(year_step) for ws in zone_ws])
            profits = [field_areas[ws.name] * 
                       (naive_crop_income - water_cost[ws.name] - total_pump_cost)
                    for ws in zone_ws
            ]

            calc += profits
            areas += list(field_areas.values())

            # Total irrigated area cannot be greater than field area
            constraints += [
                Constraint(sum(field_areas.values()), lb=0.0, ub=area_to_consider)
            ]
        # End for

        constraints += [Constraint(sum(areas),
                                   lb=0.0,
                                   ub=zone.total_area_ha)]

        # Generate appropriate OptLang model
        model = Model.clone(self.opt_model)
        model.objective = Objective(sum(calc), direction='max')
        model.add(constraints)
        model.optimize()

        if model.status != 'optimal':
            raise RuntimeError("Could not optimize!")

        return model.primal_values
    # End optimize_irrigated_area()
    
    def optimize_irrigation(self, zone, dt: object, year_step: int) -> Dict:
        """Apply Linear Programming to optimize irrigation water use.

        Results can be used to represent percentage mix
        e.g. if the field area is 100 ha, and the optimal area to be
             irrigated is
            SW: 70 ha
            GW: 30 ha

        and the required amount is 50mm
            SW: 70 / 100 = 0.7 (70%)
            GW: 30 / 100 = 0.3 (30%)
            
        Therefore, the per hectare amount to be applied from each 
        water source:
            SW = 50 * 0.7
               = 35

            GW = 50 * 0.3
               = 15
        
        Parameters
        ----------
        * zone : FarmZone
        * year_step : int

        Returns
        ---------
        * OrderedDict[str, float] : keys based on field and water source names
                                    values are hectare area
        """
        model = self.opt_model
        areas = []
        profit = []
        constraints = []

        zone_ws = zone.water_sources
        for f in zone.fields:
            did = f"{f.name}__".replace(" ", "_")
            
            if f.irrigation.name == 'dryland':
                areas += [Variable(f"{did}{ws.name}", lb=0, ub=0) 
                            for ws in zone_ws]
                continue
            # End if

            # Will always incur maintenance costs and crop costs
            total_pump_cost = sum([ws.pump.maintenance_cost(dt.year) for ws in zone_ws])
            total_irrig_cost = f.irrigation.maintenance_cost(dt.year)
            maintenance_cost = (total_pump_cost + total_irrig_cost)

            # estimated gross income - variable costs per ha
            crop_income_per_ha = f.crop.estimate_income_per_ha()

            req_water_ML_ha = f.calc_required_water(dt) / ML_to_mm

            # Costs to pump needed water volume from each water source
            costs = self.ML_water_application_cost(zone, f, req_water_ML_ha)

            max_ws_area = zone.possible_area_by_allocation(f)
            field_area = {
                ws.name: Variable(f"{did}{ws.name}", 
                                  lb=0, 
                                  ub=max_ws_area[ws.name])
                for ws in zone_ws
            }

            profit += [
                ((crop_income_per_ha - costs[ws.name]) * field_area[ws.name]) - maintenance_cost
                for ws in zone_ws
            ]

            field_area = list(field_area.values())
            areas += field_area

            # Constrain by available area and water
            f_areas = sum(field_area)
            constraints += [
                Constraint(f_areas,
                           lb=0.0,
                           ub=f.irrigated_area),
                Constraint(f_areas * req_water_ML_ha,
                           lb=0.0,
                           ub=zone.avail_allocation)
            ]
        # End for

        # Total irrigation area cannot be more than total crop area
        # to be considered
        constraints += [Constraint(sum(areas),  # sum of areas >= 0
                                   lb=0.0,
                                   ub=zone.total_area_ha),
                        Constraint(sum(profit),  # profit >= 0
                                   lb=0.0,
                                   ub=None)]

        # Generate appropriate OptLang model
        model = Model.clone(self.opt_model)
        model.objective = Objective(sum(profit), direction='max')
        model.add(constraints)
        model.optimize()

        # if model.status != 'optimal':
        #     print("Areas:")
        #     for v in areas:
        #         print(v, v.primal)
        #     print("Obj. value:", model.objective.value)

        #     print(model.primal_values)
        #     raise RuntimeError("Could not optimize!")

        return model.primal_values
    # End optimize_irrigation()

    def possible_area(self, zone, field: Component, ws_name=Optional[str]) -> float:
        if ws_name:
            available_water_ML = zone.water_sources[ws_name]
        else:
            available_water_ML = zone.avail_allocation
        # End if

        if not field.irrigated_area:
            area_to_consider = field.total_area_ha
        else:
            # Get possible irrigation area based on available water
            area_to_consider = min(field.calc_possible_area(available_water_ML), 
                                   field.irrigated_area)
        # End if

        return area_to_consider
    # End possible_area()

    def get_optimum_irrigated_area(self, field: Component, primals: Dict) -> float:
        """Extract total irrigated area from OptLang optimized results."""
        return sum([v for k, v in primals.items() if field.name in k])
    # End get_optimum_irrigated_area()

    def perc_irrigation_sources(self, field: Component, water_sources: List, primals: Dict) -> Dict:
        """Calculate percentage of area to be watered by a specific water source.

        Returns
        -------
        * Dict[str, float] : name of water source as key and perc. area as value
        """
        area = field.irrigated_area
        opt = {}

        for k in primals:
            for ws in water_sources:
                if (field.name in k) and (ws.name in k):
                    opt[ws.name] = primals[k] / area
        # End for

        return opt
    # End perc_irrigation_sources()

    def ML_water_application_cost(self, zone, field: Component, req_water_ML_ha: float) -> Dict:
        """Calculate water application cost/ML by each water source.

        Returns
        ---------
        * dict[str, float] : water source name and cost per ML
        """
        zone_ws = zone.water_sources
        irrigation = field.irrigation
        i_pressure = irrigation.head_pressure
        flow_rate = irrigation.flow_rate_Lps

        costs = {
            ws.name: (ws.pump.pumping_costs_per_ML(flow_rate, 
                                                    ws.head + i_pressure) 
                                                    * req_water_ML_ha) 
                                                    + (ws.cost_per_ML*req_water_ML_ha)
            for ws in zone_ws
        }
        return costs
    # End ML_water_application_cost()

    def calc_ML_pump_costs(self, zone, 
                           flow_rate_Lps: float) -> dict:
        """Calculate pumping costs (per ML) for each water source.

        Parameters
        ----------
        * zone : FarmZone
        * flow_rate_Lps : float, desired flow rate in Litres per second. 
        """
        ML_costs = {ws.name: ws.calc_pump_cost_per_ML(flow_rate_Lps)
                    for ws in zone.water_sources}

        return ML_costs
    # End calc_ML_pump_costs()

    def calc_potential_crop_yield(self, ssm_mm, gsr_mm, crop):
        """Uses French-Schultz equation, taken from [Oliver et al. 2008 (Equation 1)](<http://www.regional.org.au/au/asa/2008/concurrent/assessing-yield-potential/5827_oliverym.htm>)

        The method here uses the farmer friendly modified version as given in the above.

        Represents Readily Available Water - (Crop evapotranspiration * Crop Water Use Efficiency Coefficient)

        .. math::
            YP = (SSM + GSR - E) * WUE

        where

        * :math:`YP` is yield potential in kg/Ha
        * :math:`SSM` is Stored Soil Moisture (at start of season) in mm, assumed to be 30% of summer rainfall
        * :math:`GSR` is Growing Season Rainfall in mm
        * :math:`E` is Crop Evaporation coefficient in mm, the amount of rainfall required before the crop will start
          to grow, commonly 110mm, but can range from 30-170mm [Whitbread and Hancock 2008](http://www.regional.org.au/au/asa/2008/concurrent/assessing-yield-potential/5803_whitbreadhancock.htm),
        * :math:`WUE` is Water Use Efficiency coefficient in kg/mm

        Parameters
        ----------
        * ssm_mm : float, Stored Soil Moisture (mm) at start of season.
        * gsr_mm : float, Growing Season Rainfall (mm)
        * evap_coef_mm : float, Crop evapotranspiration coefficient (mm)
        * wue_coef_mm : float, Water Use Efficiency coefficient (kg/mm)
        * max_thres : float, maximum rainfall threshold in mm, water above this amount does not contribute to
                      crop yield

        Returns
        -----------
        * Potential yield in tonnes/Ha
        """
        evap_coef_mm = crop.et_coef
        wue_coef_mm = crop.wue_coef
        max_thres = crop.rainfall_threshold

        gsr_mm = min(gsr_mm, max_thres)
        return max(0.0, ((ssm_mm + gsr_mm - evap_coef_mm) * wue_coef_mm) / 1000.0)
    # End calc_potential_crop_yield()

    # def calc_effective_rainfall(self, rainfall: float, timestep: object):
    #     """Calculate effective rainfall based on current soil water deficit.

    #     Currently implemented as a simple linear relationship.

    #     :param rainfall: double, rainfall amount in mm

    #     :returns: double, effective rainfall
    #     """
    #     if timestep.month in [6, 7, 8]:
    #         return rainfall
    #     else:
    #         return rainfall * (-self.c_swd / self.Soil.TAW_mm)
