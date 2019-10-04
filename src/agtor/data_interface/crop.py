from typing import Dict
import pandas as pd

from agtor import Crop
from agtor.data_interface import load_yaml, generate_params, sort_param_types

from ema_workbench import Constant, Constant, RealParameter, CategoricalParameter


def load_data(name, crop_data, override=None):
    prefix = f"Crop___{name}__{{}}"
    props = generate_params(prefix.format('properties'), crop_data['properties'], override)
    stages = generate_params(prefix.format('growth_stages'), crop_data['growth_stages'], override)

    return {
        'name': name,
        'crop_type': crop_data["crop_type"], 
        'properties': props,
        'growth_stages': crop_data['growth_stages']
    }
# End load_data()


def collate_data(data: Dict):
    """Produce flat lists of crop-specific parameters.

    Parameters
    ----------
    * data : Dict, of crop data

    Returns
    -------
    * tuple[List] : (uncertainties, categoricals, and constants)
    """
    unc, cats, consts = sort_param_types(data['properties'], unc=[], cats=[], consts=[])

    growth_stages = data['growth_stages']
    unc, cats, consts = sort_param_types(growth_stages, unc, cats, consts)

    return unc, cats, consts
# End collate_data()


def create(data):
    tmp = data.copy()
    prop = tmp.pop('properties')

    return Crop(**tmp, **prop)
# End create()