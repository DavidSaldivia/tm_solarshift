"""
Classes for different tariff types
Each class has one method to get the energy breakdown from raw data
and another method to calculate plan cost from raw data/energy breakdown
Rui Tang 2023    
"""
import re
import itertools
import pandas as pd
from datetime import datetime

RATE_TYPE_LIST = ["peak", "offpeak", "shoulder"]
DAY_TYPE_LIST = ["weekday", "weekend"]
DEMAND_PERIOD_RE = "([1-9]|1[0-2])-month"


class FlatPlan(object):
    """class for flat tariff"""

    def __init__(self, tariff_dict):
        self.tariff_dict = tariff_dict

    @classmethod
    def convert_json_tariff(cls, json_tariff):
        """convert json tariffs to the tariff formats used in tariff_params.py

        Args:
            json_tariff ([type]): [description]

        Returns:
            [dict]: a dict with tariff info
        """
        json_tariff = json_tariff.get("charges")
        processed_tariff = {}
        processed_tariff["daily_charge"] = json_tariff["service_charges"][0][
            "rate"
        ]
        processed_tariff["export_flat_rate"] = json_tariff["energy_charges"][
            0
        ]["rate_details"][0]["rate"]
        processed_tariff["flat_rate"] = json_tariff["energy_charges"][1][
            "rate_details"
        ][0]["rate"]
        processed_tariff["additional_yearly_costs"] = 0
        if len(json_tariff["service_charges"]) > 1:
            if json_tariff["service_charges"][1]["rate_type"] == "monthly":
                processed_tariff["additional_yearly_costs"] = (
                    json_tariff["service_charges"][1]["rate"] * 12
                )
        return processed_tariff

    @classmethod
    def get_energy_breakdown(
        cls, raw_data, resolution=300, return_raw_data=False
    ):
        """get the energy breakdown for flat tariff calculation
        note: input energy needs to be in kWh

        Args:
            raw_data ([df]): raw pv/load energy data
            resolution (int, optional): resolution in sec, 5min -> 300. Defaults to 300.

        Returns:
            [dict]: a dict with info for cost calculation
        """
        energy_values = {}
        raw_data["t_stamp"] = pd.to_datetime(raw_data["t_stamp"])
        raw_data["net_energy"] = (
            raw_data["pv_energy"] - raw_data["load_energy"]
        )
        raw_data["import_energy"] = raw_data["net_energy"].clip(upper=0)
        raw_data["export_energy"] = raw_data["net_energy"].clip(lower=0)
        raw_data["import_energy"] = -raw_data["import_energy"]
        total_import_energy = float(raw_data["import_energy"].sum())
        total_export_energy = float(raw_data["export_energy"].sum())
        energy_values["total_import_energy"] = total_import_energy
        energy_values["total_export_energy"] = total_export_energy
        energy_values["num_daily_charge"] = len(raw_data) / (
            3600 / resolution * 24
        )
        if return_raw_data:
            return energy_values, raw_data
        else:
            return energy_values

    def calculate_cost(self, raw_data=None, energy_values=None):
        """calculate costs for flat tariff

        Args:
            raw_data (df, optional): raw data, if not provided
            then energy_values is required. Defaults to None.
            energy_values (dict, optional): energy breakdowns. Defaults to None.

        Returns:
            [float]: cost of the plan
        """
        if energy_values is None:
            energy_values = self.get_energy_breakdown(raw_data)
        plan_cost = (
            energy_values["num_daily_charge"]
            * self.tariff_dict["daily_charge"]
            + self.tariff_dict["flat_rate"]
            * energy_values["total_import_energy"]
            - self.tariff_dict["export_flat_rate"]
            * energy_values["total_export_energy"]
            + self.tariff_dict["additional_yearly_costs"]
            / 365
            * energy_values["num_daily_charge"]
        )
        plan_cost = plan_cost * (1 - self.tariff_dict["discount_rate"])
        return plan_cost


