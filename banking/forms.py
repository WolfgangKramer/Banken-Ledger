#!/usr/bin/env python
# -*- coding: latin-1 -*-
"""
Created on 28.01.2020
    __updated__ = "2024-11-28"
@author: Wolfgang Kramer
"""

import io
import re
import webbrowser
import requests
import ta

from contextlib import redirect_stdout
from yfinance import Ticker
from decimal import Decimal
from bisect import bisect_left
from collections import namedtuple
from datetime import date, timedelta, datetime
from tkinter import filedialog, Menu
from fints.formals import CreditDebit2
from pandas import DataFrame, to_numeric, concat, to_datetime, set_option
from pandastable import TableModel

from banking.mariadb import MariaDB
from banking.declarations_mariadb import (
    TABLE_FIELDS,
    APPLICATION, APPLICATION_VIEW, BANKIDENTIFIER, TRANSACTION_VIEW, STATEMENT, HOLDING_VIEW, HOLDING, TRANSACTION, LEDGER_COA,
    LEDGER, LEDGER_VIEW, ISIN, PRICES, PRICES_ISIN_VIEW, SERVER, LEDGER_DELETE,
    LEDGER_STATEMENT,
    DATABASE_FIELDS_PROPERTIES, TABLE_FIELDS_PROPERTIES,
    DB_adjclose,
    DB_open, DB_high, DB_low, DB_close, DB_volume,
    DB_alpha_vantage,
    DB_account, DB_acquisition_amount, DB_acquisition_price, DB_amount, DB_amount_currency, DB_applicant_name,
    DB_bic, DB_bank_statement_checked,
    DB_closing_balance, DB_closing_currency, DB_closing_status, DB_counter, DB_currency, DB_credit_account, DB_category,
    DB_credit_name,
    DB_directory,
    DB_date, DB_debit_account, DB_debit_name, DB_dividends,
    DB_entry_date, DB_exchange_rate,  DB_exchange_currency_2, DB_exchange_currency_1,
    DB_iban, DB_ISIN, DB_id_no, DB_industry,
    DB_location,
    DB_market_price, DB_name,
    DB_opening_balance, DB_opening_currency, DB_opening_status,   DB_origin, DB_origin_symbol,
    DB_pieces, DB_posted_amount,  DB_price, DB_price_currency, DB_price_date, DB_purpose_wo_identifier, DB_portfolio,
    DB_status,  DB_server, DB_splits, DB_symbol, DB_show_messages,
    DB_total_amount,  DB_type, DB_total_amount_portfolio, DB_transaction_type,  DB_TYPES,
    DB_upload_check,
    DB_validity,
    DB_wkn,
    DB_alpha_vantage_price_period,
    DB_eur_accounting, DB_tax_on_input, DB_value_added_tax,
    DB_earnings, DB_spendings, DB_transfer_account, DB_transfer_rate
)
from banking.declarations import (
    ALPHA_VANTAGE, ALPHA_VANTAGE_REQUIRED, ALPHA_VANTAGE_REQUIRED_COMBO,
    ALPHA_VANTAGE_OPTIONAL_COMBO,
    BUTTON_INDICATOR,
    CURRENCIES, CREDIT,
    DEBIT,
    ERROR, EURO, EDIT_ROW,
    FN_COMPARATIVE,
    FN_DATE, FN_PROFIT_LOSS, FN_TOTAL_PERCENT, FN_PERIOD_PERCENT, FN_DAILY_PERCENT,
    FN_FROM_DATE, FN_TO_DATE,
    FN_SHARE,  FN_INDEX, FN_TOTAL,
    FN_PROFIT_CUM, FN_PIECES_CUM, FN_PROFIT,
    HTTP_CODE_OK,
    Informations,
    OUTPUTSIZE_FULL, OUTPUTSIZE_COMPACT,
    PERCENT, POPUP_MENU_TEXT,
    INFORMATION,
    KEY_BANK_CODE, KEY_BANK_NAME, KEY_MAX_PIN_LENGTH,
    KEY_DOWNLOAD_ACTIVATED,
    KEY_MAX_TAN_LENGTH, KEY_MIN_PIN_LENGTH,
    KEY_VERSION_TRANSACTION_ALLOWED,
    KEY_TAN, MAX_PIN_LENGTH, MAX_TAN_LENGTH,
    KEY_ACC_ALLOWED_TRANSACTIONS, KEY_ACC_PRODUCT_NAME, KEY_ACC_BANK_CODE,
    KEY_PIN, KEY_BIC,
    KEY_SERVER, KEY_USER_ID, KEY_IDENTIFIER_DELIMITER,
    LIGHTBLUE,
    MENU_TEXT,  MESSAGE_TEXT, MESSAGE_TITLE, MIN_PIN_LENGTH, MIN_TAN_LENGTH,
    CURRENCY_SIGN, ORIGINS,
    ORIGIN_SYMBOLS, ORIGIN_LEDGER, ORIGIN_BANKDATA_CHANGED, ORIGIN_INSERTED,
    SCRAPER_BANKDATA,
    SEPA_AMOUNT, SEPA_CREDITOR_BANK_LOCATION, SEPA_CREDITOR_BANK_NAME, SEPA_CREDITOR_BIC,
    SEPA_CREDITOR_IBAN, SEPA_CREDITOR_NAME, SEPA_EXECUTION_DATE, SEPA_PURPOSE_1, SEPA_PURPOSE_2,
    SEPA_REFERENCE, SEPA_TRANSFER_APPLCANT_NAMES,
    START_DATE_TRANSACTIONS,
    TechnicalIndicatorData,
    TIME_SERIES_INTRADAY,  TIME_SERIES_DAILY_ADJUSTED,
    TIME_SERIES_WEEKLY,
    TIME_SERIES_MONTHLY, TIME_SERIES_WEEKLY_ADJUSTED,
    ToolbarSwitch, TIME_SERIES_DAILY,
    TRANSACTION_TYPES, TRANSACTION_RECEIPT, TRANSACTION_DELIVERY,
    VALIDITY_DEFAULT, WARNING, KEY_ACC_ACCOUNT_NUMBER, NOT_ASSIGNED, YAHOO,
    WWW_YAHOO,

    COMBO, CHECK,
    BUTTON_ADD_CHART,
    BUTTON_OK, BUTTON_ALPHA_VANTAGE, BUTTON_DATA, BUTTON_CREDIT, BUTTON_COPY, BUTTON_DEBIT,
    BUTTON_SAVE, BUTTON_NEW, BUTTON_APPEND, BUTTON_REPLACE, BUTTON_NEXT, BUTTON_UPDATE,
    BUTTON_DELETE, BUTTON_DELETE_ALL, BUTTON_STANDARD, BUTTON_SAVE_STANDARD, BUTTON_SELECT_ALL,
    BUTTON_PRICES_IMPORT,
    COLOR_HOLDING, COLOR_NOT_ASSIGNED, COLOR_ERROR,
    ENTRY,
    FORMAT_FIXED,
    NUMERIC,
    STANDARD,
    TYP_DECIMAL, TYP_DATE, TYP_ALPHANUMERIC,
    WM_DELETE_WINDOW, FORMAT_VARIABLE,
    )
from banking.formbuilts import (
    Caller,
    BuiltTableRowBox, BuiltPandasBox, BuiltCheckButton, BuiltEnterBox, BuiltText, BuiltSelectBox,
    FieldDefinition, destroy_widget, )
from banking.messagebox import (MessageBoxInfo, MessageBoxTermination)
from banking.utils import (
    application_store,
    Amount,
    check_iban, Calculate,
    dec2,
    date_years, date_days,
    prices_informations_append,
    http_error_code)

message_transaction_new = True  # Switch to show Message just once


def _set_defaults(field_defs=[FieldDefinition()], default_values=(1,)):

    if default_values:
        if len(field_defs) < len(default_values):
            MessageBoxTermination(
                info='SET_DEFAULTS: Items of Field Definition less than Items of Default_Values')
            return False  # thread checking
        for idx, item in enumerate(default_values):
            field_defs[idx].default_value = item
    return field_defs


def import_prices_run(title, mariadb, field_list, state):

    for name in field_list:
        select_isin_data = mariadb.select_table(
            ISIN, [DB_ISIN, DB_symbol, DB_origin_symbol], name=name, result_dict=True)
        if select_isin_data:
            select_isin_data = select_isin_data[0]
            symbol = select_isin_data[DB_symbol]
            origin_symbol = select_isin_data[DB_origin_symbol]
            message_symbol = symbol + '/' + origin_symbol
            isin = select_isin_data[DB_ISIN]
            if state == BUTTON_DELETE:
                mariadb.execute_delete(PRICES, symbol=symbol)
                MessageBoxInfo(title=title, information_storage=Informations.PRICES_INFORMATIONS,
                               message=MESSAGE_TEXT['PRICES_DELETED'].format(
                                   name, message_symbol, isin))
            else:
                if symbol == NOT_ASSIGNED or origin_symbol == NOT_ASSIGNED:
                    MessageBoxInfo(title=title, information_storage=Informations.PRICES_INFORMATIONS, information=WARNING,
                                   message=MESSAGE_TEXT['SYMBOL_MISSING'].format(isin, name))
                else:
                    from_date = date_days.convert('2000-01-01')
                    start_date_prices = from_date
                    if state == BUTTON_APPEND:
                        max_price_date = mariadb.select_max_column_value(
                            PRICES, DB_price_date, symbol=symbol)
                        if max_price_date:
                            from_date = max_price_date + timedelta(days=1)
                    # to_date = date_days.subtract(date.today(), 1)
                    to_date = date.today()
                    if from_date > to_date:
                        MessageBoxInfo(title=title, information_storage=Informations.PRICES_INFORMATIONS,
                                       message=MESSAGE_TEXT['PRICES_ALREADY'].format(
                                           name, message_symbol, origin_symbol, isin, '', to_date))
                    if origin_symbol == YAHOO:
                        tickers = Ticker(symbol)
                        f = io.StringIO()
                        with redirect_stdout(f):
                            dataframe = tickers.history(auto_adjust=False,
                                                        period=None, start=from_date, end=to_date)
                        if f.getvalue():
                            prices_informations_append(
                                INFORMATION, f.getvalue())
                        columns = {"Date": DB_price_date, 'Open': DB_open, 'High': DB_high,
                                   'Low': DB_low, 'Close': DB_close, 'Adj Close': DB_adjclose,
                                   'Dividends': DB_dividends, 'Stock Splits': DB_splits,
                                   'Volume': DB_volume}
                    elif origin_symbol == ALPHA_VANTAGE:
                        function = application_store.get(DB_alpha_vantage_price_period)
                        """
                        By default, outputsize=compact. Strings compact and full are accepted with the following specifications:
                        compact returns only the latest 100 data points;
                        full returns the full-length time series of 20+ years of historical data
                        """
                        url = 'https://www.alphavantage.co/query?function=' + function + '&symbol=' + \
                            symbol + '&outputsize='
                        if from_date == start_date_prices:
                            url = url + OUTPUTSIZE_FULL + '&apikey=' + \
                                application_store.get(DB_alpha_vantage)
                        else:
                            url = url + OUTPUTSIZE_COMPACT + '&apikey=' + \
                                application_store.get(DB_alpha_vantage)
                        data = requests.get(url).json()
                        keys = [*data]  # list of keys of dictionary data
                        dataframe = None
                        if len(keys) == 2:
                            try:
                                """
                                2. item of dict data contains Time Series as a dict ( *data[1})
                                example: TIME_SERIES_DAILY                                                                {
                                            "Meta Data": {
                                                "1. Information": "Daily Prices (open, high, low, close) and Volumes",
                                                "2. Symbol": "IBM",
                                                "3. Last Refreshed": "2023-07-26",
                                                "4. Output Size": "Compact",
                                                "5. Time Zone": "US/Eastern"
                                            },
                                            "Time Series (Daily)": {
                                                "2023-07-26": {
                                                    "1. open": "140.4400",
                                                    "2. high": "141.2500",
                                                    "3. low": "139.8800",
                                                    "4. close": "141.0700",
                                                    "5. volume": "4046441"
                                                },
                                                "2023-07-25": {
                                                    "1. open": "139.4200",
                                                    "2. high": "140.4300",
                                """
                                data = data[keys[1]]
                                dataframe = DataFrame(data)
                                dataframe = dataframe.T
                                if 'ADJUSTED' in function:
                                    columns = {"index": DB_price_date, '1. open': DB_open,
                                               '2. high': DB_high, '3. low': DB_low, '4. close': DB_close,
                                               '5. adjusted close': DB_adjclose, '6. volume': DB_volume,
                                               '7. dividend amount': DB_dividends,
                                               '8. split coefficient': DB_splits}
                                else:
                                    columns = {"index": DB_price_date, '1. open': DB_open,
                                               '2. high': DB_high, '3. low': DB_low, '4. close': DB_close,
                                               '5. volume': DB_volume}
                            except Exception:
                                prices_informations_append(ERROR, data)
                                MessageBoxInfo(title=title, information_storage=Informations.PRICES_INFORMATIONS,
                                               message=MESSAGE_TEXT['ALPHA_VANTAGE'].format(isin, name))
                                return
                        else:
                            try:
                                data = data['Information']
                            except Exception:
                                pass
                            prices_informations_append(ERROR, data)
                            MessageBoxInfo(title=title, information_storage=Informations.PRICES_INFORMATIONS,
                                           message=MESSAGE_TEXT['ALPHA_VANTAGE'].format(isin, name))
                            return
                    if dataframe.empty:
                        MessageBoxInfo(title=title, information_storage=Informations.PRICES_INFORMATIONS,
                                       message=MESSAGE_TEXT['PRICES_NO'].format(
                                           name, message_symbol, origin_symbol, isin, ''))
                    else:
                        dataframe = dataframe.reset_index()
                        dataframe[DB_symbol] = symbol
                        dataframe.rename(columns=columns, inplace=True)
                        if origin_symbol == YAHOO:
                            dataframe[DB_origin] = YAHOO
                        elif origin_symbol == ALPHA_VANTAGE:
                            dataframe[DB_origin] = ALPHA_VANTAGE
                        try:
                            dataframe[DB_price_date] = dataframe[DB_price_date].apply(
                                lambda x: x.date())
                        except Exception:
                            pass
                        dataframe = dataframe.set_index(
                            [DB_symbol, DB_price_date])
                        dataframe.sort_index(inplace=True)
                        period = (
                            dataframe.index[0][1], dataframe.index[-1][1])
                        mariadb.execute_delete(
                            PRICES, symbol=symbol, period=period)
                        if mariadb.import_prices(title, dataframe):
                            MessageBoxInfo(title=title, information_storage=Informations.PRICES_INFORMATIONS,
                                           message=MESSAGE_TEXT['PRICES_LOADED'].format(
                                               name, period, message_symbol, isin))


class AlphaVantageParameter(BuiltEnterBox):
    """
    TOP-LEVEL-WINDOW        EnterBox Alpha vantage API Parameters

    PARAMETER:
        options          Dictionary with Alpha Vantage Parameter Names of all Functions
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        field_dict          Dictionary Of Parameter Values of Function Value
    """

    def __init__(self, title, function, api_key, parameter_list, default_values, alpha_vantage_symbols):

        Caller.caller = self.__class__.__name__
        self.title = ' '.join([title, function.upper()])
        _field_defs = []
        ALPHA_VANTAGE_REQUIRED_COMBO[DB_symbol] = alpha_vantage_symbols
        for parameter in parameter_list:
            if parameter in ALPHA_VANTAGE_REQUIRED:
                if parameter in ALPHA_VANTAGE_REQUIRED_COMBO.keys():
                    _field_defs.append(FieldDefinition(
                        definition=COMBO, name=parameter.upper(), length=25,
                        combo_values=ALPHA_VANTAGE_REQUIRED_COMBO[parameter]))
                else:
                    _field_defs.append(FieldDefinition(
                        definition=ENTRY, name=parameter.upper(), length=25))
            elif parameter in ALPHA_VANTAGE_OPTIONAL_COMBO.keys():
                _field_defs.append(FieldDefinition(
                    definition=COMBO, name=parameter.upper(), length=25, mandatory=False,
                    default_value=ALPHA_VANTAGE_OPTIONAL_COMBO[parameter][0],
                    combo_values=ALPHA_VANTAGE_OPTIONAL_COMBO[parameter]))
            elif parameter == 'apikey':
                _field_defs.append(FieldDefinition(
                    definition=ENTRY, name=parameter.upper(), length=25,
                    default_value=api_key))
            else:
                _field_defs.append(FieldDefinition(
                    definition=ENTRY, name=parameter.upper(), length=25, mandatory=False))
        FieldNames = namedtuple('FieldNames', parameter_list)
        self._field_defs = FieldNames(*_field_defs)
        if default_values:
            _set_defaults(_field_defs, default_values)
        super().__init__(title=title,
                         button1_text=BUTTON_DATA, button2_text=BUTTON_ALPHA_VANTAGE,
                         button3_text=MENU_TEXT['ISIN Table'],
                         field_defs=self._field_defs)

    def button_1_button1(self, event):

        self.button_state = self._button1_text
        self.validation()
        if not self.footer.get():
            self.quit_widget()

    def button_1_button2(self, event):

        self.button_state = self._button2_text
        self.quit_widget()

    def button_1_button3(self, event):

        self.button_state = MENU_TEXT['ISIN Table']
        self.quit_widget()


