from agtor import (Irrigation, Pump, Crop, 
                   CropField, FarmZone, WaterSource, Manager, Climate)

from agtor.data_interface import load_yaml, get_samples
import agtor.data_interface.crop as crop_gen
import agtor.data_interface.irrigation as irrig_gen
import agtor.data_interface.watersource as water_gen

import pandas as pd

data_dir = "./tests/data/"

def setup_zone():
    climate_dir = f"{data_dir}climate/"  
    tgt = climate_dir + 'farm_climate_data.csv'
    climate_data = Climate(tgt)

    crop_dir = f"{data_dir}crops/"
    crop_data = load_yaml(crop_dir)
    crop_rotation = []
    for name, data in crop_data.items():
        crop = crop_gen.load_data(name, data)
        crop_rotation += [crop_gen.create(crop)]
    # End for

    irrig_dir = f"{data_dir}irrigation/"
    irrig_specs = load_yaml(irrig_dir)
    for k, v in irrig_specs.items():
        irrig_spec = irrig_gen.load_data(k, v)
        
        # implemented can be set at the field or zone level...
        irrig = irrig_gen.create(irrig_spec, implemented=True)
    # End for

    water_spec_dir = f"{data_dir}water_sources/"
    water_specs = load_yaml(water_spec_dir)
    w_specs = []
    for k, v in water_specs.items():
        water_spec = water_gen.load_data(k, v)

        if water_spec['name'] == 'groundwater':
            pump = Pump('groundwater', 2000.0, 1, 5, 0.05, 0.2, True, 0.7, 0.28, 0.75)
            ini_head = 25.0
        else:
            pump = Pump('surface_water', 2000.0, 1, 5, 0.05, 0.2, True, 0.7, 0.28, 0.75)
            ini_head = 0.0

        ws = water_gen.create(water_spec, pump, ini_head=ini_head)
        w_specs.append(ws)
    # End for

    field1 = CropField('field1', 100.0, irrig, crop_rotation, 25.0, 20.0, 100.0)
    field2 = CropField('field2', 90.0, irrig, crop_rotation, 25.0, 30.0, 100.0)

    z1 = FarmZone('Zone_1', 
                  climate=climate_data,
                  fields=[field1, field2],
                  water_sources=w_specs,
                  allocation={'HR': 200.0, 'LR': 25.0, 'GW': 50.0})
    return z1, w_specs
# End setup_zone()

def test_short_run():
    z1, (deeplead, channel_water) = setup_zone()

    from timeit import default_timer as timer
    from datetime import timedelta

    farmer = Manager()
    time_sequence = z1.climate.index

    start = timer()
    for dt_i in time_sequence[0:(365*5)]:
        if (dt_i.month == 5) and (dt_i.day == 15):
            # reset allocation for test
            z1.gw_allocation = 50.0
            z1.lr_allocation = 25.0
            z1.hr_allocation = 100.0
        z1.run_timestep(farmer, dt_i)
    # End for
    end = timer()

    print("Finished in:", timedelta(seconds=end-start))
# End test_short_run()


if __name__ == '__main__':
    test_short_run()
