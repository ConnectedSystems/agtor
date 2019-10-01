from .Pump import Pump
from .Zone import FarmZone, WaterSource
from typing import Dict, List

import itertools

import numpy as np
import pandas as pd

from optlang import Constraint, Model, Objective, Variable

from .consts import *

class Manager(object):

    def __init__(self):
        self.opt_model = Model(name='Farm Decision model')
    # End __init__()
    
    def optimize_irrigation(self, zone: FarmZone, year: int) -> Dict:
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

        Returns
        ---------
        * OrderedDict[str, float] : keys based on field and water source names
                                    values are hectare area
        """
        model = self.opt_model
        lp_vars = []
        lp_calcs = []
        constraints = []

        zone_ws = zone.water_sources
        
        for f in zone.fields:
            did = f"{f.name}__".replace(" ", "_")
            
            if f.irrigation.name == 'dryland':
                lp_vars += [Variable(f"{did}{ws.name}", lb=0, ub=0) 
                            for ws in zone_ws]
                continue
            # End if

            area_to_consider = self.possible_area(zone, f)

            # Will always incur maintenance costs and crop costs
            total_pump_cost = sum([ws.pump.maintenance_cost(year) for ws in zone_ws])
            total_irrig_cost = f.irrigation.maintenance_cost(year)
            maintenance_cost = (total_pump_cost + total_irrig_cost)
            crop_cost_per_ha = f.crop.variable_cost_per_ha

            crop_income_per_ha = (f.crop.yield_per_ha * f.crop.price_per_yield)

            req_water_ML_ha = f.calc_required_water() / ML_to_mm
            flow_rate = f.irrigation.flow_rate_Lps
            i_pressure = f.irrigation.head_pressure

            # Costs to pump needed water volume from each water source
            costs = self.ML_water_application_cost(zone, f, req_water_ML_ha)
            for ws in costs:
                costs[ws] += crop_cost_per_ha
            # End for

            field_area = {
                ws.name: Variable(f"{did}{ws.name}", 
                                  lb=0, 
                                  ub=area_to_consider)
                for ws in zone_ws
            }

            lp_calcs += [
                ((crop_income_per_ha - costs[ws.name]) * field_area[ws.name]) - maintenance_cost
                for ws in zone_ws
            ]

            field_area = list(field_area.values())
            lp_vars += field_area

            # Constrain by available area and water
            f_areas = sum(field_area)
            constraints += [
                Constraint(f_areas,
                           lb=0.0,
                           ub=f.total_area_ha),
                Constraint(f_areas * req_water_ML_ha,
                           lb=0.0,
                           ub=zone.avail_allocation)
            ]
        # End for

        # Total irrigation area cannot be more than total crop area
        # to be considered
        total_area_constraint = [Constraint(sum(lp_vars),
                                           lb=0.0,
                                           ub=zone.total_area_ha)]

        # Generate appropriate OptLang model
        model = Model.clone(self.opt_model)
        model.objective = Objective(sum(lp_calcs), direction='max')
        model.add(constraints + total_area_constraint)
        model.optimize()

        if model.status != 'optimal':
            raise RuntimeError("Could not optimize!")

        return model.primal_values
    # End optimize_irrigation()

    def possible_area(self, zone, field) -> float:
        available_water_ML = zone.avail_allocation
        if not field.irrigated_area:
            area_to_consider = field.total_area_ha
        else:
            # Get possible irrigation area based on available water
            area_to_consider = min(field.calc_possible_area(available_water_ML), 
                                   field.irrigated_area)
        # End if

        return area_to_consider
    # End possible_area()

    def ML_water_application_cost(self, zone: FarmZone, field, req_water_ML_ha) -> Dict:
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
            for ws in zone_ws
        }
        return costs
    # End ML_water_application_cost()

    def calc_ML_pump_costs(self, zone: FarmZone, 
                           flow_rate_Lps: float) -> float:
        ML_costs = {ws.name: ws.calc_pump_cost_per_ML(flow_rate_Lps)
                 for ws in zone.water_sources}

        return ML_costs
    # End calc_ML_pump_costs()