class AppCustomizing(BuiltTableRowBox):
    """
    TOP-LEVEL-WINDOW        EnterBox Application Customizing
    PARAMETER:
        field_defs          List of Field Definitions (see Class FieldDefintion) Applicat Fields
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        field_dict          Dictionary Of Application Customizing Fields
    """

    def __init__(self,  row_dict):

        Caller.caller = self.__class__.__name__
        alpha_vantage_price_period_list = [
            TIME_SERIES_INTRADAY, TIME_SERIES_DAILY, TIME_SERIES_DAILY_ADJUSTED,
            TIME_SERIES_WEEKLY, TIME_SERIES_WEEKLY_ADJUSTED, TIME_SERIES_MONTHLY,
            TIME_SERIES_WEEKLY_ADJUSTED]
        show_messages_list = [INFORMATION, WARNING, ERROR]
        combo_dict = {DB_alpha_vantage_price_period: alpha_vantage_price_period_list, DB_show_messages: show_messages_list}
        super().__init__(APPLICATION, APPLICATION_VIEW, row_dict, focus_in=[DB_directory], combo_dict=combo_dict)

    def focus_in_action(self, event):

        if event.widget.myId == DB_directory:
            directory = filedialog.askdirectory()
            if directory:
                getattr(self._field_defs, DB_directory).textvar.set(directory)
            getattr(self._field_defs, DB_show_messages).widget.focus_set()


class SelectLedgerAccountCategory(BuiltSelectBox):
    """
    Selection: Ledger Account, Period
    Column Fields are not selectable

    """

    def create_field_defs_list(self):

        field_defs_list = []
        # Accounts
        combo_values = []
        accounts = self.mariadb.select_table(
            LEDGER_COA, [DB_account, DB_name], order=DB_account)
        if accounts:
            for account_name in accounts:
                combo_values.append(
                    ' '.join([account_name[0], account_name[1]]))
            field_defs_list.append(self.create_combo_field(
                DB_account, 50, TYP_ALPHANUMERIC, combo_values))
        else:
            self.footer.set(MESSAGE_TEXT['DATA_NO'].format(LEDGER_COA.upper()))
        # from_date
        field_defs_list.append(self.create_date_field(FN_FROM_DATE))
        # to_date
        field_defs_list.append(self.create_date_field(FN_TO_DATE))
        # initialize empty data_dict
        if not self.data_dict:
            self.data_dict[FN_FROM_DATE] = date(datetime.now().year, 1, 1)
            self.data_dict[FN_TO_DATE] = date(datetime.now().year, 12, 31)
        return field_defs_list


class SelectLedgerAccount(BuiltSelectBox):
    """
    Selection: Ledger Account, Period
    """

    def create_field_defs_list(self):

        field_defs_list = []
        # Accounts
        combo_values = []
        accounts = self.mariadb.select_table(
            LEDGER_COA, [DB_account, DB_name], order=DB_account)
        if accounts:
            for account_name in accounts:
                combo_values.append(
                    ' '.join([account_name[0], account_name[1]]))
            field_defs_list.append(self.create_combo_field(
                DB_account, 50, TYP_ALPHANUMERIC, combo_values))
        else:
            self.footer.set(MESSAGE_TEXT['DATA_NO'].format(LEDGER_COA.upper()))
        # from_date
        field_defs_list.append(self.create_date_field(FN_FROM_DATE))
        # to_date
        field_defs_list.append(self.create_date_field(FN_TO_DATE))
        # separator line
        self.separator = [DB_account, FN_TO_DATE]
        # check_buttons
        for field_name in TABLE_FIELDS_PROPERTIES[LEDGER].keys():
            field_defs_list.append(
                self.create_check_field(field_name, TABLE_FIELDS_PROPERTIES[LEDGER][field_name].comment))
        # initialize empty data_dict
        if not self.data_dict:
            self.data_dict[FN_FROM_DATE] = date(datetime.now().year, 1, 1)
            self.data_dict[FN_TO_DATE] = date(datetime.now().year, 12, 31)
        return field_defs_list


class InputPeriod(BuiltSelectBox):
    """
    Selection: Period
    """

    def create_field_defs_list(self):

        field_defs_list = []
        # from_date
        field_defs_list.append(self.create_date_field(FN_FROM_DATE))
        # to_date
        field_defs_list.append(self.create_date_field(FN_TO_DATE))
        # initialize empty data_dict
        if not self.data_dict:
            self.data_dict[FN_FROM_DATE] = date(datetime.now().year, 1, 1)
            self.data_dict[FN_TO_DATE] = date(datetime.now().year, 12, 31)
        return field_defs_list


class InputPeriodNew(InputPeriod):
    """
    Selection: Period
    """

    def get_selection(self):
        """
        no initialization of the selection fields with the used values of last session
        """

        pass


class InputDate(BuiltSelectBox):
    """
    Selection: Date
    """

    def create_field_defs_list(self):

        field_defs_list = []
        # date
        field_defs_list.append(self.create_date_field(FN_DATE))
        # initialize empty data_dict
        if not self.data_dict:
            self.data_dict[FN_DATE] = date.today()
        return field_defs_list

    def validation_all_addon(self, field_defs):

        if (getattr(field_defs, FN_DATE).widget.get() > '{:%Y-%m-%d}'.format(date.today())):
            getattr(self._field_defs, FN_DATE).textvar.set(date.today())


class InputDateHolding(InputPeriod):
    """
    TOP-LEVEL-WINDOW        EnterBox ToDate FromDate
                            with adjusted dates

    PARAMETER:
        see BuiltSelectBox
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        field_dict          {'TO_Date':YYYY-MM-DD, 'From_Date':YYYY-MM-DD}
    """

    def validation_all_addon(self, field_defs):
        from_date = getattr(field_defs, FN_FROM_DATE).widget.get()
        _date = self._validate_date(from_date)
        if _date:
            getattr(self._field_defs, FN_FROM_DATE).textvar.set(
                _date)  # adjusted date returned
        to_date = getattr(field_defs, FN_TO_DATE).widget.get()
        _date = self._validate_date(to_date)
        if _date:
            getattr(self._field_defs, FN_TO_DATE).textvar.set(
                _date)  # adjusted date returned
        if from_date == to_date:
            from_date = date_days.subtract(from_date, 1)
            from_date = date_days.convert(from_date)
            getattr(self._field_defs, FN_FROM_DATE).textvar.set(
                from_date)  # adjusted date returned
            self.footer.set(MESSAGE_TEXT['DATE_ADJUSTED'])
        if (from_date > to_date):
            self.footer.set(MESSAGE_TEXT['DATE'].format(from_date))

    def _validate_date(self, _date):
        data_exists = self.mariadb.row_exists(
            HOLDING, iban=self.container_dict[DB_iban], price_date=_date)
        if not data_exists:
            _date = self._get_prev_date(_date)
            self.footer.set(MESSAGE_TEXT['DATE_ADJUSTED'])
        return _date

    def _get_prev_date(self, _date):

        data_ = self.mariadb.select_table_distinct(
            HOLDING, [DB_price_date], iban=self.container_dict[DB_iban], order=DB_price_date)
        if data_:
            data = list(map(lambda x: str(x[0]), data_))
            idx = bisect_left(data, _date)
            if idx != 0:
                idx = idx - 1
            return data[idx]
        else:
            return _date


class InputIsins(BuiltSelectBox):
    """
    Selection: Comparision Field  and Isins
    """

    def create_field_defs_list(self):

        field_defs_list = []
        # comparision field_names
        combo_values = [DB_pieces, DB_market_price,
                        DB_total_amount, DB_acquisition_amount, FN_PROFIT_LOSS]
        field_defs_list.append(self.create_combo_field(
            FN_COMPARATIVE, 20, TYP_ALPHANUMERIC, combo_values))
        # separator line
        self.separator = [FN_COMPARATIVE, FN_TO_DATE]
        # check_buttons
        for field_name in self.table.keys():
            field_defs_list.append(self.create_check_field(
                field_name, self.table[field_name]))
        # initialize empty data_dict
        if FN_COMPARATIVE not in self.data_dict.keys():
            self.data_dict[FN_COMPARATIVE] = DB_market_price
        return field_defs_list


class InputDatePrices(BuiltSelectBox):
    """
    Selction: Period and Isins
    """

    def create_field_defs_list(self):

        field_defs_list = []
        # from_date
        field_defs_list.append(self.create_date_field(FN_FROM_DATE))
        # to_date
        field_defs_list.append(self.create_date_field(FN_TO_DATE))
        # selection field_names of table price
        fields_properties = TABLE_FIELDS_PROPERTIES[PRICES]
        for field_name in fields_properties.keys():
            if field_name not in [DB_symbol, DB_price_date, DB_origin]:
                field_defs_list.append(self.create_check_field(
                    field_name, fields_properties[field_name].comment))
                if field_name not in self.data_dict.keys():
                    self.data_dict[field_name] = 0
        # separator line
        self.separator = [FN_TO_DATE, DB_splits]
        # selection ISIN name
        isin_names = self.mariadb.select_table_distinct(
            PRICES_ISIN_VIEW, [DB_ISIN, DB_name], result_dict=True, order=DB_name)
        for isin_dict in isin_names:
            field_defs_list.append(self.create_check_field(
                isin_dict[DB_ISIN], isin_dict[DB_name]))
            self.data_dict[field_name] = 0
        return field_defs_list


class InputDateTable(BuiltSelectBox):
    """
    Selection: Period and Table fields
    """

    def create_field_defs_list(self):

        field_defs_list = []
        fields_properties = TABLE_FIELDS_PROPERTIES[self.table]
        # from_date
        field_defs_list.append(self.create_date_field(FN_FROM_DATE))
        # to_date
        field_defs_list.append(self.create_date_field(FN_TO_DATE))
        # separator line
        self.separator = [FN_TO_DATE]
        # check_buttons
        for field_name in fields_properties.keys():
            field_defs_list.append(self.create_check_field(
                field_name, fields_properties[field_name].comment))
        # initialize empty data_dict
        for field_name in fields_properties.keys():
            if not self.data_dict:
                self.data_dict[field_name] = 0
        return field_defs_list


class InputDateTransactions(BuiltSelectBox):
    """
    Selection: Period and Isins
    """

    def create_field_defs_list(self):

        field_defs_list = []
        # Isin name
        if DB_iban not in self.data_dict.keys():
            transaction_isin = self.mariadb.select_dict(
                TRANSACTION_VIEW, DB_name, DB_ISIN, )
        else:
            transaction_isin = self.mariadb.select_dict(
                TRANSACTION_VIEW, DB_name, DB_ISIN, iban=self.data_dict[DB_iban])
        if transaction_isin == {}:
            MessageBoxInfo(title=self.title, message=MESSAGE_TEXT['DATA_NO'].format(
                '', self.data_dict[DB_iban]))
            combo_values = []
        else:
            combo_values = list(transaction_isin.keys())
        field_defs_list.append(self.create_combo_field(
            DB_name,  DATABASE_FIELDS_PROPERTIES[DB_name].length,
            DATABASE_FIELDS_PROPERTIES[DB_name].typ, combo_values))
        # from_date
        field_defs_list.append(self.create_date_field(FN_FROM_DATE))
        # to_date
        field_defs_list.append(self.create_date_field(FN_TO_DATE))
        # initialize empty data_dict
        if combo_values and DB_name not in self.data_dict.keys():
            self.data_dict[DB_name] = combo_values[0]
        if FN_FROM_DATE not in self.data_dict.keys():
            self.data_dict[FN_FROM_DATE] = START_DATE_TRANSACTIONS
        if FN_TO_DATE not in self.data_dict.keys():
            self.data_dict[FN_TO_DATE] = date.today() + timedelta(days=360)
        return field_defs_list


class InputISIN(BuiltSelectBox):
    """
    Selection: Period and Isins
    """

    def create_field_defs_list(self):

        field_defs_list = []
        if self.container_dict:  # name: isin
            combo_values = list(self.container_dict.keys())
        else:
            MessageBoxInfo(title=self.title, message=MESSAGE_TEXT['DATA_NO'].format(ISIN, ''))
            combo_values = []
        field_def = self.create_combo_field(
            DB_name,  DATABASE_FIELDS_PROPERTIES[DB_name].length,
            DATABASE_FIELDS_PROPERTIES[DB_name].typ, combo_values)
        field_def.selected = True
        field_defs_list.append(field_def)
        field_def = self.create_entry_field(
            DB_ISIN,  DATABASE_FIELDS_PROPERTIES[DB_ISIN].length+1,
            DATABASE_FIELDS_PROPERTIES[DB_ISIN].typ)
        field_def.protected = True
        field_defs_list.append(field_def)
        # from_date
        field_defs_list.append(self.create_date_field(FN_FROM_DATE))
        # to_date
        field_defs_list.append(self.create_date_field(FN_TO_DATE))
        # initialize empty data_dict

        if combo_values and DB_name not in self.data_dict.keys():
            self.data_dict[DB_name] = combo_values[0]
        if DB_ISIN not in self.data_dict.keys():
            if combo_values:
                self.data_dict[DB_ISIN] = self.container_dict[self.data_dict[DB_name]]
        if FN_FROM_DATE not in self.data_dict.keys():
            self.data_dict[FN_FROM_DATE] = date_days.subtract(date.today(), 1)
        if FN_TO_DATE not in self.data_dict.keys():
            self.data_dict[FN_TO_DATE] = date.today()
        return field_defs_list

    def comboboxselected_action(self, event):

        if getattr(self._field_defs, DB_name).name == DB_name:
            getattr(self._field_defs, DB_ISIN).textvar.set(
                self.container_dict[event.widget.get()])


class InputPIN(BuiltEnterBox):
    """
    TOP-LEVEL-WINDOW        EnterBox PIN

    PARAMETER:
        bank_code           Bankleitzahl
        bank_name
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        pin
    """

    def __init__(self, bank_code, bank_name=''):

        self.mariadb = MariaDB()
        self.pin = ''
        Caller.caller = self.__class__.__name__
        self._bank_code = bank_code
        bank_names_dict = self.mariadb.dictbank_names()
        if bank_code in bank_names_dict:
            title = bank_names_dict[bank_code]
        else:
            title = MESSAGE_TITLE
        pin_length = self.mariadb.shelve_get_key(
            bank_code, [KEY_MAX_PIN_LENGTH, KEY_MIN_PIN_LENGTH])
        pin_max_length = MAX_PIN_LENGTH
        if pin_length[KEY_MAX_PIN_LENGTH] is not None:
            pin_max_length = pin_length[KEY_MAX_PIN_LENGTH]
        pin_min_length = MIN_PIN_LENGTH
        if pin_length[KEY_MIN_PIN_LENGTH] is not None:
            pin_min_length = pin_length[KEY_MIN_PIN_LENGTH]
        while True:
            super().__init__(
                header=MESSAGE_TEXT['PIN_INPUT'].format(bank_name, bank_code), title=title,
                button1_text=BUTTON_OK, button2_text=None, button3_text=None,
                field_defs=[FieldDefinition(name=KEY_PIN, length=pin_max_length,
                                            min_length=pin_min_length)]
            )
            if self.button_state == WM_DELETE_WINDOW:
                break
            self.pin = self.field_dict[KEY_PIN]
            if self.pin.strip() not in [None, '']:
                break


class InputTAN(BuiltEnterBox):
    """
    TOP-LEVEL-WINDOW        EnterBox TAN

    PARAMETER:
        bank_code           Bankleitzahl
        bank_name
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        tan
    """

    def __init__(self, bank_code, bank_name):

        Caller.caller = self.__class__.__name__
        self._bank_code = bank_code
        self.mariadb = MariaDB()
        bank_names_dict = self.mariadb.dictbank_names()
        if bank_code in bank_names_dict:
            title = bank_names_dict[bank_code]
        else:
            title = MESSAGE_TITLE
        tan_max_length = self.mariadb.shelve_get_key(bank_code, KEY_MAX_TAN_LENGTH)
        if not tan_max_length:
            tan_max_length = MAX_TAN_LENGTH
        while True:
            super().__init__(
                header=MESSAGE_TEXT['TAN_INPUT'].format(bank_code, bank_name), title=title,
                button1_text=BUTTON_OK, button2_text=None, button3_text=None,
                field_defs=[
                    FieldDefinition(name=KEY_TAN, length=tan_max_length, min_length=MIN_TAN_LENGTH)]
            )
            if self.button_state == WM_DELETE_WINDOW:
                break
            self.tan = self.field_dict[KEY_TAN]
            if self.tan.strip() not in [None, '']:
                break


