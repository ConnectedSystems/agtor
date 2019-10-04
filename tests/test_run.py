from agtor import (Irrigation, Pump, Crop, 
                   CropField, FarmZone, WaterSource, Manager, Climate)

from agtor.data_interface import load_yaml, get_samples
import agtor.data_interface.crop as crop_gen
import agtor.data_interface.irrigation as irrig_gen

import pandas as pd

data_dir = "./tests/data/"

def setup_zone():
    climate_dir = f"{data_dir}climate/"
    crop_dir = f"{data_dir}crops/"
    irrig_dir = f"{data_dir}irrigation/"

    tgt = climate_dir + 'farm_climate_data.csv'
    climate_data = Climate(tgt)

    crop_data = load_yaml(crop_dir)
    crop_rotation = []
    for name, data in crop_data.items():
        crop = crop_gen.load_data(name, data)
        crop_rotation += [crop_gen.create(crop)]
    # End for

    irrig_specs = load_yaml(irrig_dir)
    for k, v in irrig_specs.items():
        irrig_spec = irrig_gen.load_data(name, v)
        
        # implemented can be set at the field or zone level...
        irrigation = irrig_gen.create(irrig_spec, implemented=True)
        print(irrigation)

    raise TypeError("Debug")

    irrig = Irrigation('Gravity', 2000.0, 1, 5, 0.05, 0.2, True, 0.6)

    shallowpump = Pump('surface_water', 2000.0, (1, 0.05), (5, 0.2), True, 0.7, 0.28, 0.75)
    channel_water = WaterSource('surface_water',
                                head=0.0,
                                cost_per_ML=5.0,
                                yearly_costs=100.0,
                                pump=shallowpump
                                )

    deeppump = Pump('groundwater', 2000.0, (1, 0.05), (5, 0.2), True, 0.7, 0.28, 0.75)
    deeplead = WaterSource('groundwater',
                           head=25.0,
                           cost_per_ML=10.0,
                           yearly_costs=100.0,
                           pump=deeppump
                           )

    field1 = CropField('field1', 100.0, irrig, crop_rotation, 100.0, 50.0, 20.0)
    field2 = CropField('field2', 90.0, irrig, crop_rotation, 100.0, 50.0, 30.0)

    z1 = FarmZone('Zone_1', 
                  climate=climate_data,
                  fields=[field1, field2],
                  water_sources=[channel_water, deeplead],
                  allocation={'HR': 200.0, 'LR': 25.0, 'GW': 50.0})
    return z1, channel_water, deeplead
# End setup_zone()

def test_short_run():
    z1, channel_water, deeplead = setup_zone()

    from timeit import default_timer as timer
    from datetime import timedelta

    farmer = Manager()
    time_sequence = z1.climate.index

    start = timer()
    for dt_i in time_sequence[0:(365*3)]:
        z1.run_timestep(farmer, dt_i)
    # End for
    end = timer()

    print("Finished in:", timedelta(seconds=end-start))
# End test_short_run()


if __name__ == '__main__':
    test_short_run()