class ToUPlan(object):
    """class for flat tariff"""

    def __init__(self, tariff_dict):
        self.tariff_dict = tariff_dict

    @classmethod
    def convert_json_tariff(cls, json_tariff):
        """convert json tariffs to the tariff formats used in tariff_params.py

        Args:
            json_tariff ([type]): [description]

        Returns:
            [dict]: a dict with tariff info
        """
        json_tariff = json_tariff.get("charges")
        processed_tariff = {}
        processed_tariff["daily_charge"] = json_tariff["service_charges"][0][
            "rate"
        ]
        processed_tariff["export_flat_rate"] = json_tariff["energy_charges"][
            0
        ]["rate_details"][0]["rate"]
        processed_tariff["additional_yearly_costs"] = 0
        if len(json_tariff["service_charges"]) > 1:
            if json_tariff["service_charges"][1]["rate_type"] == "monthly":
                processed_tariff["additional_yearly_costs"] = (
                    json_tariff["service_charges"][1]["rate"] * 12
                )
        num_tou_rates = len(json_tariff["energy_charges"][1]["rate_details"])
        for i in range(0, num_tou_rates):
            tariff = json_tariff["energy_charges"][1]["rate_details"][i]
            rate_name = "{}_rate_{}".format(tariff["type"], tariff["day_type"])
            processed_tariff[rate_name] = tariff["rate"]
            window_name = "{}s_{}".format(tariff["type"], tariff["day_type"])
            new_time_periods = []
            for time_period in tariff["time_periods"]:
                new_time_period = []
                for tstamp in time_period:
                    new_tstamp = str(datetime.strptime(tstamp, "%H:%M").time())
                    new_time_period.append(new_tstamp)
                new_time_periods.append(tuple(new_time_period))
            processed_tariff[window_name] = new_time_periods
        return processed_tariff

    @classmethod
    def get_import_rate(
        cls,
        timestamp,
        weekday,
        tou_dict,
        no_peak_weekday=False,
        no_shoulder_weekday=False,
        no_peak_weekend=False,
        no_shoulder_weekend=False,
    ):
        """
        get seasonal/yearly time of use tariff given the hour & weekday
        :param timestamp: a datetime.time object
        :param weekday: day of a week number, in [0-6]
        :param tou_dict: time of use tariff dict
        :param no_peak_weekday: whether there is no peak periods for weekdays
        :param no_shoulder_weekday: whether there is no shoulder periods for weekdays
        :param no_peak_weekend: whether there is no peak periods for weekends
        :param no_shoulder_weekend: whether there is no shoulder periods for weekends
        :return: electricity rate, the name of the ToU times (peak/offpeak/shoulder
        """
        if weekday > 4:
            if no_peak_weekend is False:
                for t in range(len(tou_dict["peaks_weekend"])):
                    if (
                        timestamp
                        >= datetime.strptime(
                            tou_dict["peaks_weekend"][t][0], "%H:%M:%S"
                        ).time()
                        and timestamp
                        < datetime.strptime(
                            tou_dict["peaks_weekend"][t][1], "%H:%M:%S"
                        ).time()
                    ):
                        return tou_dict["peak_rate_weekend"], "peak"
            if no_shoulder_weekend is False:
                for t in range(len(tou_dict["shoulders_weekend"])):
                    if (
                        timestamp
                        >= datetime.strptime(
                            tou_dict["shoulders_weekend"][t][0], "%H:%M:%S"
                        ).time()
                        and timestamp
                        < datetime.strptime(
                            tou_dict["shoulders_weekend"][t][1], "%H:%M:%S"
                        ).time()
                    ):
                        return tou_dict["shoulder_rate_weekend"], "shoulder"
            return tou_dict["offpeak_rate_weekend"], "offpeak"
        else:
            if no_peak_weekday is False:
                for t in range(len(tou_dict["peaks_weekday"])):
                    if (
                        timestamp
                        >= datetime.strptime(
                            tou_dict["peaks_weekday"][t][0], "%H:%M:%S"
                        ).time()
                        and timestamp
                        < datetime.strptime(
                            tou_dict["peaks_weekday"][t][1], "%H:%M:%S"
                        ).time()
                    ):
                        return tou_dict["peak_rate_weekday"], "peak"
            if no_shoulder_weekday is False:
                for t in range(len(tou_dict["shoulders_weekday"])):
                    if (
                        timestamp
                        >= datetime.strptime(
                            tou_dict["shoulders_weekday"][t][0], "%H:%M:%S"
                        ).time()
                        and timestamp
                        < datetime.strptime(
                            tou_dict["shoulders_weekday"][t][1], "%H:%M:%S"
                        ).time()
                    ):
                        return tou_dict["shoulder_rate_weekday"], "shoulder"
            return tou_dict["offpeak_rate_weekday"], "offpeak"

    @staticmethod
    def assign_weekday(dayofweek):
        """
        return weekday/weekend from weekday number (0-6)
        :param dayofweek: day of week (0-6)
        :return: weekday/weekend
        """
        if dayofweek > 4:
            return "weekend"
        else:
            return "weekday"

    @classmethod
    def get_energy_breakdown(
        cls, raw_data, import_tou_dict, resolution=300, return_raw_data=False
    ):
        """get the energy breakdown for flat tariff calculation
        note: input energy needs to be in kWh

        Args:
            raw_data ([df]): raw pv/load energy data
            import_tou_dict ([dict]): tariff details
            resolution (int, optional): resolution in sec, 5min -> 300.
            Defaults to 300.

        Returns:
            [dict]: a dict with info for cost calculation
        """
        energy_values = {}
        raw_data["t_stamp"] = pd.to_datetime(raw_data["t_stamp"])
        raw_data["times"] = (
            raw_data["t_stamp"] - pd.Timedelta(minutes=5)
        ).dt.time
        raw_data["dayofweek"] = (
            raw_data["t_stamp"] - pd.Timedelta(minutes=5)
        ).dt.dayofweek
        raw_data["month"] = (
            raw_data["t_stamp"] - pd.Timedelta(minutes=5)
        ).dt.month
        raw_data["t_stamp"] = pd.to_datetime(raw_data["t_stamp"])

        raw_data["net_energy"] = (
            raw_data["pv_energy"] - raw_data["load_energy"]
        )
        raw_data["import_energy"] = raw_data["net_energy"].clip(upper=0)
        raw_data["export_energy"] = raw_data["net_energy"].clip(lower=0)
        raw_data["import_energy"] = -raw_data["import_energy"]
        total_import_energy = float(raw_data["import_energy"].sum())
        total_export_energy = float(raw_data["export_energy"].sum())
        energy_values["total_import_energy"] = total_import_energy
        energy_values["total_export_energy"] = total_export_energy
        raw_data["day_type"] = raw_data["dayofweek"].apply(
            lambda x: cls.assign_weekday(x)
        )
        for y, z in itertools.product(RATE_TYPE_LIST, DAY_TYPE_LIST):
            key_name = "{}s_{}".format(y, z)
            if key_name not in import_tou_dict:
                import_tou_dict[key_name] = []

        if len(import_tou_dict["peaks_weekend"]) == 0:
            no_peak_weekend = True
        else:
            no_peak_weekend = False
        if len(import_tou_dict["peaks_weekday"]) == 0:
            no_peak_weekday = True
        else:
            no_peak_weekday = False
        if len(import_tou_dict["shoulders_weekday"]) == 0:
            no_shoulder_weekday = True
        else:
            no_shoulder_weekday = False
        if len(import_tou_dict["shoulders_weekend"]) == 0:
            no_shoulder_weekend = True
        else:
            no_shoulder_weekend = False
            
        raw_data[["import_rate", "rate_type"]] = raw_data.apply(
            lambda row: cls.get_import_rate(
                row["times"],
                row["dayofweek"],
                import_tou_dict,
                no_peak_weekday=no_peak_weekday,
                no_shoulder_weekday=no_shoulder_weekday,
                no_peak_weekend=no_peak_weekend,
                no_shoulder_weekend=no_shoulder_weekend,
            ),
            axis=1,
            result_type="expand",
        )
        raw_data["import_cost"] = (
            raw_data["import_rate"] * raw_data["import_energy"]
        )
        tou_summary = (
            raw_data[["rate_type", "import_cost", "import_energy", "day_type"]]
            .groupby(["rate_type", "day_type"])
            .sum()
            .reset_index()
        )
        for i in range(len(tou_summary)):
            energy_values[
                (
                    str(tou_summary.loc[i, "rate_type"])
                    + "_"
                    + str(tou_summary.loc[i, "day_type"])
                    + "_energy"
                )
            ] = float(tou_summary.loc[i, "import_energy"])
        energy_values["num_daily_charge"] = len(raw_data) / (
            3600 / resolution * 24
        )
        if return_raw_data:
            return energy_values, raw_data
        else:
            return energy_values

    def calculate_cost(self, energy_values=None, raw_data=None):
        """calculate costs for flat tariff

        Args:
            raw_data (df, optional): raw data, if not provided
            then energy_values is required. Defaults to None.
            energy_values (dict, optional): energy breakdowns. Defaults to None.

        Returns:
            [float]: cost of the plan
        """
        if energy_values is None:
            energy_values = self.get_energy_breakdown(
                raw_data, self.tariff_dict
            )
        tou_cost = 0
        for y, z in itertools.product(RATE_TYPE_LIST, DAY_TYPE_LIST):
            # use the energy breakdowns and calculate
            # the costs in different time windows and sum them
            energy_column_name = "{}_{}_energy".format(y, z)
            rate_name = "{}_rate_{}".format(y, z)
            if (
                rate_name in self.tariff_dict
                and energy_column_name in energy_values
            ):
                energy = energy_values[energy_column_name]
                tou_cost = tou_cost + self.tariff_dict[rate_name] * energy
        # first calculate the window costs and
        # then add the supply charge and additional costs
        # each column represents a plan's costs for each site,
        # note we scale the additional yearly costs based on
        # how many days of data is available
        plan_cost = (
            tou_cost
            + energy_values["num_daily_charge"]
            * self.tariff_dict["daily_charge"]
            - self.tariff_dict["export_flat_rate"]
            * energy_values["total_export_energy"]
            + self.tariff_dict["additional_yearly_costs"]
            / 365
            * energy_values["num_daily_charge"]
        )
        plan_cost = plan_cost * (1 - self.tariff_dict["discount_rate"])
        return plan_cost


