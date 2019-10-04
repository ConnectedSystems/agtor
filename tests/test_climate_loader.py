from pathlib import Path
from glob import glob

import pandas as pd


DATA_DIR = Path('./tests/data')
farm_climate = pd.read_csv(str(DATA_DIR)+'/climate/farm_climate_data.csv', index_col=0)

climate_data = {
    str(Path(fn).stem): pd.read_csv(fn, index_col=0)
    for fn in glob("./tests/data/climate/*.csv")[0]
}