class BankDataNew(BuiltEnterBox):
    """
    TOP-LEVEL-WINDOW        EnterBox New Bank BankData

    PARAMETER:
        field_defs          List of Field Definitions (see Class FieldDefintion) Bank Data Fields
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        field_dict          Dictinionary Of BankData Fields
    """

    def __init__(self,  title, bank_codes=[]):

        Caller.caller = self.__class__.__name__
        self.bank_codes = bank_codes
        FieldNames = namedtuple('FieldNames', [
            KEY_BANK_CODE, KEY_BANK_NAME, KEY_USER_ID, KEY_PIN, KEY_BIC, KEY_SERVER,
            KEY_IDENTIFIER_DELIMITER, KEY_DOWNLOAD_ACTIVATED])
        field_defs = FieldNames(
            FieldDefinition(definition=COMBO,
                            name=KEY_BANK_CODE, length=8, lformat=FORMAT_FIXED,
                            combo_values=self.bank_codes, selected=True, focus_out=True),
            FieldDefinition(name=KEY_BANK_NAME, length=70, protected=True),
            FieldDefinition(name=KEY_USER_ID, length=20),
            FieldDefinition(name=KEY_PIN, length=10, mandatory=False),
            FieldDefinition(name=KEY_BIC, length=11, lformat=FORMAT_FIXED),
            FieldDefinition(name=KEY_SERVER, length=100),
            FieldDefinition(name=KEY_IDENTIFIER_DELIMITER,
                            length=1, lformat=FORMAT_FIXED, default_value=':'),
            FieldDefinition(name=KEY_DOWNLOAD_ACTIVATED,
                            definition=CHECK,
                            checkbutton_text=KEY_DOWNLOAD_ACTIVATED),
        )
        super().__init__(title=title, button2_text=None, field_defs=field_defs)

    def validation_addon(self, field_def):

        if field_def.name == KEY_BANK_CODE:
            if field_def.widget.get() in self.mariadb.listbank_codes():
                self.footer.set(MESSAGE_TEXT['BANK_CODE_EXIST'].
                                format(field_def.widget.get()))
            else:
                if field_def.widget.get() in list(SCRAPER_BANKDATA.keys()):
                    getattr(self._field_defs,
                            KEY_IDENTIFIER_DELIMITER).textvar.set(
                                SCRAPER_BANKDATA[field_def.widget.get()][1])
                return
        if field_def.name == KEY_SERVER:
            http_code = http_error_code(field_def.widget.get())
            if http_code not in HTTP_CODE_OK:
                self.footer.set(MESSAGE_TEXT['HTTP_INPUT'].
                                format(http_code, field_def.widget.get()))

    def comboboxselected_action(self, event):

        bank_code = getattr(self._field_defs, KEY_BANK_CODE).widget.get()
        field_dict = self.mariadb.select_table(
            BANKIDENTIFIER, [DB_name, DB_bic], result_dict=True, code=bank_code)
        if field_dict and DB_name in field_dict[0]:
            getattr(self._field_defs, KEY_BANK_NAME).textvar.set(
                field_dict[0][DB_name])
        else:
            getattr(self._field_defs, KEY_BANK_NAME).textvar.set('')
        if field_dict and DB_bic in field_dict[0]:
            getattr(self._field_defs, KEY_BIC).textvar.set(
                field_dict[0][DB_bic])
        else:
            getattr(self._field_defs, KEY_BIC).textvar.set('')
        field_dict = self.mariadb.select_table(
            SERVER, [DB_server], result_dict=True, code=bank_code)
        if field_dict and DB_server in field_dict[0]:
            getattr(self._field_defs, KEY_SERVER).textvar.set(
                field_dict[0][DB_server])
        else:
            getattr(self._field_defs, KEY_SERVER).textvar.set('')

    def focus_out_action(self, event):
        if event.widget.myId == KEY_BANK_CODE:
            bank_code = getattr(self._field_defs, KEY_BANK_CODE).widget.get()
            field_dict = self.mariadb.select_table(
                BANKIDENTIFIER, [DB_name, DB_bic], result_dict=True, code=bank_code)
            if not field_dict:

                getattr(self._field_defs, KEY_BANK_NAME).textvar.set('')

                getattr(self._field_defs, KEY_BIC).textvar.set('')

                getattr(self._field_defs, KEY_SERVER).textvar.set('')


class BankDataChange(BuiltEnterBox):
    """
    TOP-LEVEL-WINDOW        EnterBox BankData

    PARAMETER:
        field_defs          List of Field Definitions (see Class FieldDefintion) Bank Data Fields
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        field_dict          Dictionary Of BankData Fields
    """

    def __init__(self, title, bank_code, login_data):

        Caller.caller = self.__class__.__name__
        servers = MariaDB().select_server(code=bank_code)
        field_defs = [
            FieldDefinition(name=KEY_BANK_NAME, length=70, protected=True),
            FieldDefinition(name=KEY_USER_ID, length=20),
            FieldDefinition(name=KEY_PIN, length=10, mandatory=False),
            FieldDefinition(name=KEY_BIC, length=11, lformat=FORMAT_FIXED),
            FieldDefinition(definition=COMBO,
                            name=KEY_SERVER, length=100,
                            combo_values=servers),
            FieldDefinition(name=KEY_IDENTIFIER_DELIMITER, length=1, lformat=FORMAT_FIXED,
                            default_value=':'),
            FieldDefinition(name=KEY_DOWNLOAD_ACTIVATED,
                            definition=CHECK,
                            checkbutton_text=KEY_DOWNLOAD_ACTIVATED), ]
        _set_defaults(field_defs, (login_data[KEY_BANK_NAME],
                                   login_data[KEY_USER_ID], login_data[KEY_PIN],
                                   login_data[KEY_BIC], login_data[KEY_SERVER],
                                   login_data[KEY_IDENTIFIER_DELIMITER],
                                   login_data[KEY_DOWNLOAD_ACTIVATED],))
        super().__init__(title=title, field_defs=field_defs)

    def validation_addon(self, field_def):

        if field_def.name == KEY_SERVER:
            http_code = http_error_code(field_def.widget.get())
            if http_code not in HTTP_CODE_OK:
                self.footer.set(MESSAGE_TEXT['HTTP_INPUT'].
                                format(http_code, field_def.widget.get()))


class BankDelete(BuiltEnterBox):
    """
    TOP-LEVEL-WINDOW        EnterBox BankData

    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        field               Selected ComoboBox Value
    """

    def __init__(self,  title):

        Caller.caller = self.__class__.__name__
        FieldNames = namedtuple('FieldNames', [KEY_BANK_CODE, KEY_BANK_NAME])
        super().__init__(
            title=title, button1_text=BUTTON_DELETE,
            field_defs=FieldNames(
                FieldDefinition(definition=COMBO,
                                name=KEY_BANK_CODE, length=8, selected=True, readonly=True,
                                combo_values=MariaDB().listbank_codes()),
                FieldDefinition(name=KEY_BANK_NAME,
                                length=70, protected=True)
            )
        )

    def button_1_button1(self, event):

        self.button_state = self._button1_text
        self.field_dict = {}
        self.field_dict[KEY_BANK_CODE] = getattr(
            self._field_defs, KEY_BANK_CODE).widget.get()
        self.field_dict[KEY_BANK_NAME] = getattr(
            self._field_defs, KEY_BANK_NAME).widget.get()
        self.quit_widget()

    def comboboxselected_action(self, event):

        getattr(self._field_defs, KEY_BANK_NAME).textvar.set(self.mariadb.shelve_get_key(
            getattr(self._field_defs, KEY_BANK_CODE).widget.get(), KEY_BANK_NAME))


class IsinTableRowBox(BuiltTableRowBox):
    """
    TOP-LEVEL-WINDOW        EnterBox Isin Table Values
    """

    def button_1_button3(self, event):
        """
        Import Prices
        """
        self.validation()
        BuiltEnterBox.button_1_button3(self, event)

    def focus_out_action(self, event):

        if event.widget.myId == DB_ISIN:
            if getattr(self._field_defs, DB_type).widget.get() == FN_INDEX:
                isin_name = getattr(self._field_defs, DB_name).widget.get()
                getattr(self._field_defs, DB_ISIN).textvar.set(isin_name.ljust(12, "0"))
            else:
                isin_code = getattr(self._field_defs, DB_ISIN).widget.get()
                isin_name = self.mariadb.select_table(
                    ISIN, [DB_name], isin_code=isin_code)
                if isin_name:
                    getattr(self._field_defs, DB_name).textvar.set(isin_name[0])
        if event.widget.myId == DB_name:
            isin_name = getattr(self._field_defs, DB_name).widget.get()
            isin_code = self.mariadb.select_table(
                ISIN, [DB_ISIN], name=isin_name)
            if isin_code:
                getattr(self._field_defs, DB_ISIN).textvar.set(isin_code[0])
        if event.widget.myId == DB_ISIN or event.widget.myId == DB_name:
            result = self.mariadb.select_table(
                ISIN, TABLE_FIELDS[ISIN][2:], order=DB_name,
                name=getattr(self._field_defs, DB_name).widget.get())
            if result:
                type_, validity, wkn, origin_symbol, self.symbol, currency, industry, _ = result[
                    0]
                getattr(self._field_defs, DB_type).textvar.set(type_)
                getattr(self._field_defs, DB_validity).textvar.set(validity)
                getattr(self._field_defs, DB_wkn).textvar.set(wkn)
                getattr(self._field_defs, DB_symbol).textvar.set(self.symbol)
                getattr(self._field_defs, DB_origin_symbol).textvar.set(
                    origin_symbol)
                getattr(self._field_defs, DB_currency).textvar.set(currency)
                getattr(self._field_defs, DB_industry).textvar.set(industry)
        if event.widget.myId == DB_type and getattr(self._field_defs, DB_type).widget.get() == FN_INDEX:
            isin_name = getattr(self._field_defs, DB_name).widget.get()
            getattr(self._field_defs, DB_ISIN).textvar.set(isin_name[:12].ljust(12, "_"))
        if event.widget.myId == DB_origin_symbol:
            if ALPHA_VANTAGE == getattr(self._field_defs, DB_origin_symbol).widget.get():
                key_alpha_vantage = application_store.get(DB_alpha_vantage)
                if key_alpha_vantage:
                    name = getattr(self._field_defs, DB_name).widget.get()
                    keywords = name.split(' ')[0]
                    url = 'https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords=' + \
                        keywords + '&apikey=' + key_alpha_vantage
                    r = requests.get(url)
                    data = r.json()
                    message = ' '.join(
                        [INFORMATION, ALPHA_VANTAGE, DB_name.upper() + ':', name, '\n     >', keywords,  '<', 3 * '\n'])
                    for dict_symbols in data['bestMatches']:
                        if dict_symbols['8. currency'] == 'EUR':
                            str_dict_symbols = str(
                                dict_symbols).replace('{', '')
                            str_dict_symbols = str_dict_symbols.replace(
                                '}', '')
                            str_dict_symbols = str_dict_symbols.replace(
                                ',', ',     \n, ')
                            str_dict_symbols = str_dict_symbols.split(",")
                            message = message + \
                                2 * '\n' + '   '.join(str_dict_symbols)
                    prices_informations_append(INFORMATION, message)
                    PrintMessageCode(title=self.title, header=Informations.PRICES_INFORMATIONS,
                                     text=Informations.prices_informations)
            elif YAHOO == getattr(self._field_defs, DB_origin_symbol).widget.get():
                webbrowser.open(WWW_YAHOO)

    def comboboxselected_action(self, event):

        self.focus_out_action(event)

    def validation_addon(self, field_def):
        """
        more field validations
        """
        if field_def.name == DB_symbol:
            symbol = getattr(self._field_defs, DB_symbol).widget.get()
            if symbol != NOT_ASSIGNED:
                result = self.mariadb.select_table(
                    ISIN, [DB_name, DB_symbol], symbol=symbol)
                if len(result) > 0 and result[0][0] != getattr(self._field_defs, DB_name).widget.get():
                    MessageBoxInfo(
                        title=self.title, message=MESSAGE_TEXT['SYMBOL_USED'].format(result))
        elif field_def.name == DB_validity:
            validity = getattr(self._field_defs, DB_validity).widget.get()
            if validity > VALIDITY_DEFAULT:
                getattr(self._field_defs, DB_validity).textvar.set(
                    VALIDITY_DEFAULT)
        elif field_def.name == DB_ISIN:
            isin_code = getattr(self._field_defs, DB_ISIN).widget.get()
            isin_code = isin_code.replace(" ", "")
            isin_code = isin_code.ljust(12, "_")
            getattr(self._field_defs, DB_ISIN).textvar.set(isin_code)
            if not isin_code[0].isalpha():
                # necessary because of use as field name in named tuples (otherwise runtime error)
                self.footer.set(MESSAGE_TEXT['ISIN_ALPHABETIC'])


class LedgerCoaTableRowBox(BuiltTableRowBox):
    """
    TOP-LEVEL-WINDOW        EnterBox LedgerCoa Table Values
    """

    def validation_addon(self, field_def):
        """
        check if account is already used in table ledger_coa
        """
        if field_def.name == DB_iban:
            iban_ = field_def.widget.get()
            if iban_ != NOT_ASSIGNED:
                result = self.mariadb.select_table(
                    LEDGER_COA, [DB_account], iban=iban_)
                if len(result) > 1:
                    account = getattr(self._field_defs,
                                      DB_account).widget.get()
                    for account_tuple in result:
                        if account != account_tuple[0]:
                            self.footer.set(
                                MESSAGE_TEXT['IBAN_USED'].format(account_tuple[0]))
                            return


class LedgerTableRowBox(BuiltTableRowBox):
    """
    TOP-LEVEL-WINDOW        EnterBox Ledger Table Values
    """

    def set_field_def(self, field_def):
        if field_def.name == DB_credit_account:
            field_def.length = DATABASE_FIELDS_PROPERTIES[DB_credit_account].length + \
                DATABASE_FIELDS_PROPERTIES[DB_credit_name].length
            field_def.lformat = FORMAT_VARIABLE   # standard data_type char would be FORMAT_FIXED
        elif field_def.name == DB_debit_account:
            field_def.length = DATABASE_FIELDS_PROPERTIES[DB_debit_account].length + \
                DATABASE_FIELDS_PROPERTIES[DB_debit_name].length
            field_def.lformat = FORMAT_VARIABLE   # standard data_type char would be FORMAT_FIXED
        elif field_def.name == DB_category:
            field_def.upper = True
        return field_def

    def button_1_button1(self, event):

        debit_account = getattr(
            self._field_defs, DB_debit_account).textvar.get()
        if debit_account:
            getattr(self._field_defs, DB_debit_account).textvar.set(
                debit_account[:TABLE_FIELDS_PROPERTIES[LEDGER][DB_credit_account].length])
        credit_account = getattr(
            self._field_defs, DB_credit_account).textvar.get()
        if credit_account:
            getattr(self._field_defs, DB_credit_account).textvar.set(
                credit_account[:TABLE_FIELDS_PROPERTIES[LEDGER][DB_debit_account].length])
        BuiltEnterBox.button_1_button1(self, event)

    def button_1_button2(self, event):

        self.button_state = self._button2_text
        if self.button_state == BUTTON_COPY:
            self.quit_widget()  # selected row as template in insert mode
        else:
            # restore data in update_mode
            BuiltEnterBox.button_1_button2(self, event)

    def show_data(self, status):

        id_no = getattr(self._field_defs, DB_id_no).textvar.get()
        protected = TABLE_FIELDS[STATEMENT]
        result = self.mariadb.select_table(
            LEDGER_STATEMENT, '*', result_dict=True, id_no=id_no, status=status)
        if result:
            ledger_statement = result[0]
            if status == CREDIT:
                title = ' '.join([BUTTON_CREDIT, STATEMENT.upper()])
            else:
                title = ' '.join([BUTTON_DEBIT, STATEMENT.upper()])
            result = self.mariadb.select_table(STATEMENT, '*', order=None, result_dict=True, date_name=None,
                                               iban=ledger_statement[DB_iban], entry_date=ledger_statement[DB_entry_date], counter=ledger_statement[DB_counter])
            if result:
                statement = BuiltTableRowBox(STATEMENT, STATEMENT, result[0],
                                             protected=protected,
                                             title=title,  button1_text=None, button2_text=None)
                if statement.button_state == WM_DELETE_WINDOW:
                    return
        else:
            self.message = MESSAGE_TEXT['LEDGER_ROW']
        self.quit_widget()

    def button_1_button3(self, event):

        self.show_data(CREDIT)

    def button_1_button4(self, event):

        self.show_data(DEBIT)


