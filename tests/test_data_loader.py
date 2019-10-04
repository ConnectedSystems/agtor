# import pytest
import pandas as pd
import yaml

from agtor import Crop
from agtor.data_interface import load_yaml, get_samples
from agtor.data_interface.crop import load_crop_data, create_crop, collate_crop_data

data_dir = "./data/"

def setup_data():
    crop_dir = f"{data_dir}crops/"
    crop_data = load_yaml(crop_dir, ext='.yml')
    return crop_data


def test_load_crop_data():
    crop_data = setup_data()

    assert "irrigated_barley" in crop_data,\
        "Expected crop data not found!"
    
    for crop_name, data in crop_data.items():
        test_crop = load_crop_data(crop_name, data)
        collate_crop_data(test_crop)
        break
# End test_load_crop_data()


def test_load_nominal():
    crop_data = setup_data()

    for crop_name, data in crop_data.items():
        test_crop = load_crop_data(crop_name, data)
        created_crop = create_crop(test_crop)

        print("Created crop! \n\n")
        print(created_crop)
        break


def test_sampling():
    from ema_workbench.em_framework.samplers import LHSSampler
    crop_data = setup_data()

    crop_name, data = list(crop_data.items())[0]
    test_crop = load_crop_data(crop_name, data)

    params = collate_crop_data(test_crop)
    num_samples = 10

    samples = get_samples(params, num_samples, LHSSampler())

    print(list(samples))



if __name__ == '__main__':
    
    climate_dir = f"{data_dir}climate/"
    tgt = climate_dir + 'farm_climate_data.csv'
    climate_data = pd.read_csv(tgt, index_col=0, parse_dates=True)

    test_load_crop_data()
    test_sampling()
    test_load_nominal()