class DemandPlan(object):
    """class for demand tariff
    Note for calculating plan costs, this class only looks
    at demand costs as an add-on, the rest of the costs (step/flat/tou)
    are calculated using other class methods
    """

    def __init__(self, tariff_dict):
        self.tariff_dict = tariff_dict

    def calculate_cost(self, raw_data):
        """calculate demand costs using raw data
        'demand_power' is required in raw data as
        a column for (load-pv) in W.
        Input data needs to be in 30-min resolution

        Args:
            raw_data (df): input raw data

        Returns:
            cost: total demand costs in AUD
        """
        raw_data["t_stamp"] = pd.to_datetime(raw_data["t_stamp"])
        raw_data["times"] = (
            raw_data["t_stamp"] - pd.Timedelta(minutes=30)
        ).dt.time
        raw_data["date"] = (
            raw_data["t_stamp"] - pd.Timedelta(minutes=30)
        ).dt.date
        raw_data["dayofweek"] = (
            raw_data["t_stamp"] - pd.Timedelta(minutes=30)
        ).dt.dayofweek
        raw_data["year"] = (
            raw_data["t_stamp"] - pd.Timedelta(minutes=30)
        ).dt.year
        raw_data["month"] = (
            raw_data["t_stamp"] - pd.Timedelta(minutes=30)
        ).dt.month
        # prepare to add year to month-date from tariff dict
        year_list = raw_data.year.unique().tolist()
        raw_data["day_type"] = raw_data["dayofweek"].apply(
            lambda x: ToUPlan.assign_weekday(x)
        )
        season_info_list = list(
            filter(
                lambda x: x["tariff_type"] == "demand",
                self.tariff_dict["charges"]["energy_charges"],
            )
        )
        total_demand_cost = 0
        for season_info in season_info_list:
            query_info = None
            for date_window in season_info["season"]:
                start_date = datetime.strptime(
                    date_window["date_start"], "%m-%d"
                )
                end_date = datetime.strptime(date_window["date_end"], "%m-%d")
                # add year so we could query by date ranges
                for year_number in year_list:
                    new_start_date = start_date.replace(year=year_number)
                    new_end_date = end_date.replace(
                        year=year_number
                    ) + pd.Timedelta(days=1)
                    new_window = f"(t_stamp > '{new_start_date}' & t_stamp <= '{new_end_date}')"
                    if query_info is None:
                        query_info = new_window
                    else:
                        query_info = query_info + " | " + new_window
            if new_start_date == new_end_date:
                # if a whole year has the same rate
                season_data = raw_data
            else:
                season_data = raw_data.query(query_info).reset_index(drop=True)
            if len(season_data) > 1:
                for rate_info in season_info["rate_details"]:
                    # number of months for demand billing period
                    demand_period = int(
                        re.match(
                            DEMAND_PERIOD_RE,
                            rate_info["period"],
                        ).group(1)
                    )
                    # list used for aggregating the demand power
                    groupby_list = ["year", "month"]
                    if demand_period > 1:
                        start_month = season_data.loc[0, "month"]
                        start_year = season_data.loc[0, "year"]
                        season_data["month_number"] = (
                            season_data["month"]
                            - start_month
                            + 12 * (season_data["year"] - start_year)
                        )
                        season_data["demand_period"] = (
                            season_data["month_number"] // demand_period
                        )
                        groupby_list = ["demand_period"]
                    season_time_data = None
                    for day_type_dict, time_windows in rate_info[
                        "window"
                    ].items():
                        # query different time windows and concat dfs
                        if day_type_dict == "weekdays":
                            day_type = "weekday"
                        else:
                            day_type = "weekend"
                        for time_window in time_windows:
                            time_window = [
                                datetime.strptime(time_stamp, "%H:%M").time()
                                for time_stamp in time_window
                            ]
                            start_time = time_window[0]
                            end_time = time_window[1]
                            new_time_window = (
                                "(times >= @start_time & times < @end_time "
                                + "& day_type == @day_type)"
                            )
                            season_time_data_single = season_data.query(
                                new_time_window
                            ).reset_index(drop=True)
                            if season_time_data is None:
                                season_time_data = season_time_data_single
                            else:
                                season_time_data = pd.concat(
                                    [
                                        season_time_data,
                                        season_time_data_single,
                                    ],
                                    axis=0,
                                )
                    season_time_data.reset_index(drop=True, inplace=True)
                    selected_columns = groupby_list.copy()
                    selected_columns.append("demand_power")
                    monthly_peak = (
                        season_time_data[selected_columns]
                        .groupby(groupby_list)
                        .max()
                    ).reset_index()
                    if rate_info["rate_type"] == "monthly":
                        if demand_period == 1:
                            monthly_peak["cost"] = (
                                monthly_peak["demand_power"]
                                / 1000
                                * rate_info["rate"]
                            )
                        else:
                            month_count_columns = groupby_list.copy()
                            month_count_columns.append("month_number")
                            month_count = (
                                season_time_data[month_count_columns]
                                .groupby(groupby_list)
                                .nunique()
                            ).reset_index()
                            monthly_peak = monthly_peak.merge(
                                month_count, how="left", on=groupby_list
                            )
                            monthly_peak["cost"] = (
                                monthly_peak["demand_power"]
                                / 1000
                                * rate_info["rate"]
                                * monthly_peak["month_number"]
                            )
                    elif rate_info["rate_type"] == "daily":
                        # if the rate is in kW/day,
                        # need to find number of days
                        # in each demand billing period
                        date_count_columns = groupby_list.copy()
                        date_count_columns.append("date")
                        month_day_count = (
                            season_time_data[date_count_columns]
                            .groupby(groupby_list)
                            .nunique()
                        ).reset_index()
                        monthly_peak = monthly_peak.merge(
                            month_day_count, how="left", on=groupby_list
                        )
                        monthly_peak["cost"] = (
                            monthly_peak["demand_power"]
                            / 1000
                            * rate_info["rate"]
                            * monthly_peak["date"]
                        )
                    total_demand_cost = (
                        total_demand_cost + monthly_peak["cost"].sum()
                    )
        return total_demand_cost


