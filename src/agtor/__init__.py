# -*- coding: utf-8 -*-
from pkg_resources import get_distribution, DistributionNotFound

from .consts import *
from .Component import *

from .Crop import *
from .Irrigation import *
from .Pump import *
from .Field import *
from .Zone import *
from .Manager import *
from .Climate import *


try:
    # Change here if project is renamed and does not equal the package name
    dist_name = __name__
    __version__ = get_distribution(dist_name).version
except DistributionNotFound:
    __version__ = 'unknown'
finally:
    del get_distribution, DistributionNotFound
