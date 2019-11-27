from typing import Optional, Dict

import numpy as np
import pandas as pd
import warnings

from ema_workbench import RealParameter, Constant, CategoricalParameter

ema_mod = __import__('ema_workbench')


def generate_params(prefix: str, dataset: Dict, override: Optional[Dict]=None):
    """Generate EMA Workbench compatible parameter definitions.

    Parameters
    ----------
    prefix : str
    dataset : dict, of parameters for given component
    override : Dict[str, object], values to override nominals with keys
               based on prefix + name
    
    Returns
    ----------
    * Dict matching structure of dataset
    """
    prefix += '__'
    if override is None:
        override = {}

    for n, vals in dataset.items():
        var_id = prefix+n

        if isinstance(vals, dict):
            dataset[n] = generate_params(prefix, vals, override)
            continue
        
        # Replace nominal value with override value if specified
        if var_id in override:
            vals = override.pop(var_id)
            dataset[n] = Constant(var_id, vals)
            continue

        param = None
        try:
            val_type, *param_vals = vals

            if len(set(param_vals)) == 1:
                dataset[n] = Constant(var_id, param_vals[0])
                continue

            ptype = getattr(ema_mod, val_type)
            param = ptype(var_id, *param_vals[1:], default=param_vals[0])
            dataset[n] = param
            continue

        except (ValueError, TypeError) as e:
            dataset[n] = Constant(var_id, vals)
            continue
        except AttributeError:
            warnings.warn("Old data parsing method used - this wil be deprecated in the future.")
            # Unknown param type, revert to old behaviour
            # To be removed
            nom, lb, ub = vals

            same_value = False
            if not isinstance(nom, str):
                try:
                    param = RealParameter(name=var_id,
                                          default=nom,
                                          lower_bound=lb,
                                          upper_bound=ub)
                except ValueError:
                    same_value = True
            else:
                if (nom == lb) and (ub == lb):
                    same_value = True
                else:
                    if len(set(vals)) > 1:
                        param = CategoricalParameter(name=var_id,
                                                    default=nom,
                                                    categories=vals)
                    else:
                        same_value = True
                # End if
            # End if

            if same_value:
                param = Constant(var_id, nom)

            if param is None:
                raise ValueError("Could not determine parameter type!")
            
            dataset[n] = param
        # End try
    # End for

    return dataset
# End generate_params()


def sort_param_types(element, unc, cats, consts):
    if not isinstance(element, dict):
        return unc, cats, consts

    for el in element.values():
        if isinstance(el, dict):
            unc, cats, consts = sort_param_types(el, unc, cats, consts)
        elif isinstance(el, Constant):
            consts += [el]
        elif isinstance(el, CategoricalParameter):
            cats += [el]
        elif isinstance(el, RealParameter):
            unc += [el]
        # End if
    # End for

    return unc, cats, consts
# End sort_param_types()


def get_samples(params, num_samples, sampler):
    uncerts, cats, consts = params

    design = sampler.generate_designs(uncerts+cats, num_samples)
    const_params = (consts, ) * num_samples

    consts_arr = [[p.value for p in i_row] for i_row in const_params]

    uc_arr = np.array(design.designs)

    combined = np.column_stack(
        [arr for arr in [uc_arr, consts_arr] if len(arr) > 0]
    )

    labels = design.params + [str(i.name) for i in const_params[0]]

    matrix = pd.DataFrame(combined, columns=labels)

    return matrix
# End get_samples()
