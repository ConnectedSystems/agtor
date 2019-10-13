import pandas as pd

from .Component import Component


class Climate(Component):

    """Serves as an interface to climate data"""

    def __init__(self, data, **kwargs):
        """
        Parameters
        ----------
        * data: str, path and filename of table-like data
        """
        self.data = pd.read_csv(data, index_col=0, parse_dates=True)

        # Set all key word arguments as attributes
        for key, value in kwargs.items():
            setattr(self, key, value)
        # End For

        climate_year = self.data.groupby(by=self.data.index.year).sum()
        self.description = climate_year.describe()
        self.description.loc['90%', :] = climate_year.quantile(q=0.9)

        # self.min_rainfall = self.description.loc['min', 'rainfall']
        # self.max_rainfall = self.description.loc['max', 'rainfall']
        # self.med_rainfall = self.description.loc['50%', 'rainfall']  # Median rainfall
        # self.mean_rainfall = self.description.loc['mean', 'rainfall']
        # self.high_rainfall = self.description.loc['90%', 'rainfall']

    # End init()

    def __getattr__(self, attr):
        return getattr(self.data, attr)
    # End __getattr__()

    # def get_climate_stat(self, attrib, phenom='rainfall'):
    #     """Retrieve climate statistics.

    #     e.g. standard deviation of rainfall

    #     Equivalent to:
    #     `return self.data.groupby(by=self.data.index.year).sum().describe().loc['std', :]`

    #     Examples
    #     --------
    #     ```python
    #     >>> Climate.get_climate_stat('std', 'rainfall')
    #     >>> Climate.get_climate_stat('mean', 'rainfall')
    #     ```

    #     Parameters
    #     ----------
    #     * attrib : str, Climate attribute accessible through a Pandas Dataframe describe() or 90th percentile
    #     * phenom : str, desired climate phenomenon, e.g. rainfall or ET
    #     """
    #     return self.description.loc[attrib, phenom]
    # # End get_climate_stat()

    def annual_rainfall(self, timestep):
        """
        Calculate the total amount of rainfall that occured in a year, given in the timestep

        Parameters
        ----------
        * timestep : datetime or int, indicating year in terms of time step.
        """
        year = timestep if type(timestep) == int else timestep.year
        data = self.data

        year_data = data[data.index.year == year]
        yearly_rainfall = year_data.sum()

        return yearly_rainfall['rainfall']
    # End annual_rainfall()

    def get_season_range(self, start, end):
        """Gets climate data for season range.

        Parameters
        ----------
        * start : datetime, start of range in Y-m-d format, inclusive.
        * end : datetime, end of range in Y-m-d format, inclusive.
        * data : DataFrame, data to extract data from.
        """
        data = self.data
        mask = (data.index >= start) & (data.index <= end)

        return data.loc[mask]
    # End get_season_range()

    def _ensure_datetime(self, start, end):
        if type(start) == str:
            start = pd.to_datetime(start)
        # End if

        if type(end) == str:
            end = pd.to_datetime(end)
        # End if

        assert end > start, 'Season end date cannot be earlier than start date ({} < {} ?)'.format(start, end)

        return start, end
    # End _ensure_datetime()

    def get_seasonal_rainfall(self, season_range, partial_name):
        """Retrieve seasonal rainfall.

        Parameters
        ----------
        * season_range : List-like, start and end dates, can be string or datetime object
        * data : pd.Series, to slice

        Returns
        --------
        numeric of seasonal rainfall
        """
        start, end = self._ensure_datetime(*season_range)
        rain_cols = [c for c in self.data.columns if ('rainfall' in c) and (partial_name in c)]

        return self.get_season_range(start, end).loc[:, rain_cols].sum()[0]
    # End get_seasonal_rainfall()

    def get_seasonal_et(self, season_range, partial_name):
        """Retrieve seasonal rainfall.

        Parameters
        ----------
        * season_range : List-like, start and end dates, can be string or datetime object

        Returns
        --------
        numeric of seasonal rainfall
        """
        start, end = self._ensure_datetime(*season_range)
        et_cols = [c for c in self.data.columns if ('ET' in c) and (partial_name in c)]

        return self.get_season_range(start, end).loc[:, et_cols].sum()[0]
    # End get_seasonal_et()

# End Climate()