class StepPlan(object):
    """class for step tariff
    note this is for step import tariff
    """

    def __init__(self, tariff_dict):
        self.tariff_dict = tariff_dict

    @classmethod
    def get_energy_breakdown(cls, raw_data, import_step_dict, resolution=300):
        """get the energy breakdown for step tariff calculation

        Args:
            raw_data ([df]): raw pv/load energy data
            resolution (int, optional): resolution in sec, 5min -> 300.
            Defaults to 300.

        Returns:
            energy_values [dict]: a dict with info for cost calculation
        """
        energy_values = {}
        raw_data["t_stamp"] = pd.to_datetime(raw_data["t_stamp"])
        raw_data["net_energy"] = (
            raw_data["pv_energy"] - raw_data["load_energy"]
        )
        raw_data["year"] = (
            raw_data["t_stamp"] - pd.Timedelta(minutes=5)
        ).dt.year
        raw_data["month"] = (
            raw_data["t_stamp"] - pd.Timedelta(minutes=5)
        ).dt.month
        raw_data["quarter"] = raw_data["month"] // 3
        raw_data["date"] = (
            raw_data["t_stamp"] - pd.Timedelta(minutes=5)
        ).dt.date
        raw_data["import_energy"] = raw_data["net_energy"].clip(upper=0)
        # convert to kWh
        raw_data["export_energy"] = raw_data["net_energy"].clip(lower=0)
        raw_data["import_energy"] = -raw_data["import_energy"]
        total_export_energy = float(raw_data["export_energy"].sum())
        energy_values["total_export_energy"] = total_export_energy
        energy_values["num_daily_charge"] = len(raw_data) / (
            3600 / resolution * 24
        )
        # locate the step info
        step_info = list(
            filter(
                lambda x: x["tariff_type"] == "stepped_rate"
                and x["charge_type"] == "plan",
                import_step_dict["charges"]["energy_charges"],
            )
        )
        if len(step_info) > 1:
            print("more than one stepped rate")
            return None
        step_info = step_info[0]
        # get aggregated import
        agg_type = step_info["block_period"]
        if agg_type == "day":
            agg_table = (
                raw_data[["date", "import_energy"]]
                .groupby("date")
                .sum()
                .reset_index()
            )
        elif agg_type == "month":
            agg_table = (
                raw_data[["year", "month", "import_energy"]]
                .groupby(["year", "month"])
                .sum()
                .reset_index()
            )
        elif agg_type == "quarter":
            agg_table = (
                raw_data[["year", "quarter", "import_energy"]]
                .groupby(["year", "quarter"])
                .sum()
                .reset_index()
            )
        elif agg_type == "year":
            agg_table = (
                raw_data[["year", "import_energy"]]
                .groupby("year")
                .sum()
                .reset_index()
            )
        for i in range(len(step_info["rate_details"])):
            energy_values[f"step_{i}_energy"] = 0
            energy_values[f"step_{i}_rate"] = step_info["rate_details"][i][
                "rate"
            ]
        energy_values["num_step"] = len(step_info["rate_details"])
        for import_energy in agg_table["import_energy"].tolist():
            for n in range(len(step_info["rate_details"])):
                step_rate_detail = step_info["rate_details"][n]
                # going through each step
                # step_energy is referring
                # to the energy amount considered for this step
                # after finish calculating a step,
                # deduct the energy from export_energy
                if (
                    step_rate_detail["max_threshold"] != "null"
                    and step_rate_detail["max_threshold"] is not None
                ):
                    if import_energy >= step_rate_detail["max_threshold"]:
                        step_energy = step_rate_detail["max_threshold"]
                        import_energy = import_energy - step_energy
                    else:
                        step_energy = import_energy
                        import_energy = 0
                else:
                    step_energy = import_energy
                    import_energy = 0
                energy_values[f"step_{n}_energy"] = (
                    energy_values[f"step_{n}_energy"] + step_energy
                )
        return energy_values

    def calculate_cost(self, raw_data=None, energy_values=None):
        """calculate costs for step tariff

        Args:
            raw_data (df, optional): raw data, if not provided
            then energy_values is required. Defaults to None.
            energy_values (dict, optional): energy breakdowns.
            Defaults to None.

        Returns:
            plan_cost[float]: cost of the plan
        """
        if energy_values is None:
            energy_values = self.get_energy_breakdown(
                raw_data, self.tariff_dict
            )
        supply_charge = list(
            filter(
                lambda x: x["service_name"] == "daily_supply_charge",
                self.tariff_dict["charges"]["service_charges"],
            )
        )
        additional_yearly_costs = 0
        if len(self.tariff_dict["charges"]["service_charges"]) > 1:
            if (
                self.tariff_dict["charges"]["service_charges"][1]["rate_type"]
                == "monthly"
            ):
                additional_yearly_costs = (
                    self.tariff_dict["charges"]["service_charges"][1]["rate"]
                    * 12
                )
        export_flat_rate = self.tariff_dict["charges"]["energy_charges"][1][
            "rate_details"
        ][0]["rate"]
        plan_cost = (
            energy_values["num_daily_charge"] * supply_charge[0]["rate"]
            - export_flat_rate * energy_values["total_export_energy"]
            + additional_yearly_costs / 365 * energy_values["num_daily_charge"]
        )
        for i in range(energy_values["num_step"]):
            plan_cost = (
                plan_cost
                + energy_values[f"step_{i}_rate"]
                * energy_values[f"step_{i}_energy"]
            )
        return plan_cost


