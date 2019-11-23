from typing import Dict, List, Optional
from collections import OrderedDict

from optlang import Constraint, Model, Objective, Variable

from .Component import Component
from .consts import *


class Manager(object):

    """An 'economically rational' crop farm manager. 
    
    Follows a set crop rotation.
    """

    def __init__(self):
        self.opt_model = Model(name='Farm Decision model')
    # End __init__()

    def optimize_irrigated_area(self, zone) -> Dict:
        """Apply Linear Programming to naively optimize irrigated area.
        
        Occurs at start of season.

        Parameters
        ----------
        * zone : FarmZone object, representing a farm or a farming zone.
        """
        calc = []
        areas = []
        constraints = []
        zone_ws = zone.water_sources
        
        total_avail_water = zone.avail_allocation

        field_areas = {}
        for f in zone.fields:
            area_to_consider = f.total_area_ha
            did = f"{f.name}__".replace(" ", "_")

            naive_crop_income = f.crop.estimate_income_per_ha()
            naive_req_water = f.crop.water_use_ML_per_ha
            app_cost_per_ML = self.ML_water_application_cost(zone, f, naive_req_water)

            pos_field_area = [w.allocation / naive_req_water
                                for ws_name, w in zone_ws.items()
            ]
            pos_field_area = min(sum(pos_field_area), area_to_consider)
            
            field_areas[f.name] = {
                ws_name: Variable(f"{did}{ws_name}", 
                                  lb=0,
                                  ub=min(w.allocation / naive_req_water, area_to_consider))
                for ws_name, w in zone_ws.items()
            }

            # total_pump_cost = sum([ws.pump.maintenance_cost(year_step) for ws in zone_ws])
            profits = [field_areas[f.name][ws_name] * 
                       (naive_crop_income - app_cost_per_ML[ws_name])
                       for ws_name in zone_ws
            ]

            calc += profits
            curr_field_areas = list(field_areas[f.name].values())
            areas += curr_field_areas

            # Total irrigated area cannot be greater than field area
            # or area possible with available water
            constraints += [
                Constraint(sum(curr_field_areas), lb=0.0, ub=pos_field_area)
            ]
        # End for

        # for ws_name in zone_ws:
        #     total_f_ws = 0
        #     for f in zone.fields:
        #         total_f_ws += field_areas[f.name][ws_name]
        #     # End for
        # # End for

        # constraints += [Constraint(total_f_ws,
        #                     lb=0.0,
        #                     ub=zone.total_area_ha)]

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
    
    def optimize_irrigation(self, zone, dt: object) -> tuple:
        """Apply Linear Programming to optimize irrigation water use.

        Results can be used to represent percentage mix
        e.g. if the field area is 100 ha, and the optimal area to be
             irrigated by a water source is

            SW: 70 ha
            GW: 30 ha

        and the required amount is 20mm

            SW: 70 / 100 = 0.7 (irrigated area / total area, 70%)
            GW: 30 / 100 = 0.3 (30%)
            
        Then the per hectare amount to be applied from each 
        water source is calculated as:

            `SW = 20mm * 0.7
               = 14mm

            GW = 20mm * 0.3
               = 6mm`
        
        Parameters
        ----------
        * zone : FarmZone
        * dt : datetime object, current datetime

        Returns
        ---------
        * Tuple : OrderedDict[str, float] : keys based on field and water source names
                                            values are hectare area
                  Float : $/ML cost of applying water
        """
        model = self.opt_model
        areas = []
        profit = []
        app_cost = OrderedDict()
        constraints = []

        zone_ws = zone.water_sources
        total_irrigated_area = sum(map(lambda f: f.irrigated_area 
                                    if f.irrigated_area is not None 
                                    else 0.0, zone.fields))
        field_area = {}
        possible_area = {}
        for f in zone.fields:
            f_name = f.name
            did = f"{f_name}__".replace(" ", "_")
            
            if f.irrigation.name == 'dryland':
                areas += [Variable(f"{did}{ws_name}", lb=0, ub=0) 
                            for ws_name in zone_ws]
                continue
            # End if

            # Disable this for now - estimated income includes variable costs
            # Will always incur maintenance costs and crop costs
            # total_pump_cost = sum([ws.pump.maintenance_cost(dt.year) for ws in zone_ws])
            # total_irrig_cost = f.irrigation.maintenance_cost(dt.year)
            # maintenance_cost = (total_pump_cost + total_irrig_cost)

            # estimated gross income - variable costs per ha
            crop_income_per_ha = f.crop.estimate_income_per_ha()
            req_water_ML_ha = f.calc_required_water(dt) / ML_to_mm

            if req_water_ML_ha == 0.0:
                field_area[f_name] = {
                    ws_name: Variable(f"{did}{ws_name}",
                                      lb=0.0,
                                      ub=0.0)
                    for ws_name in zone_ws
                }
            else:
                max_ws_area = zone.possible_area_by_allocation(f)

                field_area[f_name] = {
                    ws_name: Variable(f"{did}{ws_name}",
                                      lb=0, 
                                      ub=max_ws_area[ws_name])
                    for ws_name in zone_ws
                }
            # End if

            # Costs to pump needed water volume from each water source
            app_cost_per_ML = self.ML_water_application_cost(zone, f, req_water_ML_ha)

            app_cost.update({
                f"{did}{k}": v
                for k, v in app_cost_per_ML.items()
            })

            profit += [
                (crop_income_per_ha 
                - (app_cost_per_ML[ws_name] * req_water_ML_ha)
                ) * field_area[f_name][ws_name]
                for ws_name in zone_ws
            ]
        # End for

        # Total irrigation area cannot be more than available area
        constraints += [Constraint(sum(areas),
                                   lb=0.0,
                                   ub=min(total_irrigated_area, zone.total_area_ha))
                        ]

        # 0 <= field1*sw + field2*sw + field_n*sw <= possible area to be irrigated by sw
        for ws_name, w in zone_ws.items():
            alloc = w.allocation
            pos_area = zone.possible_irrigation_area(alloc)

            f_ws_var = []
            for f in zone.fields:
                f_ws_var += [field_area[f.name][ws_name]]
            # End for

            constraints += [Constraint(sum(f_ws_var),
                            lb=0.0,
                            ub=pos_area)]
        # End for

        # Generate appropriate OptLang model
        model = Model.clone(self.opt_model)
        model.objective = Objective(sum(profit), direction='max')
        model.add(constraints)
        model.optimize()

        return model.primal_values, app_cost
    # End optimize_irrigation()

    def possible_area(self, zone, field: Component, ws_name=Optional[str]) -> float:
        if ws_name:
            available_water_ML = zone.water_sources[ws_name].allocation
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
            for ws_name in water_sources:
                if (field.name in k) and (ws_name in k):
                    opt[ws_name] = primals[k] / area
        # End for

        return opt
    # End perc_irrigation_sources()

    def ML_water_application_cost(self, zone, field: Component, req_water_ML_ha: float) -> Dict:
        """Calculate water application cost/ML by each water source.

        Returns
        -------
        * dict[str, float] : water source name and cost per ML
        """
        zone_ws = zone.water_sources
        irrigation = field.irrigation
        i_pressure = irrigation.head_pressure
        flow_rate = irrigation.flow_rate_Lps

        costs = {
            ws_name: (w.source.pump.pumping_costs_per_ML(flow_rate, 
                                                w.source.head + i_pressure) 
                                                 * req_water_ML_ha) 
                                                 + (w.source.cost_per_ML*req_water_ML_ha)
            for ws_name, w in zone_ws.items()
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

        Returns
        ---------
        * dict[str, float] : cost of pumping per ML for each water source
        """
        ML_costs = {ws.name: ws.pump_cost_per_ML(flow_rate_Lps)
                    for ws in zone.water_sources}

        return ML_costs
    # End calc_ML_pump_costs()

    def calc_potential_crop_yield(self, ssm_mm: float, gsr_mm: float, crop: Component) -> float:
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
        * crop : object, Crop component object

        Returns
        -----------
        * Potential yield in tonnes/Ha
        """
        evap_coef_mm = crop.et_coef  # Crop evapotranspiration coefficient (mm)
        wue_coef_mm = crop.wue_coef  # Water Use Efficiency coefficient (kg/mm)

        # maximum rainfall threshold in mm
        # water above this amount does not contribute to crop yield
        max_thres = crop.rainfall_threshold  

        gsr_mm = min(gsr_mm, max_thres)
        return max(0.0, ((ssm_mm + gsr_mm - evap_coef_mm) * wue_coef_mm) / 1000.0)
    # End calc_potential_crop_yield()
