# import pytest
import pandas as pd
import yaml

from agtor import Crop
from agtor.data_interface import load_yaml, get_samples
from agtor import Climate
# load_crop_data, create_crop, collate_crop_data

data_dir = "./tests/data/"

def setup_data():
    crop_dir = f"{data_dir}crops/"
    crop_data = load_yaml(crop_dir, ext='.yml')
    return crop_data

def test_spec_loading():
    return setup_data()

def test_loading_climate():
    climate_dir = f"{data_dir}climate/"
    tgt = climate_dir + 'farm_climate_data.csv'
    data = pd.read_csv(tgt, index_col=0, parse_dates=True, 
                       dayfirst=True)
    climate = Climate(data)


def test_load_crop_data():
    crop_data = setup_data()

    assert "irrigated_barley" in crop_data,\
        "Expected crop data not found!"
    
    for crop_name, data in crop_data.items():
        test_crop = Crop.create(data)
        break
# End test_load_crop_data()


def test_load_nominal():
    crop_data = setup_data()

    for crop_name, data in crop_data.items():
        created_crop = Crop.create(data)

        print("Created crop! \n\n")
        print(created_crop)
        break


def test_sampling():
    from ema_workbench.em_framework.samplers import LHSSampler
    crop_data = setup_data()

    crop_name, data = list(crop_data.items())[0]
    test_crop = Crop.load_data(crop_name, data)

    params = Crop.collate_data(data)
    num_samples = 10

    samples = get_samples(params, num_samples, LHSSampler())

    print(list(samples))



if __name__ == '__main__':
    test_loading_climate()
    test_load_crop_data()
    test_sampling()
    test_load_nominal()
