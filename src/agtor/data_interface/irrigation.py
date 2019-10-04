from typing import Dict
import pandas as pd

from agtor import Irrigation
from agtor.data_interface import load_yaml, generate_params, sort_param_types

from ema_workbench import Constant, Constant, RealParameter, CategoricalParameter

def load_data(name, data, override=None):
    prefix = f"Irrigation___{name}"
    props = generate_params(prefix, data['properties'], override)

    return {
        'name': name,
        'properties': props
    }
# End load_data()


def collate_data(data: Dict):
    """Produce flat lists of crop-specific parameters.

    Parameters
    ----------
    * crop_data : Dict, of crop_data

    Returns
    -------
    * tuple[List] : (uncertainties, categoricals, and constants)
    """
    unc, cats, consts = sort_param_types(data['properties'], unc=[], cats=[], consts=[])

    return unc, cats, consts
# End collate_data()


def create(data, implemented):
    tmp = data.copy()
    prop = tmp.pop('properties')

    return Irrigation(implemented=implemented, **tmp, **prop)
# End create()