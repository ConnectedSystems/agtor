from typing import Dict
import pandas as pd

from agtor import WaterSource
from agtor.data_interface import load_yaml, generate_params, sort_param_types

from ema_workbench import Constant, Constant, RealParameter, CategoricalParameter


def load_data(name, crop_data, override=None):
    prefix = f"WaterSource___{name}__{{}}"
    props = generate_params(prefix.format('properties'), crop_data['properties'], override)

    return {
        'name': name,
        'properties': props
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

    return unc, cats, consts
# End collate_data()


def create(data, pump, ini_head):
    tmp = data.copy()
    prop = tmp.pop('properties')

    return WaterSource(**tmp, **prop, pump=pump, head=ini_head)
# End create()
