from typing import List, Optional, Iterable
from dataclasses import dataclass, field
import itertools as it

from .Component import Component
from .FieldComponent import Infrastructure
from .Crop import Crop
from .consts import ML_to_mm

import pandas as pd

@dataclass
class CropField(Component):
    '''Class representing field that is cropped.'''
    name: str
    total_area_ha: float
    irrigation: Infrastructure
    crop_rotation: Iterable[Crop]
    irrigated_volume: field(init=False)

    # average total available water in soil (mm)
    soil_TAW: Optional[float] = None  

    # soil water deficit in mm, value is 0.0 or above
    soil_SWD: Optional[float] = None
    irrigated_area: Optional[float] = None

    def __post_init__(self):
        self.crop_rotation = it.cycle(self.crop_rotation)
        self.set_next_crop()
        self.irrigated_area = None
        self.ssm = 0.0  # soil moisture at season start
    # End __post_init__()

    def update_SWD(self, rainfall: float, ET: float):
        """Calculate soil water deficit.

        Water deficit is represented as positive values.

        Parameters
        ==========
        * rainfall : Amount of rainfall across timestep in mm
        * ET : Amount of evapotranspiration across timestep in mm
        """
        tmp = self.soil_SWD - (rainfall - ET)
        tmp = max(0.0, min(tmp, self.soil_TAW))
        # self.soil_SWD = 0.0 if np.isclose(tmp, 0.0) else round(tmp, 4)
        self.soil_SWD = round(tmp, 4)
    # End update_SWD()

    def nid(self, dt: object = None) -> float:
        """
        Calculate net irrigation depth in mm, 0.0 or above.

        Equation taken from [Agriculture Victoria](http://agriculture.vic.gov.au/agriculture/horticulture/vegetables/vegetable-growing-and-management/estimating-vegetable-crop-water-use)

        See also:
        * http://www.fao.org/docrep/x5560e/x5560e03.htm
        * https://www.bae.ncsu.edu/programs/extension/evans/ag452-1.html
        * http://dpipwe.tas.gov.au/Documents/Soil-water_factsheet_14_12_2011a.pdf

        :math:`NID` = Effective root depth (:math:`D_{rz}`) :math:`*` Readily Available Water (:math:`RAW`)

        where:

        * :math:`D_{rz}` = :math:`Crop_{root_depth} * Crop_{e_rz}`, where :math:`Crop_{root_depth}` is the estimated root depth for current stage of crop (initial, late, etc.) and :math:`Crop_{e_rz}` is the effective root zone coefficient for the crop. \\
        * :math:`Crop_{e_rz}` is said to be between 1 and 2/3rds of total root depth \\

        * see https://www.agric.wa.gov.au/water-management/calculating-readily-available-water?nopaging=1 \\
          as well as the resources listed above

        * RAW = :math:`p * TAW`, :math:`p` is depletion fraction of crop, :math:`TAW` is Total Available Water in Soil

        As an example, if a crop has a root depth (:math:`RD_{r}`) of 1m, an effective root zone (:math:`RD_{erz}`) coefficient of 0.55, a depletion fraction (p) of 0.4 and the soil has a TAW of 180mm: \\
        :math:`(RD_{r} * RD_{erz}) * (p * TAW)`
        :math:`(1 * 0.55) * (0.4 * 180)`

        :returns: float, net irrigation depth as negative value
        """
        crop = self.crop
        coefs = crop.get_stage_coefs(dt)

        dep_frac = self.get_nominal(coefs['depletion_fraction'])
        e_rootzone_m = (crop.root_depth_m * crop.effective_root_zone)

        soil_RAW = self.soil_TAW * dep_frac
        return (e_rootzone_m * soil_RAW)
    # End nid()
        
    def calc_required_water(self, dt=None) -> float:
        """Volume of water to maintain moisture at net irrigation depth.

        Factors in irrigation efficiency.
        Values are given in mm.
        """
        to_nid = self.soil_SWD - self.nid(dt)
        if to_nid < 0.0:
            return 0.0
        # End if
        
        tmp = self.soil_SWD / self.irrigation.efficiency
        return round(tmp, 4)
    # End calc_required_water()

    def calc_possible_area(self, vol_ML: float) -> float:
        if vol_ML == 0.0:
            return 0.0

        area = self.total_area_ha if self.irrigated_area is None else self.irrigated_area
        req_water_mm = self.calc_required_water()
        if req_water_mm == 0.0:
            return area
        
        ML_per_ha = (req_water_mm / ML_to_mm)
        perc_area = (vol_ML / (ML_per_ha * area))
        
        return min(perc_area * area, area)
    # End calc_possible_area()

    def set_next_crop(self):
        self.crop = next(self.crop_rotation)
        self.ini_state()
    # End set_next_crop()

    def ini_state(self):
        self.reset_state()
        self.plant_date = self.crop.plant_date
    # End set_crop_state()

    def reset_state(self):
        self.sowed = False
        self.harvested = False
        # self.nid = 0.0
        self.irrigated_area = None
        self.irrigated_volume = 0.0

        try:
            del self.harvest_date
        except AttributeError:
            # not an attribute, so is okay
            pass
    # End reset()

# End FarmField()


if __name__ == '__main__':
    from .Irrigation import Irrigation
    from .Crop import Crop

    irrig = Irrigation('Gravity', 2000.0, (1, 0.05), (5, 0.2), True, 0.5)
    crop_rotation = [Crop('Wheat'), Crop('Barley'), Crop('Canola')]

    Field = FarmField(100.0, irrig, crop_rotation)
