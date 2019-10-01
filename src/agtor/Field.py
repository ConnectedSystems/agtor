from typing import List
from dataclasses import dataclass
import itertools as it

from .FieldComponent import Infrastructure
from .Crop import Crop
from .consts import ML_to_mm

@dataclass
class CropField:
    '''Class representing field that is cropped.'''
    name: str
    total_area_ha: float
    irrigation: Infrastructure
    crop_rotation: List[Crop]

    soil_TAW: float = None  # average total available water in soil (mm)

    # represents soil water deficit in mm, value is 0.0 or above
    soil_SWD: float = None
    nid: float = None  # net irrigation depth in mm, 0.0 or above

    def __post_init__(self):
        self.crop_rotation = it.cycle(self.crop_rotation)
        self.set_next_crop()
        self.irrigated_area = None
    # End __post_init__()

    def calc_SWD(self, rainfall: float, ET: float):
        """Calculate soil water deficit.

        Water deficit is represented as positive values.

        Parameters
        ==========
        * rainfall : Amount of rainfall across timestep in mm
        * ET : Amount of evapotranspiration across timestep in mm
        """
        self.soil_SWD -= rainfall - ET
    # End calc_SWD()
        
    def calc_required_water(self) -> float:
        """Volume of water to maintain moisture at net irrigation depth.

        Factors in irrigation efficiency.
        Values are given in mm.
        """
        to_nid = self.soil_SWD - self.nid
        if to_nid < 0.0:
            return 0.0
        # End if
        
        return self.soil_SWD / self.irrigation.efficiency
    # End calc_required_water()

    def calc_possible_area(self, vol_ML: float) -> float:
        req_water_mm = self.calc_required_water()
        vol_mm = (vol_ML / self.irrigated_area) * ML_to_mm
        return (req_water_mm / vol_mm) * self.irrigated_area

    def calc_field_cost(self, year: int) -> float:
        """Calculate total cost of irrigation and crops.

        Parameters
        ----------
        year : int, time step (important to determine maintenance costs)
        """
        total = self.irrigation.cost_per_ha(year)
        total += self.crop.cost_per_ha()

        total = (total * self.total_area_ha)

        return total
    # End calc_field_cost()

    def set_next_crop(self):
        self.crop = next(self.crop_rotation)
    # End set_next_crop()

    def set_crop_state(self):
        # TODO: Extract details from growth pattern
        raise NotImplementedError("Not yet finished!")
        self.sow_date = ''
        self.harvest_date = ''
        self.nid = 0.0
    # End set_crop_state()

    def reset(self):
        self.sowed = False
        self.harvested = False
        self.nid = 0.0
        self.irrigated_area = None
    # End reset()

# End FarmField()


if __name__ == '__main__':
    from Irrigation import Irrigation
    from Crop import Crop

    irrig = Irrigation('Gravity', 2000.0, (1, 0.05), (5, 0.2), True, 0.5)
    crop_rotation = [Crop('Wheat'), Crop('Barley'), Crop('Canola')]

    Field = FarmField(100.0, irrig, crop_rotation)