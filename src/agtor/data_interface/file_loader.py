from pebble import concurrent

from pebble import ProcessPool
from multiprocessing import cpu_count

from glob import glob
import yaml

def ingest_data(fn):
    with open(fn) as fp:
        loaded = yaml.load(fp, Loader=yaml.FullLoader)
    return loaded
# End ingest_data()


def load_yaml(data_dir, ext='.yml', cpus=None):
    if not ext.startswith('.'):
        raise ValueError("Extension must include period, e.g. '.yml'")

    if not data_dir.endswith("/") or not data_dir.endswith("\\"):
        data_dir += '/'
    
    if not cpus:
        cpus = cpu_count()

    data_files = glob(data_dir+"*{}".format(ext))

    with ProcessPool(max_workers=cpus) as pool:
        collated = pool.map(ingest_data, data_files, timeout=30)
        loaded_dataset = {fn['name']: fn for fn in collated.result()}

    return loaded_dataset
# End load_yaml()