
class Catchment(object):
    def __init__(self, zones, managers):
        self.zones = zones
        self.managers = managers
    # End __init__()

    def run_timestep(self, dt):
        for z in self.zones:
            farmer = self.managers[z.name]
            z.run_timestep(farmer, dt)
        # End for
    # End run_timestep()
# End Catchment()