class SeasonalCLPlan(object):
    """class for flat tariff"""

    def __init__(self, tariff_dict):
        self.tariff_dict = tariff_dict

    @classmethod
    def assign_cl_rate(cls, raw_data: pd.DataFrame, cl_dict: dict):
        """
        Assign controlled load rate to each row of raw data
        Args:
            raw_data (df): raw data
            cl_dict (dict): controlled load dictionary
        """
        raw_data["t_stamp"] = pd.to_datetime(raw_data["t_stamp"])
        raw_data["times"] = (
            raw_data["t_stamp"] - pd.Timedelta(minutes=5)
        ).dt.time
        raw_data["date"] = (
            raw_data["t_stamp"] - pd.Timedelta(minutes=5)
        ).dt.date
        raw_data["year"] = (
            raw_data["t_stamp"] - pd.Timedelta(minutes=5)
        ).dt.year
        raw_data["cl_rate"] = 0.0
        year_list = raw_data.year.unique().tolist()
        season_info_list = list(
            filter(
                lambda x: x["tariff_type"] == "controlled_load",
                cl_dict["CL_plan"]["charges"]["energy_charges"],
            )
        )
        for season_info in season_info_list:
            query_info = None
            for date_window in season_info["season_periods"]:
                start_date = datetime.strptime(date_window[0], "%m-%d")
                end_date = datetime.strptime(date_window[1], "%m-%d")
                # add year so we could query by date ranges
                for year_number in year_list:
                    new_start_date = start_date.replace(year=year_number)
                    new_end_date = end_date.replace(
                        year=year_number
                    ) + pd.Timedelta(days=1)
                    new_window = f"(t_stamp > '{new_start_date}' & t_stamp <= '{new_end_date}')"
                    if query_info is None:
                        query_info = new_window
                    else:
                        query_info = query_info + " | " + new_window
            for time_window in season_info["rate_details"][0]["time_periods"]:
                time_window = [
                    datetime.strptime(time_stamp, "%H:%M").time()
                    for time_stamp in time_window
                ]
                start_time = time_window[0]
                end_time = time_window[1]
                new_time_window = "(times >= @start_time & times < @end_time)"
                raw_data.loc[
                    raw_data.query(
                        f"({query_info}) & ({new_time_window})"
                    ).index,
                    "cl_rate",
                ] = season_info["rate_details"][0]["rate"]
        return raw_data