class SepaCreditBox(BuiltEnterBox):
    """
    TOP-LEVEL-WINDOW        EnterBox SEPA Credit Transfer Data

    PARAMETER:
        field_defs          List of Field Definitions (see Class FieldDefintion)
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        field_dict          Dictionary of SEPA Credit Transfer Data
    """

    def __init__(self, bank, account, title=MESSAGE_TITLE):

        Caller.caller = self.__class__.__name__
        self.mariadb = MariaDB()
        period = (date_years.subtract(date.today(), 2), date.today())
        self.combo_values = self.mariadb.select_sepa_transfer_creditor_names(
            posting_text=SEPA_TRANSFER_APPLCANT_NAMES,
            date_name=DB_entry_date, period=period)
        Field_Names = namedtuple(
            'Field_Names', [SEPA_CREDITOR_NAME, SEPA_CREDITOR_IBAN, SEPA_CREDITOR_BIC,
                            SEPA_CREDITOR_BANK_NAME, SEPA_CREDITOR_BANK_LOCATION, SEPA_AMOUNT,
                            SEPA_PURPOSE_1, SEPA_PURPOSE_2, SEPA_REFERENCE]
        )

        field_defs = Field_Names(
            FieldDefinition(definition=COMBO, name=SEPA_CREDITOR_NAME, length=70, selected=True,
                            combo_values=self.combo_values, combo_insert_value=True, focus_out=True),
            FieldDefinition(name=SEPA_CREDITOR_IBAN,
                            length=34, focus_out=True),
            FieldDefinition(name=SEPA_CREDITOR_BIC,
                            length=11, lformat=FORMAT_FIXED),
            FieldDefinition(name=SEPA_CREDITOR_BANK_NAME, length=70, mandatory=False,
                            protected=True),
            FieldDefinition(name=SEPA_CREDITOR_BANK_LOCATION, length=70, mandatory=False,
                            protected=True),
            FieldDefinition(name=SEPA_AMOUNT, length=14, typ=TYP_DECIMAL),
            FieldDefinition(name=SEPA_PURPOSE_1, length=70, mandatory=False),
            FieldDefinition(name=SEPA_PURPOSE_2, length=70, mandatory=False),
            FieldDefinition(name=SEPA_REFERENCE, length=35, mandatory=False)
        )
        header = MESSAGE_TEXT['SEPA_CRDT_TRANSFER'].format(
            bank.bank_name, account[KEY_ACC_PRODUCT_NAME], account[KEY_ACC_ACCOUNT_NUMBER])
        if 'HKCSE' in account[KEY_ACC_ALLOWED_TRANSACTIONS]:
            Field_Names = namedtuple(
                'Field_Names', [*Field_Names._fields] + [SEPA_EXECUTION_DATE])
            field_defs = Field_Names(
                *field_defs,
                FieldDefinition(name=SEPA_EXECUTION_DATE, length=10, typ=TYP_DATE,
                                default_value=date.today(), mandatory=False))
        super().__init__(
            header=header, title=title,
            button1_text=BUTTON_OK, button2_text=BUTTON_DELETE_ALL,
            field_defs=field_defs)

    def validation_addon(self, field_def):

        if field_def.name == SEPA_CREDITOR_IBAN and not check_iban(field_def.widget.get()):
            self.footer.set(MESSAGE_TEXT['IBAN'])
            return
        if field_def.name == SEPA_EXECUTION_DATE:
            date_ = date_ = field_def.widget.get()[0:10]
            try:
                day = int(date_.split('-')[2])
                month = int(date_.split('-')[1])
                year = int(date_.split('-')[0])
                date_ = date(year, month, day)
            except (ValueError, EOFError, IndexError):
                self.footer.set(MESSAGE_TEXT['DATE'])
                return
            days = date_ - date.today()
            if days.days < 0:
                self.footer.set(MESSAGE_TEXT['DATE_TODAY'])
                return

    def button_1_button1(self, event):

        BuiltEnterBox.button_1_button1(self, event)
        getattr(self._field_defs, SEPA_CREDITOR_NAME).combo_positioning = True
        getattr(self._field_defs, SEPA_CREDITOR_NAME).combo_insert_value = True

    def button_1_button2(self, event):

        self.button_state = self._button2_text
        self.clear_form_fields()
        getattr(self._field_defs, SEPA_CREDITOR_NAME).combo_positioning = True
        getattr(self._field_defs, SEPA_CREDITOR_NAME).combo_insert_value = True

    def clear_form_fields(self):

        getattr(self._field_defs, SEPA_CREDITOR_IBAN).textvar.set('')
        getattr(self._field_defs, SEPA_CREDITOR_BIC).textvar.set('')
        getattr(self._field_defs, SEPA_CREDITOR_BANK_NAME).textvar.set('')
        getattr(self._field_defs, SEPA_CREDITOR_BANK_LOCATION).textvar.set('')
        getattr(self._field_defs, SEPA_AMOUNT).textvar.set('')
        getattr(self._field_defs, SEPA_PURPOSE_1).textvar.set('')
        getattr(self._field_defs, SEPA_PURPOSE_2).textvar.set('')
        getattr(self._field_defs, SEPA_REFERENCE).textvar.set('')

    def comboboxselected_action(self, event):

        result = self.mariadb.select_sepa_transfer_creditor_data(
            applicant_name=getattr(self._field_defs, SEPA_CREDITOR_NAME).widget.get())
        if result:
            applicant_iban, applicant_bic, purpose = result[0]
            getattr(self._field_defs, SEPA_CREDITOR_IBAN).textvar.set(
                applicant_iban)
            getattr(self._field_defs, SEPA_CREDITOR_BIC).textvar.set(
                applicant_bic)
            self._bankdata(applicant_iban)
            getattr(self._field_defs, SEPA_PURPOSE_1).textvar.set(purpose[:70])
            getattr(self._field_defs, SEPA_PURPOSE_2).textvar.set(purpose[70:])

    def focus_out_action(self, event):

        if event.widget.myId == SEPA_CREDITOR_NAME:
            result = self.mariadb.select_sepa_transfer_creditor_data(
                applicant_name=getattr(self._field_defs, SEPA_CREDITOR_NAME).widget.get())
            if not result:
                getattr(self._field_defs, SEPA_CREDITOR_BIC).textvar.set('')
                getattr(self._field_defs, SEPA_CREDITOR_IBAN).textvar.set('')
                getattr(self._field_defs,
                        SEPA_CREDITOR_BANK_NAME).textvar.set('')
                getattr(self._field_defs,
                        SEPA_CREDITOR_BANK_LOCATION).textvar.set('')
                getattr(self._field_defs, SEPA_CREDITOR_BIC).textvar.set('')
                getattr(self._field_defs, SEPA_PURPOSE_1).textvar.set('')
                getattr(self._field_defs, SEPA_PURPOSE_2).textvar.set('')
        if event.widget.myId == SEPA_CREDITOR_IBAN:
            iban = getattr(self._field_defs, SEPA_CREDITOR_IBAN).widget.get()
            iban = iban.replace(' ', '')
            iban = iban.strip()
            getattr(self._field_defs, SEPA_CREDITOR_IBAN).textvar.set(iban)
            self._bankdata(iban)

    def _bankdata(self, iban):
        bank_code = iban[4:12]
        field_dict = self.mariadb.select_table(
            BANKIDENTIFIER, [DB_name, DB_location, DB_bic], result_dict=True, code=bank_code)
        if field_dict and DB_name in field_dict[0]:
            getattr(self._field_defs, SEPA_CREDITOR_BANK_NAME).textvar.set(
                field_dict[0][DB_name])
        if field_dict and DB_location in field_dict[0]:
            getattr(self._field_defs,
                    SEPA_CREDITOR_BANK_LOCATION).textvar.set(field_dict[0][DB_location])
        if field_dict and DB_bic in field_dict[0]:
            getattr(self._field_defs, SEPA_CREDITOR_BIC).textvar.set(
                field_dict[0][DB_bic])


class SelectFields(BuiltCheckButton):
    """
    TOP-LEVEL-WINDOW        Checkbutton

    PARAMETER:
        checkbutton_texts    List  of Fields
        standard             last selection stored in shelve files: key standard
        default_text         initialization of checkbox
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        self.field_list        contains selected check_fields
    """

    def __init__(self,  title=MESSAGE_TITLE,
                 button1_text=BUTTON_NEXT,
                 button2_text=BUTTON_STANDARD, button3_text=BUTTON_SAVE_STANDARD,
                 button4_text=BUTTON_SELECT_ALL,
                 default_texts=[], standard=STANDARD,
                 checkbutton_texts=['Description of Checkbox1',
                                    'Description of Checkbox2',
                                    'Description of Checkbox3']
                 ):

        Caller.caller = self.__class__.__name__
        self.mariadb = MariaDB()
        self.standard = standard
        super().__init__(
            title=title, header=MESSAGE_TEXT['CHECKBOX'],
            button1_text=button1_text, button2_text=button2_text, button3_text=button3_text,
            button4_text=button4_text,
            default_texts=default_texts,
            checkbutton_texts=checkbutton_texts
        )

    def button_1_button2(self, event):

        self.button_state = self._button2_text
        standard = self.mariadb.selection_get(self.standard)
        if standard:
            for idx, check_text in enumerate(self.checkbutton_texts):
                if check_text in standard:
                    self._check_vars[idx].set(1)
                else:
                    self._check_vars[idx].set(0)
        else:
            for idx, check_text in enumerate(self.checkbutton_texts):
                self._check_vars[idx].set(0)

    def button_1_button3(self, event):

        self.button_state = self._button3_text
        self.field_list = []
        for idx, check_var in enumerate(self._check_vars):
            if check_var.get() == 1:
                self.field_list.append(self.checkbutton_texts[idx])
        self.validate_all()
        self.mariadb.selection_put(self.standard, self.field_list)

    def validate_all(self):

        if self.standard == MENU_TEXT['Show'] + MENU_TEXT['Statement']:
            if DB_amount in self.field_list:
                if DB_status not in self.field_list:
                    self.field_list.append(DB_status)
                if DB_currency not in self.field_list:
                    self.field_list.append(DB_currency)
            if DB_opening_balance in self.field_list:
                if DB_opening_status not in self.field_list:
                    self.field_list.append(DB_opening_status)
                if DB_opening_currency not in self.field_list:
                    self.field_list.append(DB_opening_currency)
            if DB_closing_balance in self.field_list:
                if DB_closing_status not in self.field_list:
                    self.field_list.append(DB_closing_status)
                if DB_closing_currency not in self.field_list:
                    self.field_list.append(DB_closing_currency)
        elif self.standard == MENU_TEXT['Show'] + MENU_TEXT['Holding']:
            if (
                (DB_total_amount in self.field_list or
                 DB_total_amount_portfolio in self.field_list or
                 DB_acquisition_amount in self.field_list)
                and
                    DB_amount_currency not in self.field_list):
                self.field_list.append(DB_amount_currency)
            if (
                (DB_market_price in self.field_list or
                 DB_acquisition_price in self.field_list)
                and
                    DB_price_currency not in self.field_list):
                self.field_list.append(DB_price_currency)


class SelectDownloadPrices(BuiltCheckButton):
    """
    TOP-LEVEL-WINDOW        Select ISINs download Prices

    PARAMETER:
        checkbutton_texts    List  of Fields

        default_text         initialization of checkbox
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        self.field_list        contains selected check_fields
    """

    def __init__(self,  title=MESSAGE_TITLE,
                 button1_text=BUTTON_APPEND, button2_text=BUTTON_REPLACE, button3_text=BUTTON_DELETE,
                 checkbutton_texts=['Description of Checkbox1',
                                    'Description of Checkbox2',
                                    'Description of Checkbox3']
                 ):

        Caller.caller = self.__class__.__name__
        super().__init__(
            title=title, header=MESSAGE_TEXT['CHECKBOX'],
            button1_text=button1_text,
            button2_text=button2_text, button3_text=button3_text,
            checkbutton_texts=checkbutton_texts
        )

    def button_1_button2(self, event):

        self.button_state = self._button2_text
        self.field_list = []
        for idx, check_var in enumerate(self._check_vars):
            if check_var.get() == 1:
                self.field_list.append(self.checkbutton_texts[idx])
        self.quit_widget()

    def button_1_button3(self, event):

        self.button_state = self._button3_text
        self.field_list = []
        for idx, check_var in enumerate(self._check_vars):
            if check_var.get() == 1:
                self.field_list.append(self.checkbutton_texts[idx])
        self.quit_widget()


class PrintList(BuiltText):
    """
    TOP-LEVEL-WINDOW        TextBox with ScrollBars (Only Output)

    PARAMETER:
        header              Header Line (Column Desscription)
        text                String of Text Lines
    """

    def set_tags(self, textline, line):
        if not line % 2:
            self.text_widget.tag_add(LIGHTBLUE, str(line + 1) + '.0',
                                     str(line + 1) + '.' + str(len(textline)))
            self.text_widget.tag_config(LIGHTBLUE, background='LIGHTBLUE')


