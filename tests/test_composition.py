from agtor import (Irrigation, Pump, Crop, CropField, FarmZone, Manager, WaterSource)

def test_zone_management():
    irrig = Irrigation('Gravity', 2000.0, (1, 0.05), (5, 0.2), True, 0.6)

    # None values represent growth_pattern data which I haven't converted yet.
    crop_rotation = [
        Crop('Wheat', None, 3.5, 180.0, 100.0, 0.5),
        Crop('Barley', None, 3.5, 180.0, 100.0, 0.5),
        Crop('Canola', None, 3.5, 180.0, 100.0, 0.5)
    ]

    shallowpump = Pump('surface_water', 2000.0, (1, 0.05), (5, 0.2), True, 0.7, 0.28, 0.75)
    channel_water = WaterSource('surface_water',
                            head=0.0,
                            cost_per_ML=20.0,
                            yearly_costs=100.0,
                            pump=shallowpump
                        )

    deeppump = Pump('groundwater', 2000.0, (1, 0.05), (5, 0.2), True, 0.7, 0.28, 0.75)
    deeplead = WaterSource('groundwater',
                            head=25.0,
                            cost_per_ML=20.0,
                            yearly_costs=100.0,
                            pump=deeppump
                        )

    field1 = CropField('1', 100.0, irrig, crop_rotation, 100.0, 50.0, 20.0)
    field2 = CropField('2', 90.0, irrig, crop_rotation, 100.0, 50.0, 30.0)

    z1 = FarmZone('Zone_1', climate=None, 
                    fields=[field1, field2],
                    water_sources=[channel_water, deeplead],
                    allocation={'HR': 200.0, 'LR': 25.0, 'GW': 50.0})

    Farmer = Manager()
    opt_results = Farmer.optimize_irrigation(z1, 1)

    expected = [0.0, 100.0, 0.0, 90.0]
    opt = list(opt_results.values())
    assert opt == expected,\
        """Optimization results did not match.
        Got: {}
        Expected: {}
        Raw: {}
        """.format(opt, expected, opt_results.values())

    channel_water.head = 25.0
    deeplead.head = 0.0

    opt_results = Farmer.optimize_irrigation(z1, 1)

    expected = [100.0, 0.0, 90.0, 0.0]
    opt = list(opt_results.values())
    assert opt == expected,\
        """Optimization results did not match.
        Got: {}
        Expected: {}
        Raw: {}
        """.format(opt, expected, opt_results)
# End test_zone_management()


if __name__ == '__main__':
    test_zone_management()