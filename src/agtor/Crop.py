from dataclasses import dataclass

@dataclass
class Crop:
    name: str = ''
    growth_pattern: object = None

    yield_per_ha: float = None
    price_per_yield: float = None
    variable_cost_per_ha: float = None
    water_use_ML_per_ha: float = None
    root_depth_m: float = None
    et_coef: float = None
    wue_coef: float = None
    rainfall_threshold: float = None
    ssm_coef: float = None
# End Crop()