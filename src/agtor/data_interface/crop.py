from typing import Dict
import pandas as pd

from agtor import Crop
from agtor.data_interface import load_yaml, generate_params, sort_param_types

from ema_workbench import Constant, Constant, RealParameter, CategoricalParameter


def load_crop_data(name, crop_data, override=None):
    # 'Crop', crop name, grouping, parameter
    # growth_coefs = pd.DataFrame(crop_data['growth_coefficients'])

    prefix = f"Crop___{name}__{{}}"
    props = generate_params(prefix.format('properties'), crop_data['properties'], override)
    stages = generate_params(prefix.format('growth_stages'), crop_data['growth_stages'], override)

    # # Derive harvest day
    # tmp = sum([v.value for v in stages.values()])
    # stages['harvest'] = Constant(prefix.format('growth_stages')+'__harvest', tmp)

    return {
        'name': name,
        'crop_type': crop_data["crop_type"], 
        'properties': props, 
        # 'growth_coefficients': growth_coefs,
        'growth_stages': crop_data['growth_stages']
    }
# End load_crop_data()


def collate_crop_data(crop_data: Dict):
    """Produce flat lists of crop-specific parameters.

    Parameters
    ----------
    * crop_data : Dict, of crop_data

    Returns
    -------
    * tuple[List] : (uncertainties, categoricals, and constants)
    """
    unc, cats, consts = [], [], []
    unc, cats, consts = sort_param_types(crop_data['properties'], unc, cats, consts)

    growth_stages = crop_data['growth_stages']
    unc, cats, consts = sort_param_types(growth_stages, unc, cats, consts)

    # growth_coefficients = crop_data['growth_coefficients']
    # unc, cats, consts = sort_param_types(growth_coefficients, unc, cats, consts)

    return unc, cats, consts
# End collate_crop_data()


def create_crop(crop_data):
    """TODO: Generate crop object from data."""

    tmp = crop_data.copy()
    prop = tmp.pop('properties')

    return Crop(**tmp, **prop)
# End create_crop()