class PandasBoxHolding(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Shows Dataframe of Holdings

    PARAMETER:
        dataframe           DataFrame object
        name                Name of Data Rows of PandasTable (e.g. Pandas.>column<)
        root                >root=self< Caller must define new_row(), cHange_row(), delete_row() methods
    """

    def set_properties(self):

        self.dataframe = self.dataframe.drop(
            columns=[DB_amount_currency, DB_price_currency, DB_currency],
            axis=1, errors='ignore')
        self.pandas_table.updateModel(TableModel(self.dataframe))
        self.pandas_table.redraw()

    def create_dataframe(self):

        if isinstance(self.dataframe, tuple):
            (data, columns) = self.dataframe
            self.dataframe = DataFrame(data)[columns]
            if DB_total_amount in columns and DB_acquisition_amount in columns:
                self.dataframe[FN_PROFIT] = self.dataframe[DB_total_amount] - \
                    self.dataframe[DB_acquisition_amount]
        elif isinstance(self.dataframe, DataFrame):
            pass
        else:
            self.dataframe = DataFrame(self.dataframe)


class PandasBoxHoldingPercent(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Shows Holdings
                            Period Changes in Percent

    PARAMETER:
        dataframe           (data_to_date, data_from_date)
    """

    def _get_name(self, position_dict):

        return position_dict[DB_name]

    def create_dataframe(self):

        data_to_date, data_from_date = self.dataframe

        to_map_set = {*map(self._get_name, data_to_date)}
        from_map_set = {*map(self._get_name, data_from_date)}
        # purchase positions: insert to data_from_date
        inserts = to_map_set.difference(from_map_set)
        data_to_date_insert = [
            item for item in data_to_date if item[DB_name] in inserts]
        data_from_date = data_from_date + data_to_date_insert
        # sale position delete form data_from_date
        removes = from_map_set.difference(to_map_set)
        data_from_date = [
            item for item in data_from_date if item[DB_name] not in removes]

        data_to_date = sorted(data_to_date, key=lambda i: (i[DB_name]))
        data_from_date = sorted(data_from_date, key=lambda i: (i[DB_name]))
        # create dataframe
        self.dataframe = DataFrame(data_to_date)
        dataframe_from_date = DataFrame(data_from_date)
        columns = [DB_total_amount, DB_acquisition_amount,
                   DB_pieces, DB_market_price]
        self.dataframe[columns] = self.dataframe[columns].apply(to_numeric)
        dataframe_from_date[columns] = dataframe_from_date[columns].apply(
            to_numeric)
        # adjust sales and purchases
        if not dataframe_from_date[DB_pieces].equals(self.dataframe[DB_pieces]):
            dataframe_from_date[DB_total_amount] = (
                dataframe_from_date[DB_total_amount] * self.dataframe[DB_pieces] / dataframe_from_date[DB_pieces])
        # add sum row
        sum_row = {}
        sum_row[DB_total_amount] = self.dataframe[DB_total_amount].sum()
        sum_row[DB_acquisition_amount] = self.dataframe[DB_acquisition_amount].sum()
        sum_row[DB_amount_currency] = EURO
        self.dataframe.loc[len(self.dataframe.index)] = sum_row
        sum_row[DB_total_amount] = dataframe_from_date[DB_total_amount].sum()
        sum_row[DB_acquisition_amount] = dataframe_from_date[DB_acquisition_amount].sum()
        dataframe_from_date.loc[len(dataframe_from_date.index)] = sum_row

        # compute percentages
        self.dataframe[FN_PROFIT_LOSS] = self.dataframe[DB_total_amount] - \
            self.dataframe[DB_acquisition_amount]
        self.dataframe[FN_TOTAL_PERCENT] = (
            self.dataframe[FN_PROFIT_LOSS] / self.dataframe[DB_acquisition_amount] * 100)
        self.dataframe[FN_PERIOD_PERCENT] = (
            self.dataframe[DB_total_amount] /
            dataframe_from_date[DB_total_amount]
            * 100 - 100)
        self.dataframe = self.dataframe.drop(
            [FN_PROFIT_LOSS, DB_acquisition_amount], axis=1)
        self.dataframe = self.dataframe[[DB_name, DB_total_amount, DB_market_price, DB_pieces,
                                         FN_TOTAL_PERCENT, FN_PERIOD_PERCENT]]


class PandasBoxHoldingPortfolios(PandasBoxHolding):
    """
    TOP-LEVEL-WINDOW        Shows Totals of Portfolios
                            Changes (Daily/Total) in Percent

    PARAMETER:
        dataframe           data per price_date
    """

    def create_dataframe(self):

        # create dataframe
        set_option('display.float_format', lambda x: '%0.2f' % x)
        columns = [DB_price_date, DB_total_amount_portfolio,
                   DB_acquisition_amount]
        self.dataframe = DataFrame(self.dataframe, columns=columns[:3])
        self.dataframe[columns[1:]
                       ] = self.dataframe[columns[1:]].apply(to_numeric)
        # Drop first row
        # self.dataframe.drop(
        #    index=self.dataframe.index[0], axis=0,  inplace=True)
        self.dataframe[DB_price_date] = to_datetime(
            self.dataframe[DB_price_date]).dt.date
        self.dataframe.set_index(DB_price_date, inplace=True)
        # compute percentages
        self.dataframe[FN_PROFIT_LOSS] = (
            self.dataframe[DB_total_amount_portfolio] -
            self.dataframe[DB_acquisition_amount]
        )
        self.dataframe[FN_TOTAL_PERCENT] = (
            self.dataframe[FN_PROFIT_LOSS] /
            self.dataframe[DB_acquisition_amount]
            * 100)
        self.dataframe[DB_total_amount_portfolio]
        price_date = self.dataframe.first_valid_index()
        self.dataframe[FN_PERIOD_PERCENT] = (
            self.dataframe[DB_total_amount_portfolio] /
            self.dataframe.loc[price_date, DB_total_amount_portfolio]
            * 100 - 100)
        self.dataframe = self.dataframe.round(2)


class PandasBoxHoldingTransaction(PandasBoxHolding):
    """
    TOP-LEVEL-WINDOW        Shows Dataframe Transactions of Holdings

    PARAMETER:
        dataframe           DataFrame object
        name                Name of Data Rows of PandasTable (e.g. Pandas.>column<)
        root                >root=self< Caller must define new_row(), cHange_row(), delete_row() methods
    """

    def create_dataframe(self):

        if isinstance(self.dataframe, tuple):
            (data, columns) = self.dataframe
            self.dataframe = DataFrame(data)[columns]
        elif isinstance(self.dataframe, DataFrame):
            pass
        else:
            self.dataframe = DataFrame(self.dataframe)
        if DB_transaction_type in self.dataframe.columns and DB_posted_amount in self.dataframe.columns:
            deliveries = self.dataframe[DB_transaction_type] == TRANSACTION_DELIVERY
            self.dataframe[DB_posted_amount] = self.dataframe[DB_posted_amount].where(
                deliveries, -self.dataframe[DB_posted_amount])


class PandasBoxPrices(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Shows Prices

    PARAMETER:
        dataframe           data per price_date
    """

    def create_dataframe(self):

        (db_field, data, self.origin, sign) = self.dataframe
        if sign == PERCENT:
            dataframe = DataFrame(data)
            dataframe = dataframe.dropna(how='all', axis=1)
            self.dataframe = dataframe.pivot(
                index='price_date', columns='name', values=db_field)
            columns = self.dataframe.columns
            base_row = self.dataframe.head(1)
            for idx, column, in enumerate(columns):
                if base_row.iloc[0, idx] != 0:
                    self.dataframe[column] = (
                        self.dataframe[column] / dec2.convert(base_row.iloc[0, idx]) - 1) * 100
        else:
            dataframe = DataFrame(data)
            columns = [DB_name]
            self.dataframe = dataframe.pivot(
                index=DB_price_date, columns=columns, values=db_field)
            columns = list(self.dataframe)
            self.dataframe[columns[0]] = self.dataframe[columns[0]].apply(
                to_numeric)

    def set_column_format(self):

        for column in self.dataframe.columns:
            _, name_ = column
            if self.origin[name_] == ALPHA_VANTAGE:
                # AlphaVamtageColumns are aqua
                self.pandas_table.columncolors[column] = '#00FFFF'
            else:
                # Yahoo columns are violet
                self.pandas_table.columncolors[column] = '#EE82EE'
        BuiltPandasBox.set_column_format(self)


class PandasBoxIsinTable(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Isin Pandastable
                            Row Actions: Show, Delete, Update, New
    """

    def __init__(self, title, data, message, mode=EDIT_ROW, selected_row=0):

        Caller.caller = self.__class__.__name__
        self.title = title
        self.data = data
        self.mariadb = MariaDB()
        self.message = message
        self.selected_row = selected_row
        if data:
            self.isins_exist = True
            ToolbarSwitch.toolbar_switch = False
            super().__init__(title=title, dataframe=data,
                             message=message, mode=mode, selected_row=self.selected_row)
        else:
            self.isins_exist = False
            self.button_state = self.new_row()

    def create_dataframe(self):

        self.dataframe = DataFrame(data=self.data)

    def drop_currencies(self):

        pass

    def show_row(self):

        row_dict = self.get_selected_row()
        protected = TABLE_FIELDS[ISIN]
        isin = BuiltTableRowBox(ISIN, ISIN, row_dict,
                                protected=protected,
                                title=self.title,  button1_text=None, button2_text=None)
        self.button_state = isin.button_state
        if isin.button_state == WM_DELETE_WINDOW:
            return
        self.quit_widget()

    def del_row(self):

        row_dict = self.get_selected_row()
        if row_dict:
            protected = TABLE_FIELDS[ISIN]
            isin = BuiltTableRowBox(ISIN, ISIN, row_dict,
                                    protected=protected,
                                    title=self.title, button1_text=BUTTON_DELETE, button2_text=None)
            self.button_state = isin.button_state
            if isin.button_state == WM_DELETE_WINDOW:
                return
            elif isin.button_state == BUTTON_DELETE:
                self.mariadb.execute_delete(
                    ISIN, isin_code=isin.field_dict[DB_ISIN])
                self.message = MESSAGE_TEXT['DATA_DELETED'].format(
                    ' '.join([self.title, '\n', DB_ISIN.upper(), isin.field_dict[DB_ISIN], '\n', isin.field_dict[DB_name]]))
        self.quit_widget()

    def update_row(self):

        row_dict = self.get_selected_row()
        if row_dict:
            if row_dict[DB_type] == FN_INDEX:
                protected = [DB_ISIN, DB_wkn, DB_industry]
            else:
                protected = [DB_ISIN]
            mandatory = [DB_name, DB_type, DB_validity, DB_currency]
            focus_out = [DB_ISIN, DB_name, DB_type, DB_origin_symbol]
            upper = [DB_symbol]
            if row_dict[DB_symbol] == NOT_ASSIGNED:
                button3_text = None
            else:
                button3_text = BUTTON_PRICES_IMPORT  # symbol mandatory for import of prices
            isin = IsinTableRowBox(
                ISIN, ISIN, row_dict,
                combo_dict=self._create_combo_dict(), combo_insert_value=[DB_industry],
                protected=protected, mandatory=mandatory,
                focus_out=focus_out, upper=upper,
                title=self.title, button1_text=BUTTON_UPDATE,
                button3_text=button3_text)
            self.button_state = isin.button_state
            if isin.button_state == WM_DELETE_WINDOW:
                return
            elif isin.button_state == BUTTON_UPDATE:
                self.mariadb.execute_replace(ISIN, isin.field_dict)
                self.message = MESSAGE_TEXT['DATA_CHANGED'].format(
                    ' '.join([self.title, DB_ISIN.upper(), isin.field_dict[DB_ISIN], isin.field_dict[DB_name]]))
            elif isin.button_state == BUTTON_PRICES_IMPORT:
                self.selected_row_dict = isin.field_dict
        self.quit_widget()

    def new_row(self):

        mandatory = [DB_ISIN, DB_name, DB_type, DB_validity, DB_currency]
        focus_out = [DB_ISIN, DB_name, DB_type, DB_origin_symbol]
        upper = [DB_symbol]
        row_dict = {}
        row_dict[DB_type] = FN_SHARE
        row_dict[DB_validity] = VALIDITY_DEFAULT
        row_dict[DB_wkn] = NOT_ASSIGNED
        row_dict[DB_origin_symbol] = NOT_ASSIGNED
        row_dict[DB_symbol] = NOT_ASSIGNED
        row_dict[DB_currency] = EURO
        isin = IsinTableRowBox(ISIN, ISIN, row_dict,
                               combo_dict=self._create_combo_dict(), mandatory=mandatory,
                               combo_insert_value=[DB_industry],
                               focus_out=focus_out, upper=upper,
                               title=self.title, button1_text=BUTTON_NEW)
        self.button_state = isin.button_state
        if isin.button_state == WM_DELETE_WINDOW:
            return isin.button_state
        elif isin.button_state == BUTTON_NEW:
            if self.mariadb.row_exists(ISIN, isin_code=isin.field_dict[DB_ISIN]):
                self.message = MESSAGE_TEXT['DATA_ROW_EXIST'].format(
                    ' '.join([ISIN.upper(), '\n', DB_ISIN.upper(), isin.field_dict[DB_ISIN]]))
            elif self.mariadb.row_exists(ISIN, name=isin.field_dict[DB_name]):
                self.message = MESSAGE_TEXT['DATA_ROW_EXIST'].format(
                    ' '.join([ISIN.upper(), '\n',  DB_name.upper(), isin.field_dict[DB_name]]))
            else:
                self.mariadb.execute_insert(ISIN, isin.field_dict)
                self.message = MESSAGE_TEXT['DATA_INSERTED'].format(
                    ' '.join([self.title, DB_ISIN.upper(), '\n', isin.field_dict[DB_ISIN], isin.field_dict[DB_name]]))
        if self.isins_exist:
            self.quit_widget()  # see BuiltPandasBox
        else:
            isin.quit_widget()  # see BuiltTableRowBox

    def _create_combo_dict(self):

        currency_dict = {DB_currency: CURRENCIES}
        type_dict = {DB_type: DB_TYPES}
        origin_symbol_dict = {DB_origin_symbol: ORIGIN_SYMBOLS}
        result = self.mariadb.select_table_distinct(ISIN, DB_industry)
        if result:
            industry_list = sorted([item[0] for item in result])
        else:
            industry_list = []
        industry_dict = {DB_industry: industry_list}
        return {**currency_dict, **type_dict, **origin_symbol_dict, **industry_dict}


class PandasBoxIsinComparision(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Shows market_prices, total_amounts, pieces, profit_loss of compared isin_codes
    PARAMETER:
        dataframe           data per price_date
    """

    def create_dataframe(self):

        (db_field, data) = self.dataframe
        dataframe = DataFrame(data)
        dataframe = dataframe.dropna(how='all', axis=1)
        self.dataframe = dataframe.pivot(
            index='price_date', columns='name', values=db_field)


class PandasBoxIsinComparisionPercent(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Shows market_prices, total_amounts, pieces, profit_loss of compared isin_codes
                            Shows data of isin_codes with their the maximum common time interval
    PARAMETER:
        dataframe           data per price_date
    """

    def create_dataframe(self):

        (db_field, data) = self.dataframe
        dataframe = DataFrame(data)
        dataframe = dataframe.dropna(how='all', axis=1)
        self.dataframe = dataframe.pivot(
            index='price_date', columns='name', values=db_field)
        self.dataframe = self.dataframe.dropna(how='all', axis=1)
        columns = self.dataframe.columns
        base_row = self.dataframe.head(1)
        for idx, column, in enumerate(columns):
            if base_row.iloc[0, idx] != 0:
                self.dataframe[column] = (
                    self.dataframe[column] / base_row.iloc[0, idx] - 1) * 100


class PandasBoxStatementBalances(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Shows Dataframe of Statements

    PARAMETER:
        dataframe           DataFrame object
        name                Name of Data Rows of PandasTable (e.g. Pandas.>column<)
        root                >root=self< Caller must define new_row(), cHange_row(), delete_row() methods
    """

    def _debit(self, amount, status=CREDIT, places=2):

        self.amount = str(amount)
        self.status = status
        m = re.match(r'(?<![.,])[-]{0,1}\d+[,.]{0,1}\d*', self.amount)
        if m:
            if m.group(0) == self.amount:
                self.amount = Calculate(places=places).convert(
                    self.amount.replace(',', '.'))
                if self.status == DEBIT or self.status == CreditDebit2.DEBIT:
                    self.amount = -self.amount
        return self.amount

    def create_dataframe(self):

        if isinstance(self.dataframe, tuple):
            data, columns = self.dataframe
            self.dataframe = DataFrame(data=data, columns=columns)
        names = self.dataframe.columns.tolist()
        if DB_amount in names:
            self.dataframe[DB_amount] = self.dataframe[[DB_amount, DB_status]].apply(
                lambda x: self._debit(*x), axis=1)
        if DB_opening_balance in names:
            self.dataframe[DB_opening_balance] = self.dataframe[[DB_opening_balance, DB_opening_status]].apply(
                lambda x: self._debit(*x), axis=1)
        if DB_closing_balance in names:
            self.dataframe[DB_closing_balance] = self.dataframe[[DB_closing_balance, DB_closing_status]].apply(
                lambda x: self._debit(*x), axis=1)

    def set_properties(self):

        self.dataframe = self.dataframe.drop(
            axis=1, errors='ignore',
            columns=[DB_currency, DB_status, DB_opening_currency, DB_opening_status,
                     DB_closing_currency, DB_closing_status, DB_amount_currency, DB_price_currency
                     ]
        )
        self.pandas_table.updateModel(TableModel(self.dataframe))
        self.pandas_table.redraw()


class PandasBoxHoldingTable(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        HOLDING Pandastable
                            Row Actions: Show, Delete, Update, New
    """

    def __init__(self, title, data, message, iban, mode=EDIT_ROW):

        Caller.caller = self.__class__.__name__
        self.title = title
        self.data = data
        self.mariadb = MariaDB()
        self.message = message
        if data:
            ToolbarSwitch.toolbar_switch = False
            super().__init__(title=title, dataframe=data, message=message, mode=mode)
        else:
            holding = self.new_row_insert({DB_iban: iban})
            self.button_state = holding.button_state

    def create_dataframe(self):

        self.dataframe = DataFrame(data=self.data)

    def drop_currencies(self):

        pass

    def show_row(self):

        row_dict = self.get_selected_row()
        protected = TABLE_FIELDS[HOLDING_VIEW]
        holding = BuiltTableRowBox(HOLDING, HOLDING_VIEW, row_dict,
                                   protected=protected,
                                   title=self.title,  button1_text=None, button2_text=None)
        self.button_state = holding.button_state
        if holding.button_state == WM_DELETE_WINDOW:
            return
        self.quit_widget()

    def del_row(self):

        row_dict = self.get_selected_row()
        if row_dict:
            protected = TABLE_FIELDS[HOLDING_VIEW]
            holding = BuiltTableRowBox(HOLDING, HOLDING_VIEW, row_dict,
                                       protected=protected,
                                       title=self.title, button1_text=BUTTON_DELETE, button2_text=None)
            self.button_state = holding.button_state
            if holding.button_state == WM_DELETE_WINDOW:
                return
            elif holding.button_state == BUTTON_DELETE:
                self.mariadb.execute_delete(
                    HOLDING, iban=holding.field_dict[DB_iban], isin_code=holding.field_dict[DB_ISIN], price_date=holding.field_dict[DB_price_date])
                self.message = MESSAGE_TEXT['DATA_DELETED'].format(
                    ' '.join([self.title, '\n', DB_price_date.upper(), holding.field_dict[DB_price_date], '\n', DB_ISIN.upper(), holding.field_dict[DB_ISIN], '\n', holding.field_dict[DB_name]]))
        self.quit_widget()

    def update_row(self):

        row_dict = self.get_selected_row()
        if row_dict:
            holding_dict = self.mariadb.select_table(
                HOLDING_VIEW, '*', result_dict=True, iban=row_dict[DB_iban], price_date=row_dict[DB_price_date], isin_code=row_dict[DB_ISIN],)[0]
            protected = TABLE_FIELDS[HOLDING_VIEW].copy()
            protected.remove(DB_market_price)
            protected.remove(DB_pieces)
            protected.remove(DB_acquisition_amount)
            protected.remove(DB_acquisition_price)
            mandatory = [DB_market_price, DB_pieces,
                         DB_acquisition_amount, DB_acquisition_price]
            holding = BuiltTableRowBox(HOLDING, HOLDING_VIEW, holding_dict,
                                       protected=protected, mandatory=mandatory,
                                       title=self.title, button1_text=BUTTON_UPDATE)
            self.button_state = holding.button_state
            if holding.button_state == WM_DELETE_WINDOW:
                return
            elif holding.button_state == BUTTON_UPDATE:
                if holding.field_dict[DB_market_price] != str(holding_dict[DB_market_price]) or holding.field_dict[DB_pieces] != str(holding_dict[DB_pieces]):
                    holding.field_dict[DB_total_amount] = dec2.multiply(
                        holding.field_dict[DB_market_price], holding.field_dict[DB_pieces])

                    holding.field_dict[DB_origin] = ORIGIN_BANKDATA_CHANGED
                if holding.field_dict[DB_acquisition_price] != str(holding_dict[DB_acquisition_price]) or holding.field_dict[DB_pieces] != str(holding_dict[DB_pieces]):
                    holding.field_dict[DB_acquisition_amount] = dec2.multiply(
                        holding.field_dict[DB_acquisition_price], holding.field_dict[DB_pieces])
                name = holding.field_dict[DB_name]
                del holding.field_dict[DB_name]
                del holding.field_dict[DB_symbol]
                self.mariadb.execute_replace(HOLDING, holding.field_dict)
                result = self.mariadb.select_holding_all_total(
                    iban=row_dict[DB_iban], price_date=row_dict[DB_price_date])
                if result:
                    field_dict = {DB_total_amount_portfolio: result[0][1]}
                    self.mariadb.execute_update(
                        HOLDING, field_dict, iban=row_dict[DB_iban], price_date=row_dict[DB_price_date])
                self.message = MESSAGE_TEXT['DATA_CHANGED'].format(
                    ' '.join([self.title, '\n', DB_price_date.upper(), holding.field_dict[DB_price_date], '\n', DB_ISIN.upper(), holding.field_dict[DB_ISIN], name]))
        self.quit_widget()

    def new_row(self):

        row_dict = self.get_selected_row()
        self.new_row_insert(row_dict)
        self.quit_widget()

    def new_row_insert(self, row_dict):

        combo_dict,  combo_positioning_dict, protected, mandatory = self.new_row_properties()
        holding = BuiltTableRowBox(HOLDING, HOLDING_VIEW, row_dict,
                                   combo_dict=combo_dict, combo_positioning_dict=combo_positioning_dict, protected=protected, mandatory=mandatory,
                                   title=self.title, button1_text=BUTTON_NEW)
        self.button_state = holding.button_state
        if holding.button_state == WM_DELETE_WINDOW:
            return holding
        elif holding.button_state == BUTTON_NEW:
            name = holding.field_dict[DB_name]
            if self.mariadb.row_exists(HOLDING, iban=holding.field_dict[DB_iban], isin_code=holding.field_dict[DB_ISIN], price_date=holding.field_dict[DB_price_date]):
                self.message = MESSAGE_TEXT['DATA_ROW_EXIST'].format(
                    ' '.join([HOLDING.upper(), '\n', DB_price_date.upper(), holding.field_dict[DB_price_date], '\n', DB_ISIN.upper(), holding.field_dict[DB_ISIN], name]))
            else:
                holding.field_dict[DB_origin] = ORIGIN_INSERTED
                del holding.field_dict[DB_name]
                del holding.field_dict[DB_symbol]
                self.mariadb.execute_insert(HOLDING, holding.field_dict)
                self.message = MESSAGE_TEXT['DATA_INSERTED'].format(
                    ' '.join([self.title, '\n', DB_price_date.upper(), holding.field_dict[DB_price_date], '\n', DB_ISIN.upper(), holding.field_dict[DB_ISIN], name]))
        return holding

    def new_row_properties(self):

        protected = [DB_iban, DB_name, DB_symbol]
        price_currency_dict = {DB_price_currency: CURRENCIES}
        amount_currency_dict = {DB_amount_currency: CURRENCIES}
        exchange_currency_1_dict = {DB_exchange_currency_1: CURRENCIES}
        exchange_currency_2_dict = {DB_exchange_currency_2: CURRENCIES}
        origin_dict = self.create_combo_list(HOLDING, DB_origin)
        combo_dict = {**price_currency_dict, **amount_currency_dict, **
                      exchange_currency_1_dict, **exchange_currency_2_dict, **origin_dict}
        isin_code_dict = self.create_combo_list(ISIN, DB_ISIN, from_date=None)
        combo_positioning_dict = isin_code_dict
        mandatory = TABLE_FIELDS[HOLDING_VIEW].copy()
        mandatory.remove(DB_total_amount_portfolio)
        mandatory.remove(DB_exchange_rate)
        mandatory.remove(DB_exchange_currency_2)
        mandatory.remove(DB_exchange_currency_1)
        mandatory.remove(DB_name)
        return combo_dict,  combo_positioning_dict, protected, mandatory


class PandasBoxLedgerAccountCategory(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Ledger Pandastable
    """

    def create_dataframe(self):

        account = self.title.split()[3]
        dataframe = DataFrame(data=self.dataframe)
        dataframe[DB_amount] = dataframe.apply(
            lambda row: row[DB_amount] if row[DB_credit_account] == account else -row[DB_amount], axis=1)
        # total sum
        total_sum = dataframe[DB_amount].sum()

        # Sort by 'Category'
        dataframe = dataframe.sort_values(by=[DB_category, DB_entry_date])

        # Group by 'Category' and append sum rows
        result = DataFrame()
        for group, group_df in dataframe.groupby(DB_category):
            group_df = group_df.copy()
            group_df.loc[FN_TOTAL] = {
                DB_id_no: FN_TOTAL,  DB_entry_date: group, DB_amount: group_df[DB_amount].sum()}
            result = concat(
                [result, group_df], ignore_index=True)
        result.loc[FN_TOTAL] = {
            DB_entry_date: FN_TOTAL, DB_amount: total_sum}
        self.dataframe = result

    def set_row_format(self):

        for i, row in self.pandas_table.model.df.iterrows():
            if row[DB_id_no] == FN_TOTAL:
                self.pandas_table.setRowColors(
                    rows=[i], clr='lightblue', cols='all')


class PandasBoxLedgerTable(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Ledger Pandastable
                            Row Actions: Show, Delete, Update, New
    """

    def __init__(self, title, data, message, mode=EDIT_ROW, color_columns_dict={}, period=None, selected_row=0):

        Caller.caller = self.__class__.__name__
        self.button_state = ''
        self.title = title
        self.data = data
        self.period = period
        self.mariadb = MariaDB()
        self.selected_row = selected_row
        result = MariaDB().select_ledger_statement_missed(self.period)
        if result:
            self.credit_statement_missed, self.debit_statement_missed = result
        else:
            self.credit_statement_missed = self.debit_statement_missed = []
        self.message = message
        if data:
            super().__init__(title=title, dataframe=data, message=message,
                             mode=mode, selected_row=self.selected_row)
        else:
            self.new_row_insert({})

    def create_dataframe(self):

        self.dataframe = DataFrame(data=self.data)

    def dataframe_append_sum(self):
        """
        Append Sum Row for column amount for Menu Ledger > Account
        """
        if (self.title.startswith(' '.join([MENU_TEXT['Ledger'], MENU_TEXT['Account']]))
                and DB_credit_account in self.dataframe.columns
                and DB_debit_account in self.dataframe.columns):
            start_account_name = len(
                ' '.join([MENU_TEXT['Ledger'], MENU_TEXT['Account']])) + 2
            account = self.title[start_account_name:start_account_name+4]
            self.dataframe[DB_amount] = self.dataframe.apply(
                lambda row: row[DB_amount] if row[DB_credit_account] == account else -row[DB_amount], axis=1)
            self.dataframe.loc[len(self.dataframe.index)] = {
                DB_id_no: '',
                DB_amount: self.dataframe[DB_amount].sum()}

    def color_columns(self, column):

        if column == DB_category:
            self.pandas_table.setColorByMask(
                DB_category, self.dataframe[DB_category] == NOT_ASSIGNED, COLOR_NOT_ASSIGNED)
        if column == DB_debit_account:
            self.pandas_table.setColorByMask(
                DB_debit_account, self.dataframe[DB_debit_account] == NOT_ASSIGNED, COLOR_ERROR)
        if column == DB_credit_account:
            mask = self.dataframe[DB_id_no].apply(
                lambda x: True if x in self.credit_statement_missed else False)
            self.pandas_table.setColorByMask(
                DB_credit_account, mask, COLOR_ERROR)
        if column == DB_debit_account:
            mask = self.dataframe[DB_id_no].apply(
                lambda x: True if x in self.debit_statement_missed else False)
            self.pandas_table.setColorByMask(
                DB_debit_account, mask, COLOR_ERROR)

    def _ledger_statement_missed(self, id_no, status=DEBIT):
        """
        Determines the bank accounts in the ledger table
        that have no assignment to a bank transaction
        """
        highlight_list = MariaDB().select_ledger_statement_missed(status, self.period)
        if id_no in highlight_list:
            return True
        else:
            return False

    def show_row(self):

        row_dict = self.get_selected_row()
        protected = TABLE_FIELDS[LEDGER_VIEW]
        ledger = LedgerTableRowBox(LEDGER, LEDGER_VIEW, row_dict,
                                   protected=protected,
                                   title=self.title,  button1_text=None, button2_text=None)
        self.message = ''
        if ledger.button_state == WM_DELETE_WINDOW:
            return
        self.quit_widget()

    def show_data(self, title, status):

        row_dict = self.get_selected_row()
        self.message = ''
        if row_dict:
            protected = TABLE_FIELDS[STATEMENT]
            result = self.mariadb.select_table(
                LEDGER_STATEMENT, '*', result_dict=True, id_no=row_dict[DB_id_no], status=status)
            if result:
                ledger_statement = result[0]
                result = self.mariadb.select_table(STATEMENT, '*', order=None, result_dict=True, date_name=None,
                                                   iban=ledger_statement[DB_iban], entry_date=ledger_statement[DB_entry_date], counter=ledger_statement[DB_counter])
                if result:
                    BuiltTableRowBox(STATEMENT, STATEMENT, result[0],
                                     protected=protected,
                                     title=title,  button1_text=None, button2_text=None)
                    self.message = ''
                else:
                    self.mariadb.exceute_delete(
                        LEDGER_STATEMENT, id_no=row_dict[DB_id_no], status=status)
                    self.message = MESSAGE_TEXT['LEDGER_ROW']
            else:
                self.message = MESSAGE_TEXT['LEDGER_ROW']
        self.quit_widget()

    def show_credit_data(self):

        title = ' '.join([self.title, POPUP_MENU_TEXT['Show credit data']])
        self.show_data(title, CREDIT)

    def show_debit_data(self):

        title = ' '.join([self.title, POPUP_MENU_TEXT['Show debit data']])
        self.show_data(title, DEBIT)

    def del_row(self):

        row_dict = self.get_selected_row()
        self.message = ''
        if row_dict:
            protected = TABLE_FIELDS[LEDGER_VIEW]
            ledger = LedgerTableRowBox(LEDGER, LEDGER_VIEW, row_dict,
                                       protected=protected,
                                       title=self.title, button1_text=BUTTON_DELETE, button2_text=None)
            if ledger.button_state == WM_DELETE_WINDOW:
                return
            elif ledger.button_state == BUTTON_DELETE:
                for field_name in TABLE_FIELDS[LEDGER_DELETE]:
                    if not ledger.field_dict[field_name]:
                        del ledger.field_dict[field_name]
                del ledger.field_dict[DB_credit_name]
                del ledger.field_dict[DB_debit_name]
                ledger.field_dict[DB_amount] = ledger.field_dict[DB_amount].removeprefix("-")  # menu ledger>account shows -amounts
                self.mariadb.execute_insert(LEDGER_DELETE, ledger.field_dict)
                self.mariadb.execute_delete(
                    # deletes per foreign key connected row in LEDGER_STATEMENT
                    LEDGER, id_no=ledger.field_dict[DB_id_no])
                self.message = MESSAGE_TEXT['DATA_DELETED'].format(
                    ' '.join([DB_id_no.upper(), ledger.field_dict[DB_id_no]]))
        self.quit_widget()

    def update_row(self):

        row_dict = self.get_selected_row()
        self.message = ''
        if row_dict:
            row_dict = self.mariadb.select_table(
                LEDGER_VIEW, '*', result_dict=True, id_no=row_dict[DB_id_no])
            if row_dict:
                row_dict = row_dict[0]
            else:
                return
            combo_dict,  combo_insert_value, combo_positioning_dict, protected, mandatory = self.new_row_properties()
            if self.mariadb.row_exists(LEDGER_STATEMENT, id_no=row_dict[DB_id_no], status=CREDIT):
                button3_text = BUTTON_CREDIT
            else:
                button3_text = None
            if self.mariadb.row_exists(LEDGER_STATEMENT, id_no=row_dict[DB_id_no], status=DEBIT):
                button4_text = BUTTON_DEBIT
            else:
                button4_text = None
            ledger = LedgerTableRowBox(LEDGER, LEDGER_VIEW, row_dict,
                                       protected=protected, mandatory=mandatory, combo_insert_value=combo_insert_value, combo_dict=combo_dict, combo_positioning_dict=combo_positioning_dict,
                                       title=self.title, button1_text=BUTTON_UPDATE, button3_text=button3_text, button4_text=button4_text)
            if ledger.button_state == WM_DELETE_WINDOW:
                return
            elif ledger.button_state == BUTTON_UPDATE:
                for field_name in protected:
                    if field_name != DB_id_no:
                        del ledger.field_dict[field_name]
                self.mariadb.execute_update(
                    LEDGER, ledger.field_dict, id_no=ledger.field_dict[DB_id_no])
                # Update LEDGER_STATEMENT connection
                self._update_ledger_statement(
                    CREDIT, ledger.field_dict, row_dict)
                self._update_ledger_statement(
                    DEBIT, ledger.field_dict, row_dict)
                # Special for LEDGER Check Upload
                if self.title.startswith(' '.join([MENU_TEXT['Ledger'], MENU_TEXT['Check Upload']])):
                    clause_upload_check = ' '.join(
                        [DB_id_no, "<=", ledger.field_dict[DB_id_no], "AND NOT", DB_upload_check])
                    self.mariadb.execute_update(
                        LEDGER, {DB_upload_check: 1}, clause=clause_upload_check)
                # Special for LEDGER Check Bank Statement
                if self.title.startswith(' '.join([MENU_TEXT['Ledger'], MENU_TEXT['Check Bank Statement']])):
                    self.mariadb.execute_update(
                        LEDGER, {DB_bank_statement_checked: 1}, id_no=ledger.field_dict[DB_id_no])
                self.message = MESSAGE_TEXT['DATA_CHANGED'].format(
                    ' '.join([DB_id_no.upper(), ledger.field_dict[DB_id_no]]))
        self.quit_widget()

    def _update_ledger_statement(self, status, ledger_dict, row_dict):
        """
        Connect ledger row to credit or debit statement row
        """

        if status == CREDIT:
            ledger_account = ledger_dict[DB_credit_account]
            row_account = row_dict[DB_credit_account]
        else:
            ledger_account = ledger_dict[DB_debit_account]
            row_account = row_dict[DB_debit_account]
        if row_account != ledger_account:
            # disconnect old ledger statement credit/debit connection
            if self.mariadb.row_exists(LEDGER_STATEMENT, id_no=ledger_dict[DB_id_no], status=status):
                self.mariadb.execute_delete(
                    LEDGER_STATEMENT, id_no=ledger_dict[DB_id_no])
        ledger_coa = self.mariadb.select_table(
            LEDGER_COA, '*', result_dict=True, account=ledger_account)
        if not (ledger_coa and ledger_coa[0][DB_iban] != NOT_ASSIGNED and not ledger_coa[0][DB_portfolio]):
            # its not a bank statement account
            return
        if row_account != ledger_account:
            # its a bank account, show selection of statements to assign
            PandasBoxLedgerStatement(
                self.title, ledger_coa[0][DB_iban], status, ledger_dict)
        elif not self.mariadb.row_exists(LEDGER_STATEMENT, id_no=ledger_dict[DB_id_no], status=status):
            # account not changed, its a bank account, but ledger statement connection not yet done
            PandasBoxLedgerStatement(
                self.title, ledger_coa[0][DB_iban], status, ledger_dict)

    def new_row(self):

        row_dict = self.get_selected_row()
        if row_dict:
            self.new_row_insert(row_dict)
        self.quit_widget()

    def new_row_insert(self, row_dict):

        combo_dict, combo_insert_value, combo_positioning_dict, protected, mandatory = self.new_row_properties()
        # create ledger
        ledger_dict = {DB_currency: EURO}
        while True:
            ledger = LedgerTableRowBox(LEDGER, LEDGER_VIEW, ledger_dict,
                                       protected=protected, mandatory=mandatory, combo_insert_value=combo_insert_value,
                                       combo_dict=combo_dict, combo_positioning_dict=combo_positioning_dict,
                                       title=self.title, button1_text=BUTTON_NEW, button2_text=BUTTON_COPY)
            if ledger.button_state == BUTTON_COPY:
                ledger_dict = row_dict
                ledger_dict[DB_currency] = EURO
                del ledger_dict[DB_id_no]
            else:
                break
        if ledger.button_state == WM_DELETE_WINDOW:
            return ledger
        elif ledger.button_state == BUTTON_NEW:
            for field_name in protected:
                if field_name != DB_id_no:
                    del ledger.field_dict[field_name]
            ledger.field_dict[DB_origin] = ORIGIN_LEDGER
            if DB_entry_date in ledger.field_dict:
                _year = date_days.convert(
                    ledger.field_dict[DB_entry_date]).year
                from_id_no = _year * 1000000
                to_id_no = (_year + 1) * 1000000
                clause = ' '.join(
                    [DB_id_no, ">", str(from_id_no), 'AND', DB_id_no, "<", str(to_id_no)])
                max_id_no = self.mariadb.select_max_column_value(
                    LEDGER, DB_id_no, clause=clause)
                if max_id_no:
                    id_no = max_id_no + 1
                else:
                    id_no = from_id_no + 1
                ledger.field_dict[DB_id_no] = id_no
                self.mariadb.execute_insert(LEDGER, ledger.field_dict)
                self.message = MESSAGE_TEXT['DATA_INSERTED'].format(
                    ' '.join([LEDGER.upper(), '\n', DB_id_no.upper(), str(id_no)]))
            else:
                self.message = MESSAGE_TEXT['ENTRY_DATE']
        return ledger

    def new_row_properties(self):

        protected = [DB_id_no, DB_date, DB_debit_name, DB_credit_name]
        mandatory = [DB_entry_date, DB_credit_account,
                     DB_debit_account, DB_amount, DB_currency, DB_purpose_wo_identifier]
        # get allowed accounts
        accounts_list = []
        accounts = self.mariadb.select_table(
            LEDGER_COA, [DB_account, DB_name], order=DB_account)
        if accounts:
            for account_name in accounts:
                accounts_list.append(
                    ' '.join([account_name[0], account_name[1]]))
        # create combo_dict
        origin_dict = self.create_combo_list(
            LEDGER, DB_origin, date_name=DB_entry_date)
        if not origin_dict:
            origin_dict = ORIGINS
        category_dict = self.create_combo_list(
            LEDGER, DB_category, date_name=DB_entry_date)
        applicant_name_dict = self.create_combo_list(
            LEDGER, DB_applicant_name, date_name=DB_entry_date)
        combo_dict = {**origin_dict}
        combo_insert_value = [DB_category, DB_applicant_name]
        combo_positioning_dict = {**category_dict, **applicant_name_dict}
        combo_positioning_dict[DB_currency] = CURRENCIES
        combo_positioning_dict[DB_credit_account] = accounts_list
        combo_positioning_dict[DB_debit_account] = accounts_list
        return combo_dict,  combo_insert_value, combo_positioning_dict, protected, mandatory


class PandasBoxLedgerCoaTable(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        LedgerCoa Pandastable
                            Row Actions: Show, Delete, Update, New
    """
    NOT_USED = [DB_eur_accounting, DB_tax_on_input, DB_value_added_tax,
                DB_earnings, DB_spendings, DB_transfer_account, DB_transfer_rate]

    def __init__(self, title, data, message, mode=EDIT_ROW, selected_row=0):

        Caller.caller = self.__class__.__name__
        self.title = title
        self.data = data
        self.mariadb = MariaDB()
        self.message = message
        self.selected_row = selected_row
        if data:
            super().__init__(title=title, dataframe=data,
                             message=message, mode=mode, selected_row=self.selected_row)
        else:
            ledger_coa = self.new_row_insert({})
            self.button_state = ledger_coa.button_state

    def create_dataframe(self):

        self.dataframe = DataFrame(data=self.data)

    def show_row(self):

        row_dict = self.get_selected_row()
        protected = TABLE_FIELDS[LEDGER_COA]
        ledger_coa = LedgerCoaTableRowBox(LEDGER_COA, LEDGER_COA, row_dict,
                                          protected=protected,
                                          title=self.title,  button1_text=None, button2_text=None)
        self.button_state = ledger_coa.button_state
        if ledger_coa.button_state == WM_DELETE_WINDOW:
            return
        self.quit_widget()

    def del_row(self):

        row_dict = self.get_selected_row()
        if row_dict:
            protected = TABLE_FIELDS[LEDGER_COA]
            ledger_coa = LedgerCoaTableRowBox(LEDGER_COA, LEDGER_COA, row_dict,
                                              protected=protected,
                                              title=self.title, button1_text=BUTTON_DELETE, button2_text=None)
            self.button_state = ledger_coa.button_state
            if ledger_coa.button_state == WM_DELETE_WINDOW:
                return
            elif ledger_coa.button_state == BUTTON_DELETE:
                self.mariadb.execute_delete(
                    LEDGER_COA, account=ledger_coa.field_dict[DB_account])
                self.message = MESSAGE_TEXT['DATA_DELETED'].format(
                    ' '.join([self.title, '\n', DB_account.upper(), ledger_coa.field_dict[DB_account]]))
        self.quit_widget()

    def update_row(self):

        row_dict = self.get_selected_row()
        if row_dict:
            protected = [DB_account] + PandasBoxLedgerCoaTable.NOT_USED
            mandatory = [DB_name]
            ledger_coa = LedgerCoaTableRowBox(LEDGER_COA, LEDGER_COA, row_dict,
                                              protected=protected, mandatory=mandatory,
                                              title=self.title, button1_text=BUTTON_UPDATE)

            self.button_state = ledger_coa.button_state
            if ledger_coa.button_state == WM_DELETE_WINDOW:
                return
            elif ledger_coa.button_state == BUTTON_UPDATE:
                self.mariadb.execute_replace(LEDGER_COA, ledger_coa.field_dict)
                self.message = MESSAGE_TEXT['DATA_CHANGED'].format(
                    ' '.join([self.title, '\n', DB_account.upper(), ledger_coa.field_dict[DB_account]]))
        self.quit_widget()

    def new_row(self):

        row_dict = self.get_selected_row()
        self.new_row_insert(row_dict)
        self.quit_widget()

    def new_row_insert(self, row_dict):

        mandatory = [DB_account, DB_name]
        ledger_coa = LedgerCoaTableRowBox(LEDGER_COA, LEDGER_COA, row_dict,
                                          mandatory=mandatory, protected=PandasBoxLedgerCoaTable.NOT_USED,
                                          title=self.title, button1_text=BUTTON_NEW)
        self.button_state = ledger_coa.button_state
        if ledger_coa.button_state == WM_DELETE_WINDOW:
            return ledger_coa
        elif ledger_coa.button_state == BUTTON_NEW:
            if self.mariadb.row_exists(LEDGER_COA, iban=ledger_coa.field_dict[DB_account]):
                self.message = MESSAGE_TEXT['DATA_ROW_EXIST'].format(
                    ' '.join([LEDGER_COA.upper(), '\n', DB_account.upper(), ledger_coa.field_dict[DB_account]]))
            else:
                self.mariadb.execute_insert(LEDGER_COA, ledger_coa.field_dict)
                self.message = MESSAGE_TEXT['DATA_INSERTED'].format(
                    ' '.join([self.title, '\n', DB_account.upper(), ledger_coa.field_dict[DB_account]]))
        return ledger_coa


class PandasBoxLedgerStatement(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Shows selection of statements for allocation in the ledger
    """

    def __init__(self, title, iban, status, ledger_dict):

        Caller.caller = self.__class__.__name__
        self.title = title
        self.status = status
        self.iban = iban
        self.ledger_dict = ledger_dict
        if status == CREDIT:
            # Credit always 2nd account transaction (after debit) , therefore 5 days back
            self.from_date = date_days.convert(self.ledger_dict[DB_entry_date])
            self.to_date = date_days.convert(
                date_days.add(self.ledger_dict[DB_entry_date], 5))
        if status == DEBIT:
            # Debit always 1st account transaction (before credit), therefore 5 days in advance
            self.to_date = date_days.convert(self.ledger_dict[DB_entry_date])
            self.from_date = date_days.convert(
                date_days.subtract(self.ledger_dict[DB_entry_date], 5))
        title = ' '.join([self.title, MESSAGE_TEXT['ASSINGNABLE_STATEMENTS'].format(
            self.from_date, self.to_date)])
        super().__init__(title=title,
                         message=MESSAGE_TEXT['SELECT_ROW'], mode=CURRENCY_SIGN)

    def create_dataframe(self):

        period = (self.from_date, self.to_date)
        statement_list = self.mariadb.select_table(STATEMENT, '*',
                                                   result_dict=True, date_name=DB_entry_date, order=[DB_entry_date, DB_counter],
                                                   status=self.status,
                                                   iban=self.iban, period=period,
                                                   amount=self.ledger_dict[DB_amount])
        new_statement_list = []
        for statement_dict in statement_list:
            if not self.mariadb.row_exists(LEDGER_STATEMENT, iban=statement_dict[DB_iban], entry_date=statement_dict[DB_entry_date], counter=statement_dict[DB_counter]):
                new_statement_list.append(statement_dict)
        if new_statement_list:
            self.dataframe = DataFrame(new_statement_list)
        else:
            if self.status == CREDIT:
                MessageBoxInfo(MESSAGE_TEXT['LEDGER_STATEMENT_ASSIGMENT_EMPTY'].format(
                    self.ledger_dict[DB_id_no], self.ledger_dict[DB_credit_account]))
            else:
                MessageBoxInfo(MESSAGE_TEXT['LEDGER_STATEMENT_ASSIGMENT_EMPTY'].format(
                    self.ledger_dict[DB_id_no], self.ledger_dict[DB_debit_account]))
            self.abort = True
            destroy_widget(self.dataframe_window)

    def processing(self):

        statement_dict = self.get_selected_row()
        if statement_dict:
            ledger_statement_dict = {}
            ledger_statement_dict[DB_iban] = statement_dict[DB_iban]
            ledger_statement_dict[DB_entry_date] = statement_dict[DB_entry_date]
            ledger_statement_dict[DB_counter] = statement_dict[DB_counter]
            ledger_statement_dict[DB_status] = self.status
            ledger_statement_dict[DB_id_no] = self.ledger_dict[DB_id_no]
            self.mariadb.execute_insert(
                LEDGER_STATEMENT, ledger_statement_dict)
        self.quit_widget()


class PandasBoxStatementTable(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        TRANSACTION Pandastable
                            Row Actions: Show
    """

    def __init__(self, title, data, message, mode=EDIT_ROW):

        Caller.caller = self.__class__.__name__
        self.title = title
        self.data = data
        self.message = message
        super().__init__(title=title, dataframe=data,
                         message=message, mode=mode)

    def _debit(self, amount, status=CREDIT, places=2):

        self.amount = str(amount)
        self.status = status
        m = re.match(r'(?<![.,])[-]{0,1}\d+[,.]{0,1}\d*', self.amount)
        if m:
            if m.group(0) == self.amount:
                self.amount = Calculate(places=places).convert(
                    self.amount.replace(',', '.'))
                if self.status == DEBIT or self.status == CreditDebit2.DEBIT:
                    self.amount = -self.amount
        return self.amount

    def create_dataframe(self):

        self.dataframe = DataFrame(data=self.data)
        names = self.dataframe.columns.tolist()
        if DB_amount in names:
            self.dataframe[DB_amount] = self.dataframe[[DB_amount, DB_status]].apply(
                lambda x: self._debit(*x), axis=1)
        if DB_opening_balance in names:
            self.dataframe[DB_opening_balance] = self.dataframe[[DB_opening_balance, DB_opening_status]].apply(
                lambda x: self._debit(*x), axis=1)
        if DB_closing_balance in names:
            self.dataframe[DB_closing_balance] = self.dataframe[[DB_closing_balance, DB_closing_status]].apply(
                lambda x: self._debit(*x), axis=1)

    def set_properties(self):

        self.dataframe = self.dataframe.drop(
            axis=1, errors='ignore',
            columns=[DB_currency, DB_status, DB_opening_currency, DB_opening_status,
                     DB_closing_currency, DB_closing_status, DB_amount_currency, DB_price_currency
                     ]
        )
        self.pandas_table.updateModel(TableModel(self.dataframe))
        self.pandas_table.redraw()

    def show_row(self):

        row_dict = self.get_selected_row()
        if row_dict:
            row_dict = self.mariadb.select_table(STATEMENT, '*', order=None, result_dict=True,
                                                 date_name=None, iban=row_dict[DB_iban],
                                                 entry_date=row_dict[DB_entry_date],
                                                 counter=row_dict[DB_counter])
            if not row_dict:
                return
            statement = BuiltTableRowBox(
                STATEMENT, STATEMENT, row_dict[0], title=self.title,
                protected=TABLE_FIELDS[STATEMENT],
                button1_text=None, button2_text=None)
            self.button_state = statement.button_state
            if statement.button_state == WM_DELETE_WINDOW:
                return
        self.quit_widget()


class PandasBoxBalances(PandasBoxStatementBalances):
    """
    TOP-LEVEL-WINDOW        Shows Dataframe of Balances

    PARAMETER:
        dataframe           DataFrame object
    """

    def create_dataframe(self):

        PandasBoxStatementBalances.create_dataframe(self)
        self.dataframe.drop(KEY_ACC_BANK_CODE, inplace=True, axis=1)


class PandasBoxBalancesAllBanks(PandasBoxStatementBalances):
    """
    TOP-LEVEL-WINDOW        Shows Dataframe of Balances

    PARAMETER:
        dataframe           DataFrame object
    """

    def __init__(self, title, dataframe, mode, bank_names):

        Caller.caller = self.__class__.__name__
        self.bank_names = bank_names
        super().__init__(title=title, dataframe=dataframe, mode=mode)

    def create_dataframe(self):

        dataframe_all = concat(self.dataframe)
        max_entry_date = dataframe_all[DB_entry_date].max()
        # total sum all Banks
        self.dataframe_append_sum(
            dataframe_all, [DB_closing_balance, DB_opening_balance])
        dataframe_all[KEY_BANK_NAME] = FN_TOTAL
        dataframe_all[DB_entry_date] = max_entry_date
        # total sum of each bank
        dataframes = []
        for dataframe in self.dataframe:
            self.dataframe_append_sum(
                dataframe, [DB_closing_balance, DB_opening_balance])
            dataframe[DB_entry_date] = max_entry_date
            dataframe[KEY_BANK_NAME] = ''
            dataframe.at[len(
                dataframe)-1, KEY_BANK_NAME] = self.bank_names[dataframe.at[0, KEY_BANK_CODE]]
            dataframes.append(dataframe)
        # append total sum all Bank
        dataframes.append(dataframe_all.tail(1))
        self.dataframe = concat(dataframes, ignore_index=True)

        PandasBoxStatementBalances.create_dataframe(self)
        self.dataframe.reset_index()
        # calculate percent changes
        self.dataframe[FN_DAILY_PERCENT] = self.dataframe[[DB_closing_balance,
                                                           DB_opening_balance]].apply(lambda x: self._daily_percent(*x), axis=1)
        self.dataframe[DB_closing_balance] = self.dataframe[[DB_closing_balance, DB_closing_status]].apply(
            lambda x: self._debit(*x), axis=1)
        # if no changes set set percent = 0
        self.dataframe[FN_DAILY_PERCENT] = self.dataframe.apply(
            lambda row: 0 if max_entry_date > row[DB_entry_date] else row[FN_DAILY_PERCENT], axis=1)
        # format display

        self.dataframe = self.dataframe[[KEY_ACC_BANK_CODE, KEY_ACC_ACCOUNT_NUMBER,
                                         KEY_ACC_PRODUCT_NAME, DB_entry_date, DB_closing_balance,
                                         FN_DAILY_PERCENT, KEY_BANK_NAME]]
        bank_name = self.dataframe[KEY_BANK_NAME]
        self.dataframe.drop(
            [KEY_BANK_NAME, KEY_ACC_BANK_CODE, DB_entry_date], inplace=True, axis=1)
        self.dataframe.insert(0, KEY_BANK_NAME, bank_name)

    def _daily_percent(self, closing_balance, opening_balance):

        if opening_balance != 0:
            result = (closing_balance - opening_balance) / \
                opening_balance * 100
            result = dec2.convert(result)
            return result
        else:
            return 0

    def set_row_format(self):

        for i, row in self.pandas_table.model.df.iterrows():
            if row[KEY_BANK_NAME]:
                self.pandas_table.setRowColors(
                    rows=[i], clr='lightblue', cols='all')

    def _debit(self, amount, status=CREDIT, places=2):

        self.amount = str(amount)
        self.status = status
        m = re.match(r'(?<![.,])[-]{0,1}\d+[,.]{0,1}\d*', self.amount)
        if m:
            if m.group(0) == self.amount:
                self.amount = Calculate(places=places).convert(
                    self.amount.replace(',', '.'))
                if self.status == DEBIT or self.status == CreditDebit2.DEBIT:
                    self.amount = -self.amount
        return self.amount

    def create_dataframe_append_sum(self):
        """
        Append Sum Row for columns in self.dataframe_sum
        """
        self.dataframe = self.dataframe_append_sum(
            self.dataframe, self.dataframe_sum)

    def dataframe_append_sum(self, dataframe, dataframe_sum):
        """
        Append Sum Row for columns in dataframe_sum
        """
        sum_row = {}
        for column in dataframe_sum:
            dataframe[column] = dataframe[column].apply(
                lambda x: Amount(x).to_decimal())
            if column == DB_opening_balance:
                dataframe[column] = dataframe[[column, DB_opening_status]].apply(
                    lambda x: self._debit(*x), axis=1)
            elif column == DB_closing_balance:
                dataframe[column] = dataframe[[column, DB_closing_status]].apply(
                    lambda x: self._debit(*x), axis=1)
            if column in dataframe.columns:
                sum_row[column] = to_numeric(
                    dataframe[column]).sum()
                sum_row[column] = dec2.convert(sum_row[column])
        if sum_row != {}:
            sum_row[DB_price_currency] = EURO
            sum_row[DB_amount_currency] = EURO
            sum_row[DB_currency] = EURO
            dataframe.loc[len(dataframe.index)] = sum_row
        return dataframe


class PandasBoxTotals(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Shows Dataframe of Totals

    PARAMETER:
        data           data_total_amounts (list of tuple: (iban/account, entry_date, sum)
    """

    def __init__(self, title, data, portfolio=['DE81101308001002902112', 'DEXX504000000004414413']):

        Caller.caller = self.__class__.__name__
        self.title = title
        self.data = data
        self.portfolio = portfolio
        super().__init__(title=title, dataframe=data, mode=NUMERIC)

    def _debit(self, amount, status=CREDIT, places=2):

        if status == DEBIT:
            amount = amount * -1
        return amount

    def create_dataframe(self):

        self.dataframe = DataFrame(self.dataframe, columns=[
            DB_iban, DB_date, DB_status, DB_total_amount])
        self.dataframe[DB_total_amount] = self.dataframe[[DB_total_amount, DB_status]].apply(
            lambda x: self._debit(*x), axis=1)
        self.dataframe = self.dataframe.sort_values([DB_iban, DB_date])
        self.dataframe = self.dataframe.pivot_table(index=[DB_date], columns=[
            DB_iban], values=[DB_total_amount])
        self.ffill_dataframe()
        self.dataframe[FN_TOTAL] = self.dataframe.sum(
            axis=1).apply(lambda x: dec2.convert(x))
        self.dataframe = self.dataframe.iloc[1:]
        dict1 = self.mariadb.select_dict(LEDGER_COA, DB_iban, DB_name)
        dict2 = self.mariadb.select_dict(LEDGER_COA, DB_account, DB_name)
        self.dataframe.columns = [col[1] for col in self.dataframe.columns]  # column header with 2 levels
        self.dataframe = self.dataframe.rename(columns=lambda c: dict1.get(c, dict2.get(c, c)))

    def ffill_dataframe(self):
        '''
        ffill account columns
        '''
        columns = self.dataframe.columns.to_list()
        for column in columns:
            _, iban = column
            if iban in self.portfolio:
                # index of first not empty cell
                start_index = self.dataframe[column].first_valid_index()
                # index of last not empty cell
                end_index = self.dataframe[column].last_valid_index()
                self.dataframe.loc[start_index:end_index,
                                   column] = self.dataframe.loc[start_index:end_index, column].ffill()
            else:
                self.dataframe[column] = self.dataframe[column].ffill()


class PandasBoxTransactionProfit(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Shows Dataframe of Transactions

    PARAMETER:
        dataframe           List of tuples with transaction data
    """

    def create_dataframe(self):

        self.dataframe = DataFrame(
            self.dataframe,
            columns=[DB_ISIN, DB_name, FN_PROFIT, DB_amount_currency, DB_pieces])
        self.dataframe.drop(columns=[DB_pieces], inplace=True, axis=1)
        sum_row = {DB_ISIN: '',  DB_name: 'TOTAL: ',
                   FN_PROFIT: self.dataframe[FN_PROFIT].sum(), DB_amount_currency: EURO}
        self.dataframe.loc[len(self.dataframe.index)] = sum_row


class PandasBoxTransactionDetail(BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        Shows Dataframe of Transactions

    PARAMETER:
        dataframe           List of tuples with transaction data
    """

    def create_dataframe(self):

        self.count_transactions, data = self.dataframe
        self.dataframe = DataFrame(
            data,
            columns=[DB_price_date, DB_counter, DB_transaction_type,
                     DB_price, DB_pieces, DB_posted_amount])
        deliveries = self.dataframe[DB_transaction_type] == TRANSACTION_RECEIPT
        # Replace values where the condition is False.
        self.dataframe[DB_pieces] = self.dataframe[DB_pieces].where(deliveries, -self.dataframe[DB_pieces])
        self.dataframe[FN_PIECES_CUM] = self.dataframe[DB_pieces].cumsum()

        receipts = self.dataframe[DB_transaction_type] == TRANSACTION_DELIVERY
        self.dataframe[DB_posted_amount] = self.dataframe[DB_posted_amount].where(receipts, -self.dataframe[DB_posted_amount])
        self.dataframe[FN_PROFIT_CUM] = self.dataframe[DB_posted_amount].cumsum()
        closed_postion = self.dataframe[FN_PIECES_CUM] == 0
        self.dataframe[FN_PROFIT_CUM] = self.dataframe[FN_PROFIT_CUM].where(closed_postion, other=0)
        self.dataframe.drop(
            columns=[DB_counter], inplace=True)

    def set_row_format(self):

        if self.count_transactions < self.dataframe.shape[0]:
            self.pandas_table.setRowColors(
                self.count_transactions, COLOR_HOLDING, 'all')


class PandasBoxTransactionTableShow (BuiltPandasBox):
    """
    TOP-LEVEL-WINDOW        TRANSACTION Pandastable
                            Row Actions: Show
    """

    def __init__(self, title, data, message, iban, isin='', isin_name='', mode=EDIT_ROW):

        Caller.caller = self.__class__.__name__
        self.title = title
        self.data = data
        self.mariadb = MariaDB()
        self.message = message
        if data:
            super().__init__(title=title, dataframe=data, message=message, mode=mode)
        else:
            transaction = self.new_row_insert(
                {DB_iban: iban, DB_ISIN: isin, DB_name: isin_name})
            self.button_state = transaction.button_state

    def create_dataframe(self):

        self.dataframe = DataFrame(data=self.data)

    def show_row(self):

        row_dict = self.get_selected_row()
        protected = TABLE_FIELDS[TRANSACTION_VIEW]
        transaction = BuiltTableRowBox(
            TRANSACTION, TRANSACTION_VIEW, row_dict, title=self.title,
            protected=protected,
            button1_text=None, button2_text=None)
        self.button_state = transaction.button_state
        if transaction.button_state == WM_DELETE_WINDOW:
            return
        self.quit_widget()


class PandasBoxTransactionTable(PandasBoxTransactionTableShow):
    """
    TOP-LEVEL-WINDOW        TRANSACTION Pandastable
                            Row Actions: Show, Delete, Update, New
    """

    def del_row(self):

        row_dict = self.get_selected_row()
        if row_dict:
            protected = TABLE_FIELDS[TRANSACTION_VIEW]
            transaction = BuiltTableRowBox(
                TRANSACTION, TRANSACTION_VIEW, row_dict, title=self.title,  protected=protected,
                button1_text=BUTTON_DELETE, button2_text=None)
            self.button_state = transaction.button_state
            if transaction.button_state == WM_DELETE_WINDOW:
                return
            elif transaction.button_state == BUTTON_DELETE:
                self.mariadb.execute_delete(
                    TRANSACTION, iban=transaction.field_dict[DB_iban], isin_code=transaction.field_dict[DB_ISIN], price_date=transaction.field_dict[DB_price_date], counter=transaction.field_dict[DB_counter])
                self.message = MESSAGE_TEXT['DATA_DELETED'].format(
                    ' '.join([self.title, '\n', DB_price_date.upper(), transaction.field_dict[DB_price_date], '\n', DB_counter.upper(), transaction.field_dict[DB_counter]]))
        self.quit_widget()

    def update_row(self):

        row_dict = self.get_selected_row()
        if row_dict:
            row_dict = self.mariadb.select_table(
                TRANSACTION, '*', result_dict=True, iban=row_dict[DB_iban], price_date=row_dict[DB_price_date], isin_code=row_dict[DB_ISIN], counter=row_dict[DB_counter],)
            if row_dict:
                row_dict = row_dict[0]
            else:
                return
            protected = [DB_iban, DB_ISIN, DB_price_date, DB_counter, DB_name]
            mandatory = [DB_transaction_type, DB_price_currency,
                         DB_price, DB_pieces, DB_amount_currency]
            transaction_type_dict = {DB_transaction_type: TRANSACTION_TYPES}
            price_currency_dict = {DB_price_currency: CURRENCIES}
            amount_currency_dict = {DB_amount_currency: CURRENCIES}
            origin_dict = self.create_combo_list(TRANSACTION, DB_origin)
            combo_dict = origin_dict
            combo_positioning_dict = {**transaction_type_dict,
                                      **price_currency_dict, **amount_currency_dict}
            transaction = BuiltTableRowBox(TRANSACTION, TRANSACTION_VIEW, row_dict,
                                           protected=protected, mandatory=mandatory, combo_dict=combo_dict, combo_positioning_dict=combo_positioning_dict,
                                           title=self.title)
            self.button_state = transaction.button_state
            if transaction.button_state == WM_DELETE_WINDOW:
                return
            elif transaction.button_state == BUTTON_SAVE:
                del transaction.field_dict[DB_name]
                self.mariadb.execute_replace(
                    TRANSACTION, transaction.field_dict)
                self.message = MESSAGE_TEXT['DATA_CHANGED'].format(
                    ' '.join([self.title, '\n', DB_price_date.upper(), transaction.field_dict[DB_price_date], '\n', DB_counter.upper(), transaction.field_dict[DB_counter]]))
        self.quit_widget()

    def new_row(self):

        row_dict = self.get_selected_row()
        row_dict[DB_origin] = ''
        row_dict[DB_counter] = 0
        self.new_row_insert(row_dict)
        self.quit_widget()

    def new_row_insert(self, row_dict):

        combo_dict,  combo_positioning_dict, protected, mandatory = self.new_row_properties()
        row_dict[DB_price_currency] = EURO
        row_dict[DB_amount_currency] = EURO
        transaction = BuiltTableRowBox(TRANSACTION, TRANSACTION_VIEW, row_dict,
                                       combo_dict=combo_dict, combo_positioning_dict=combo_positioning_dict, protected=protected, mandatory=mandatory,
                                       title=self.title, button1_text=BUTTON_NEW)
        self.button_state = transaction.button_state
        if transaction.button_state == WM_DELETE_WINDOW:
            return transaction
        elif transaction.button_state == BUTTON_NEW:
            if self.mariadb.row_exists(TRANSACTION, iban=transaction.field_dict[DB_iban], isin_code=transaction.field_dict[DB_ISIN], price_date=transaction.field_dict[DB_price_date], counter=transaction.field_dict[DB_counter]):
                self.message = MESSAGE_TEXT['DATA_ROW_EXIST'].format(
                    ' '.join([TRANSACTION.upper(), '\n', DB_price_date.upper(), transaction.field_dict[DB_price_date], '\n', DB_ISIN.upper(), transaction.field_dict[DB_ISIN], '\n', DB_counter.upper(), transaction.field_dict[DB_counter]]))
            else:
                transaction.field_dict[DB_posted_amount] = dec2.multiply(
                    transaction.field_dict[DB_price], transaction.field_dict[DB_pieces])
                del transaction.field_dict[DB_name]
                self.mariadb.execute_insert(
                    TRANSACTION, transaction.field_dict)
                self.message = MESSAGE_TEXT['DATA_INSERTED'].format(
                    ' '.join([self.title, '\n', DB_price_date.upper(), transaction.field_dict[DB_price_date], '\n', DB_ISIN.upper(), transaction.field_dict[DB_ISIN], '\n', DB_counter.upper(), transaction.field_dict[DB_counter]]))
        return transaction

    def new_row_properties(self):

        protected = [DB_iban, DB_ISIN, DB_name]
        mandatory = [DB_ISIN, DB_price_date, DB_counter, DB_transaction_type, DB_price_currency,
                     DB_price, DB_pieces, DB_amount_currency]
        transaction_type_dict = {DB_transaction_type: TRANSACTION_TYPES}
        price_currency_dict = {DB_price_currency: CURRENCIES}
        amount_currency_dict = {DB_amount_currency: CURRENCIES}
        origin_dict = self.create_combo_list(TRANSACTION, DB_origin)
        combo_dict = origin_dict
        combo_positioning_dict = {**transaction_type_dict,
                                  **price_currency_dict, **amount_currency_dict}
        return combo_dict,  combo_positioning_dict, protected, mandatory


class TechnicalIndicator(InputISIN):
    """
    Paraameter
     selection_name --> Storage name for last used selection values
     data_dict --> default values of select_data
     data_container --> contains additional data from caller

    1. Volume Indicators
    2. Volatility Indicators
    3. Trend Indicators
    4. Momentum Indicators
    5. Other Indicators
    Details (see in declarations.py TechnicalIndicatorData)
    """

    TA_MENU_TEXT = {
        'Volume': 'Volume',
        'Volatility': 'Volatility',
        'Trend': 'Trend',
        'Momentum': 'Momentum',
        'Others': 'Others'
        }


    def __init__(self, title=MESSAGE_TITLE, data_dict={}, container_dict={}, selection_name=None):

        super().__init__(title=title, header=None, table=None,
                         button1_text=BUTTON_INDICATOR, button2_text=None,
                         button3_text=None, button4_text=None,
                         selection_name=selection_name,
                         data_dict=data_dict,
                         upper=[], separator=[],
                         container_dict=container_dict
                         )

    def comboboxselected_action(self, event):

        self._box_window_top.config(menu='')  # remove technical indicator  menu
        InputISIN.comboboxselected_action(self, event)

    def button_1_button1(self, event):

        self.button_state = self._button1_text
        self.validation()
        if not self.footer.get():
            # create ta ohlc dataframe
            
            symbol = self.container_dict[self.field_dict[DB_name]]
            import_prices_run(self.title, self.mariadb, [self.field_dict[DB_name]], BUTTON_APPEND)
            field_list = [DB_price_date, DB_open, DB_high, DB_low, DB_close, DB_volume]
            data = self.mariadb.select_table(
                PRICES, field_list, result_dict=True, order=DB_price_date, symbol=symbol,
                period=(self.field_dict[FN_FROM_DATE], self.field_dict[FN_TO_DATE]))
            if data:
                dataframe = self._convert_decimals_to_float(DataFrame(data))
                # extend to technical indicator dataframe
                dataframe = ta.utils.dropna(dataframe)
                dataframe = ta.add_all_ta_features(
                    dataframe,
                    open=DB_open,
                    high=DB_high,
                    low=DB_low,
                    close=DB_close,
                    volume=DB_volume,
                    fillna=True
                )
                dataframe = dataframe.set_index(dataframe.columns[0])
                self._set_menu(dataframe)
            else:
                self.footer.set(MESSAGE_TEXT["DATA_NO"].format(PRICES.upper(), self.data_dict[DB_name]))

    def quit_widget(self):

        self._geometry_put(self._box_window_top)
        destroy_widget(self._box_window_top)

    def _convert_decimals_to_float(self, df: DataFrame) -> DataFrame:
        for col in df.columns:
            # Check if the column contains at least one Decimal value
            if df[col].map(lambda x: isinstance(x, Decimal)).any():
                # Convert only Decimal values to float; leave all other values unchanged
                df[col] = df[col].map(lambda x: float(x) if isinstance(x, Decimal) else x)
        return df

    def _set_menu(self, dataframe):
        """
        create menu with technical indicators
        """
        try:
            menubar = Menu(self._box_window_top)
            volume_menu = Menu(menubar, tearoff=0)
            for indicator in TechnicalIndicatorData.TA_VOLUME.keys():
                volume_menu.add_command(
                    label=indicator,
                    command=lambda x=dataframe, y=TechnicalIndicatorData.TA_VOLUME[indicator], z=indicator: self._show_indicator(x, y, z))
            menubar.add_cascade(label=self.TA_MENU_TEXT['Volume'], menu=volume_menu)
            volatility_menu = Menu(menubar, tearoff=0)
            for indicator in TechnicalIndicatorData.TA_VOLATILITY.keys():
                volatility_menu.add_command(
                    label=indicator,
                    command=lambda x=dataframe, y=TechnicalIndicatorData.TA_VOLATILITY[indicator], z=indicator: self._show_indicator(x, y, z))
            menubar.add_cascade(label=self.TA_MENU_TEXT['Volatility'], menu=volatility_menu)
            trend_menu = Menu(menubar, tearoff=0)
            for indicator in TechnicalIndicatorData.TA_TREND.keys():
                trend_menu.add_command(
                    label=indicator,
                    command=lambda x=dataframe, y=TechnicalIndicatorData.TA_TREND[indicator], z=indicator: self._show_indicator(x, y, z))
            menubar.add_cascade(label=self.TA_MENU_TEXT['Trend'], menu=trend_menu)
            momentum_menu = Menu(menubar, tearoff=0)
            for indicator in TechnicalIndicatorData.TA_MOMENTUM.keys():
                momentum_menu.add_command(
                    label=indicator,
                    command=lambda x=dataframe, y=TechnicalIndicatorData.TA_MOMENTUM[indicator], z=indicator: self._show_indicator(x, y, z))
            menubar.add_cascade(label=self.TA_MENU_TEXT['Momentum'], menu=momentum_menu)
            others_menu = Menu(menubar, tearoff=0)
            for indicator in TechnicalIndicatorData.TA_OTHERS.keys():
                others_menu.add_command(
                    label=indicator,
                    command=lambda x=dataframe, y=TechnicalIndicatorData.TA_OTHERS[indicator], z=indicator: self._show_indicator(x, y, z))
            menubar.add_cascade(label=self.TA_MENU_TEXT['Others'], menu=others_menu)
            self._box_window_top.config(menu=menubar)
        except Exception as e:
            import traceback
            print("Error in menu command:", e)
            traceback.print_exc()

    def _show_indicator(self, dataframe, indicator_columns, indicator):

        title = ' '.join([indicator, self.field_dict[DB_name]])
        line_columns = []
        if indicator in TechnicalIndicatorData.TA_LINES.keys():
            for line_column in TechnicalIndicatorData.TA_LINES[indicator]:
                line_column_name, line_column_value = line_column
                dataframe[line_column_name] = line_column_value
                line_columns.append(line_column_name)
        TechnicalIndicatorData.TA_CLOSE = []
        BuiltPandasBox(title=title, dataframe=dataframe[indicator_columns + line_columns],
                       mode=NUMERIC, instant_plotting=True)
        if self.button_state == WM_DELETE_WINDOW:
            return
        BuiltPandasBox(title=title, dataframe=dataframe[indicator_columns + TechnicalIndicatorData.TA_CLOSE + line_columns],
                       mode=NUMERIC, instant_plotting=True)


class SelectCloseVolume(BuiltCheckButton):
    """
    TOP-LEVEL-WINDOW        Select additional charts

    Select addtional charts to technical indicator chart

    PARAMETER:
        checkbutton_texts    List  of Fields

        default_text         initialization of checkbox
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        self.field_list        contains selected check_fields
    """

    def __init__(self):

        Caller.caller = self.__class__.__name__
        super().__init__(
            title=MESSAGE_TEXT['TA_ADD_CHART'], header=MESSAGE_TEXT['CHECKBOX'],
            button1_text=BUTTON_ADD_CHART, button2_text=None,
            checkbutton_texts=[DB_close, DB_volume],
            default_texts=TechnicalIndicatorData.TA_CLOSE
        )

    def button_1_button2(self, event):

        self.button_state = self._button2_text
        self.field_list = []
        for idx, check_var in enumerate(self._check_vars):
            if check_var.get() == 1:
                self.field_list.append(self.checkbutton_texts[idx])
        self.quit_widget()

    def button_1_button3(self, event):

        self.button_state = self._button3_text
        self.field_list = []
        for idx, check_var in enumerate(self._check_vars):
            if check_var.get() == 1:
                self.field_list.append(self.checkbutton_texts[idx])
        self.quit_widget()


class PrintMessageCode(BuiltText):
    """
    TOP-LEVEL-WINDOW        TextBox with ScrollBars (Only Output)

    PARAMETER:
        header              Header Line (Column Description)
        text                String of Text Lines

    SHOWS Text Sheet if one of following text line qualifiers exist:

        INFORMATION = 'INFORMATION: '
        WARNING = 'WARNING:     '
        ERROR = 'ERROR:       '
    """

    def set_tags(self, textline, line):
        if len(textline) > 13:
            if textline[0:12] == ERROR:
                self.text_widget.tag_add(ERROR, str(line + 1) + '.0',
                                         str(line + 1) + '.' + str(len(textline)))
                self.text_widget.tag_config(ERROR, foreground='RED')
            elif textline[0:12] == WARNING:
                self.text_widget.tag_add(WARNING, str(line + 1) + '.0',
                                         str(line + 1) + '.' + str(len(textline)))
                self.text_widget.tag_config(WARNING, foreground='BLUE')
            elif textline[0:12] == INFORMATION:
                self.text_widget.tag_add(INFORMATION, str(line + 1) + '.0',
                                         str(line + 1) + '.' + str(len(textline)))
                self.text_widget.tag_config(INFORMATION, foreground='GREEN')

    def destroy_widget(self, text):

        info = re.compile(INFORMATION)
        if info.search(text):
            return False
        warn = re.compile(WARNING)
        if warn.search(text):
            return False
        err = re.compile(ERROR)
        if err.search(text):
            return False
        return True


class VersionTransaction(BuiltEnterBox):
    """
    TOP-LEVEL-WINDOW        EnterBox Version of HKKAZ, HKSAL, HKWPD to use

    PARAMETER:
        field_defs          List of Field Definitions (see Class FieldDefintion)
                            Transactions HKAKZ, HKSAL, HKWPD
    INSTANCE ATTRIBUTES:
        button_state        Text of selected Button
        field_dict          Dictionary Of Version of Used Transactions
    """

    def __init__(self, title, bank_code, transaction_versions):

        Caller.caller = self.__class__.__name__
        self.bank_code = bank_code
        self.transaction_versions = transaction_versions
        transaction_version_allowed = MariaDB().shelve_get_key(self.bank_code, KEY_VERSION_TRANSACTION_ALLOWED)
        if transaction_version_allowed:
            field_defs = [
                FieldDefinition(definition=COMBO,
                                name='HKKAZ statements', length=1,
                                combo_values=transaction_version_allowed['KAZ']),
                FieldDefinition(definition=COMBO,
                                name='HKWPD holdings', length=1,
                                combo_values=transaction_version_allowed['WPD']),
                FieldDefinition(definition=COMBO,
                                name='HKTAN holdings', length=1,
                                combo_values=transaction_version_allowed['TAN']),
            ]
            _set_defaults(field_defs, default_values=(self._get_version('KAZ'), self._get_version('WPD'), self._get_version('TAN')))
            super().__init__(title=title,
                             header='Transaction Versions ({})'.format(
                                 self.bank_code),
                             field_defs=field_defs)
        else:
            MessageBoxTermination()

    def _get_version(self, transaction):

        try:
            return self.transaction_versions[transaction]
        except Exception:
            return '?'

    def button_1_button1(self, event):

        self.button_state = self._button1_text
        self.validation()
        if not self.footer.get():
            for key in self.field_dict.keys():
                self.field_dict[key] = int(self.field_dict[key])
            self.quit_widget()
