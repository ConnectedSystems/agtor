from agtor import (Irrigation, Pump, Crop, CropField, FarmZone, Manager, WaterSource)

import numpy as np
import pandas as pd

def setup_zone():
    irrig = Irrigation('Gravity', 2000.0, 1, 5, 0.05, 0.2, True, 0.6, 12, 10)

    # None values represent growth_stages data which I haven't converted yet.
    crop_rotation = [
        Crop('Wheat', 'irrigated_cereal', '05-15', 
             yield_per_ha=3.5, 
             price_per_yield=180.0, 
             variable_cost_per_ha=100.0, 
             root_depth_m=1.0,
             effective_root_zone=0.55,
             water_use_ML_per_ha=3.0,
             growth_stages={
                 'initial': {
                     'stage_length': 40,
                     'depletion_fraction': 0.55
                 }
             }),
        Crop('Barley', 'irrigated_cereal', '05-15',
             yield_per_ha=3.5, 
             price_per_yield=180.0, 
             variable_cost_per_ha=100.0, 
             root_depth_m=1.0,
             effective_root_zone=0.55,
             water_use_ML_per_ha=3.0,
             growth_stages={
                 'initial': {
                     'stage_length': 40,
                     'crop_coefficient': 0.15,
                     'depletion_fraction': 0.55
                 }
             }),
        Crop('Canola', 'irrigated_cereal', '05-15',
             yield_per_ha=3.5, 
             price_per_yield=180.0, 
             variable_cost_per_ha=100.0, 
             root_depth_m=1.0,
             effective_root_zone=0.55,
             water_use_ML_per_ha=3.0,
             growth_stages={
                 'initial': {
                     'stage_length': 40,
                     'crop_coefficient': 0.15,
                     'depletion_fraction': 0.55
                 }
             })
    ]

    shallowpump = Pump('surface_water', 2000.0, 1, 5, 0.05, 0.2, True, 0.7, 0.28, 0.75)
    channel_water = WaterSource('surface_water',
                            head=0.0,
                            cost_per_ML=20.0,
                            cost_per_ha=7.95,
                            yearly_costs=100.0,
                            pump=shallowpump
                        )

    deeppump = Pump('groundwater', 2000.0, 1, 5, 0.05, 0.2, True, 0.7, 0.28, 0.75)
    deeplead = WaterSource('groundwater',
                            head=25.0,
                            cost_per_ML=20.0,
                            cost_per_ha=7.95,
                            yearly_costs=100.0,
                            pump=deeppump
                        )

    field1 = CropField('field1', 100.0, irrig, crop_rotation, 100.0, 50.0, 20.0)
    field2 = CropField('field2', 90.0, irrig, crop_rotation, 100.0, 50.0, 30.0)

    z1 = FarmZone('Zone_1', climate=None, 
                  fields=[field1, field2],
                  water_sources=[channel_water, deeplead],
                  allocation={'HR': 200.0, 'LR': 25.0, 'GW': 50.0})
    return z1, channel_water, deeplead
# End setup_zone()

def test_naive_management():
    z1, channel_water, deeplead = setup_zone()

    Farmer = Manager()
    dt = pd.to_datetime('1981-01-01')
    opt_results = Farmer.optimize_irrigated_area(z1, 1)
# End test_naive_management()

def test_zone_management():
    z1, channel_water, deeplead = setup_zone()

    Farmer = Manager()
    opt_results = Farmer.optimize_irrigated_area(z1, 1)

    for f in z1.fields:
        f.irrigated_area = Farmer.get_optimum_irrigated_area(f, opt_results)

    dt = pd.to_datetime('1981-01-01')
    opt_results, cost = Farmer.optimize_irrigation(z1, dt, 1)

    expected = [0.0, 100.0, 0.0, 90.0]
    opt = list(opt_results.values())
    assert np.allclose(opt, expected),\
        """Optimization results did not match.
        Got: {}
        Expected: {}
        Raw: {}
        """.format(opt, expected, opt_results.values())

    channel_water.head = 1000.0
    deeplead.head = 0.0

    opt_results, cost = Farmer.optimize_irrigation(z1, dt, 1)

    expected = [60.0, 0.0, 60.0, 0.0]
    opt = list(opt_results.values())
    assert np.allclose(opt, expected),\
        """Optimization results did not match.
        Got: {}
        Expected: {}
        Raw: {}
        """.format(opt, expected, opt_results)
# End test_zone_management()


if __name__ == '__main__':
    test_naive_management()
    test_zone_management()
