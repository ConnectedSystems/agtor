from dataclasses import dataclass
from typing import List, Tuple, Dict

from .FieldComponent import Infrastructure

@dataclass
class Pump(Infrastructure):
    pump_efficiency: float = 0.7  # Efficiency of pump. Defaults to 0.7 (70%)
    cost_per_kW: float = 0.28  # cost in dollars/kW
    
    # Accounts for efficiency losses between the energy required at the pump
    # shaft and the total energy required. Defaults to 0.75
    derating: float = 0.75

    def cost_per_ha(self, year_step: int, area: float) -> float:
        return self.maintenance_cost(year_step) / area

    def pumping_costs_per_ML(self, flow_rate_Lps: float, 
                             head_pressure: float, 
                             additional_head: float=0.0) -> float:
        """Calculate pumping cost per ML for a given flow rate and head pressure.

        .. :math:
            P(Kw) = (H * Q) / ((102 * Ep) * D)

        where:
        * :math:`H` is head pressure in metres (m)
        * :math:`Q` is Flow in Litres per Second
        * :math:`Ep` is Pump efficiency (defaults to 0.7)
        * :math:`D` is the derating factor
        * :math:`102` is a constant, as given in Velloti & Kalogernis (2013)

        See
          * `Robinson, D. W., 2002 <http://www.clw.csiro.au/publications/technical2002/tr20-02.pdf>`_
          * `Vic. Dept. Agriculture, 2006 <http://agriculture.vic.gov.au/agriculture/farm-management/soil-and-water/irrigation/border-check-irrigation-design>`_
          * `Vellotti & Kalogernis, 2013 <http://irrigation.org.au/wp-content/uploads/2013/06/Gennaro-Velloti-and-Kosi-Kalogernis-presentation.pdf>`_

        :param flow_rate_Lps: required flow rate in Litres per second over the irrigation duration
        :param head_pressure: Head pressure of pumping system in metres. Uses water level of water
                              source if not given.
        :param additional_head: Additional head pressure, typically factored in from the implemented
                                irrigation system
        :param pump_efficiency: Efficiency of pump. Defaults to 0.7 (70%)
        :param derating: Accounts for efficiency losses between the energy required at the pump
                         shaft and the total energy required. Defaults to 0.75
        :param fuel_per_kW: Amount of fuel (in litres) required for a Kilowatt hour.
                            Defaults to 0.25L for diesel (Robinson 2002).
                            Is only used if cost_per_kw is not given.

        :return: float, cost_per_ML
        """
        if flow_rate_Lps <= 0.0:
            return 0.0

        head_pressure += additional_head

        constant = 102.0
        pe = self.pump_efficiency
        dr = self.derating
        energy_required_kW = (head_pressure * flow_rate_Lps) / ((constant * pe) * dr)

        # Litres / minutes in hour / seconds in minute
        hours_per_ML = (1000000.0 / flow_rate_Lps) / 60.0 / 60.0

        cost_per_Hour = self.cost_per_kW * energy_required_kW
        cost_per_ML = (cost_per_Hour * hours_per_ML)

        assert cost_per_ML > 0.0 or np.isclose(cost_per_ML, 0.0), """
        Pumping costs cannot be negative ({})
        flow_rate_Lps: {}
        head pressure: {}
        additional head: {}
        """.format(cost_per_ML, flow_rate_Lps, head_pressure, additional_head)

        return cost_per_ML
    # End pumping_costs_per_ML()

if __name__ == '__main__':
    shallowpump = Pump('shallow', 2000.0, (1, 0.05), (5, 0.2), True, 0.5, 12.0, 0.28)
    deeppump = Pump('deeplead', 2000.0, (1, 0.05), (5, 0.2), True, 0.5, 12.0, 0.28)