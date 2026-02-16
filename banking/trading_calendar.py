'''
Created on 02.02.2026

@author: Wolfg
'''
from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache
from enum import Enum
from typing import Optional, Union

import pandas as pd
from pandas.tseries.offsets import CustomBusinessDay

from banking.message_handler import MessageBoxInfo, get_message, MESSAGE_TEXT


# =====================================================
# Exchange Enum
# =====================================================
class Exchange(Enum):
    XETRA = "XETRA"
    NYSE = "NYSE"
    NASDAQ = "NASDAQ"


# =====================================================
# Base Trading Calendar
# =====================================================
class TradingCalendar:
    weekmask: str = "Mon Tue Wed Thu Fri"

    @classmethod
    def business_day(cls, start_year: int, end_year: int) -> CustomBusinessDay:
        """
        Return a CustomBusinessDay offset for the calendar.
        """
        return CustomBusinessDay(
            holidays=cls.holidays(start_year, end_year),
            weekmask=cls.weekmask,
        )

    @classmethod
    def holidays(cls, start_year: int, end_year: int) -> list[pd.Timestamp]:
        raise NotImplementedError

    @classmethod
    def adjust_period(
        cls,
        start: Union[str, pd.Timestamp],
        end: Union[str, pd.Timestamp],
        bday: Optional[CustomBusinessDay] = None,
        settlement_days: int = 0,
        as_str: bool = True  # If True, return dates as ISO-format strings instead of pd.Timestamp.
    ) -> tuple[pd.Timestamp, pd.Timestamp]:
        """
        Adjust start to next trading day, end to previous trading day.
        Converts string inputs to pd.Timestamp automatically.
        Optionally applies settlement offset (T+n days).
        """
        # Convert to pd.Timestamp if necessary
        if isinstance(start, str):
            start = pd.Timestamp(start)
        if isinstance(end, str):
            end = pd.Timestamp(end)

        if bday is None:
            bday = cls.business_day(start.year, end.year)

        start_adj = start + 0 * bday  # roll forward
        end_adj = end - 0 * bday      # roll backward

        if settlement_days > 0:
            start_adj += settlement_days * bday
            end_adj += settlement_days * bday

        if start_adj > end_adj:
            MessageBoxInfo(
                get_message(
                    MESSAGE_TEXT, 'DATE_NO_XETRA'
                    )
                )
            return (start, end)
        if as_str:
            return start_adj.strftime("%Y-%m-%d"), end_adj.strftime("%Y-%m-%d")
        else:
            return start_adj, end_adj
        return start_adj, end_adj


class XetraCalendar(TradingCalendar):

    @staticmethod
    @lru_cache(maxsize=None)
    def _easter_sunday(year: int) -> date:
        a = year % 19
        b = year // 100
        c = year % 100
        d = b // 4
        e = b % 4
        f = (b + 8) // 25
        g = (b - f + 1) // 3
        h = (19 * a + b - d - g + 15) % 30
        i = c // 4
        k = c % 4
        l = (32 + 2 * e + 2 * i - h - k) % 7
        m = (a + 11 * h + 22 * l) // 451
        month = (h + l - 7 * m + 114) // 31
        day = ((h + l - 7 * m + 114) % 31) + 1
        return date(year, month, day)

    @classmethod
    @lru_cache(maxsize=None)
    def _holidays_for_year(cls, year: int) -> list[pd.Timestamp]:
        easter = cls._easter_sunday(year)
        return [
            pd.Timestamp(year, 1, 1),
            pd.Timestamp(year, 5, 1),
            pd.Timestamp(year, 12, 25),
            pd.Timestamp(year, 12, 26),
            pd.Timestamp(easter - timedelta(days=2)),  # Good Friday
            pd.Timestamp(easter + timedelta(days=1)),  # Easter Monday
        ]

    @classmethod
    @lru_cache(maxsize=None)
    def holidays(cls, start_year: int, end_year: int) -> list[pd.Timestamp]:
        holidays: list[pd.Timestamp] = []
        for year in range(start_year, end_year + 1):
            holidays.extend(cls._holidays_for_year(year))
        return holidays


class USCalendar(TradingCalendar):
    """
    US stock market calendar for NYSE and NASDAQ with all federal holidays.
    """

    @staticmethod
    @lru_cache(maxsize=None)
    def _nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> date:
        d = date(year, month, 1)
        count = 0
        while True:
            if d.weekday() == weekday:
                count += 1
                if count == n:
                    return d
            d += timedelta(days=1)

    @staticmethod
    @lru_cache(maxsize=None)
    def _last_weekday_of_month(year: int, month: int, weekday: int) -> date:
        d = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
        while d.weekday() != weekday:
            d -= timedelta(days=1)
        return d

    @classmethod
    @lru_cache(maxsize=None)
    def _holidays_for_year(cls, year: int) -> list[pd.Timestamp]:
        holidays: list[pd.Timestamp] = []

        # Fixed-date holidays
        fixed = [(1, 1), (7, 4), (12, 25)]
        for m, d in fixed:
            dt = date(year, m, d)
            # Observe if weekend
            if dt.weekday() == 5:  # Saturday → Friday
                dt -= timedelta(days=1)
            elif dt.weekday() == 6:  # Sunday → Monday
                dt += timedelta(days=1)
            holidays.append(pd.Timestamp(dt))

        # Movable US holidays
        holidays.append(pd.Timestamp(cls._nth_weekday_of_month(year, 1, 0, 3)))  # MLK, 3rd Mon Jan
        holidays.append(pd.Timestamp(cls._nth_weekday_of_month(year, 2, 0, 3)))  # Presidents, 3rd Mon Feb
        holidays.append(pd.Timestamp(cls._last_weekday_of_month(year, 5, 0)))     # Memorial, last Mon May
        holidays.append(pd.Timestamp(cls._nth_weekday_of_month(year, 9, 0, 1)))  # Labor, 1st Mon Sep
        holidays.append(pd.Timestamp(cls._nth_weekday_of_month(year, 11, 3, 4)))  # Thanksgiving, 4th Thu Nov

        # Good Friday
        easter = XetraCalendar._easter_sunday(year)
        holidays.append(pd.Timestamp(easter - timedelta(days=2)))

        return sorted(holidays)

    @classmethod
    @lru_cache(maxsize=None)
    def holidays(cls, start_year: int, end_year: int) -> list[pd.Timestamp]:
        all_holidays: list[pd.Timestamp] = []
        for year in range(start_year, end_year + 1):
            all_holidays.extend(cls._holidays_for_year(year))
        return all_holidays


class TradingCalendarFactory:
    @staticmethod
    def get_calendar(exchange: Exchange) -> type[TradingCalendar]:
        if exchange == Exchange.XETRA:
            return XetraCalendar
        elif exchange in [Exchange.NYSE, Exchange.NASDAQ]:
            return USCalendar
        else:
            raise ValueError(f"Unknown exchange: {exchange}")


# US Calendar
us_cls = TradingCalendarFactory.get_calendar(Exchange.NYSE)
us_bday = us_cls.business_day(2010, 2030)

# XETRA Calendar
xetra_cls = TradingCalendarFactory.get_calendar(Exchange.XETRA)
xetra_bday = xetra_cls.business_day(2010, 2030)

"""
# Test: adjust period
start_adj, end_adj = xetra_cls.adjust_period("2026-01-01", "2026-01-03", xetra_bday)
print(start_adj, end_adj)
"""
