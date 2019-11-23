from agtor import (Irrigation, Pump, Crop, CropField, FarmZone, Manager, WaterSource)

import numpy as np
import pandas as pd

import pytest
import pytest_dependency


def setup_zone():
    irrig = Irrigation('Gravity', 2000.0, 1, 5, 0.05, 0.2, 
                       efficiency=0.5, flow_ML_day=12, head_pressure=12)

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

    shallowpump = Pump('surface_water', 2000.0, 1, 5, 0.05, 0.2, 0.7, 0.28, 0.75)
    channel_water = WaterSource('surface_water',
                            head=0.0,
                            cost_per_ML=20.0,
                            cost_per_ha=7.95,
                            yearly_costs=100.0,
                            pump=shallowpump
                        )

    deeppump = Pump('groundwater', 2000.0, 1, 5, 0.05, 0.2, 0.7, 0.28, 0.75)
    deeplead = WaterSource('groundwater',
                            head=25.0,
                            cost_per_ML=20.0,
                            cost_per_ha=7.95,
                            yearly_costs=100.0,
                            pump=deeppump
                        )

    field1 = CropField('field1', 100.0, irrig, crop_rotation, 100.0, 20.0, 100.0)
    field2 = CropField('field2', 90.0, irrig, crop_rotation, 100.0, 30.0, 90.0)

    z1 = FarmZone('Zone_1', climate=None, 
                  fields=[field1, field2],
                  water_sources=[channel_water, deeplead],
                  allocation={'surface_water': 225.0, 'groundwater': 50.0})
    return z1, channel_water, deeplead
# End setup_zone()


@pytest.mark.dependency()
def test_manual_setup():
    setup_zone()


@pytest.mark.dependency(depends=["test_manual_setup"])
def test_naive_management():
    z1, channel_water, deeplead = setup_zone()

    Farmer = Manager()
    dt = pd.to_datetime('1981-01-01')
    opt_results = Farmer.optimize_irrigated_area(z1)
# End test_naive_management()


@pytest.mark.dependency(depends=["test_manual_setup"])
def test_expensive_surface_water():
    z1, channel_water, deeplead = setup_zone()

    channel_water.cost_per_ML = 2000.0
    deeplead.head = 0.0

    Farmer = Manager()
    opt_results = Farmer.optimize_irrigated_area(z1)

    for f in z1.fields:
        f.soil_SWD = 80.0
        f.irrigated_area = Farmer.get_optimum_irrigated_area(f, opt_results)

    dt = pd.to_datetime('1981-01-01')
    opt_results, cost = Farmer.optimize_irrigation(z1, dt)

    opt = list(opt_results.values())
    assert (opt[0] >= opt[1]) and (opt[2] >= opt[3]), \
        """Unexpected results. If surface water is more expensive,
        then expect higher groundwater volume to be used.
        """
# End test_zone_management()


@pytest.mark.dependency(depends=["test_manual_setup"])
def test_expensive_groundwater():
    z1, channel_water, deeplead = setup_zone()

    # Make surface water more attractive for test
    deeplead.head = 1000.0
    channel_water.cost_per_ML = 0.0

    Farmer = Manager()
    opt_results = Farmer.optimize_irrigated_area(z1)

    # Reset allocation for test
    z1.water_sources['groundwater'].allocation = 100.0
    z1.water_sources['surface_water'].allocation = 100.0

    # Reset soil water deficit
    for f in z1.fields:
        f.soil_SWD = 100.0

    dt = pd.to_datetime('1981-01-01')
    opt_results, cost = Farmer.optimize_irrigation(z1, dt)

    opt = list(opt_results.values())
    assert (opt[1] == 50.0) and (sum([opt[0]] + opt[2:]) == 0.0), \
        """Unexpected results. If groundwater is more expensive,
        then expect higher surface water volume to be used.
        Expected: [50.0, 0.0, 0.0, 0.0]
        Got: {}
        """.format(opt_results)
# End test_expensive_groundwater()


@pytest.mark.dependency(depends=["test_manual_setup"])
def test_no_required_irrigation():
    z1, channel_water, deeplead = setup_zone()

    Farmer = Manager()
    opt_results = Farmer.optimize_irrigated_area(z1)

    # No soil water deficit
    for f in z1.fields:
        f.soil_SWD = 0.0

    dt = pd.to_datetime('1981-01-01')
    opt_results, cost = Farmer.optimize_irrigation(z1, dt)
    expected = [0.0, 0.0, 0.0, 0.0]
    opt = list(opt_results.values())
    assert np.allclose(opt, expected),\
        """Optimization results did not match.
        Got: {}
        Expected: {}
        Raw: {}
        """.format(opt, expected, opt_results)
# End test_no_required_irrigation()

if __name__ == '__main__':
    test_manual_setup()
    test_naive_management()
    test_expensive_surface_water()
    test_expensive_groundwater()
