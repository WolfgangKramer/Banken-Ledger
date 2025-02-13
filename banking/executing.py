"""
Created on 09.12.2019
__updated__ = "2025-02-13"
Author: Wolfang Kramer
"""


import io
import sys
import requests
import webbrowser

from contextlib import redirect_stdout
from time import sleep
from datetime import date, timedelta, datetime
from threading import Thread
from tkinter import Tk, Menu, TclError, GROOVE, ttk, Canvas, StringVar, font, PhotoImage
from tkinter.ttk import Label
from fints.types import ValueList
from pandas import DataFrame
from yfinance import Ticker

from banking.bank import InitBank, InitBankSync, InitBankAnonymous
from banking.declarations import (
    APP_SHELVE_KEYS, ALPHA_VANTAGE, ALPHA_VANTAGE_DOCUMENTATION,
    Balance,  BANK_MARIADB_INI,
    BMW_BANK_CODE, BUNDESBANK_BLZ_MERKBLATT, BUNDEBANK_BLZ_DOWNLOAD,
    CURRENCY_SIGN, CREDIT,
    DEBIT,
    EURO, ERROR, EDIT_ROW,
    FINTS_SERVER, FINTS_SERVER_ADDRESS,
    START_DATE_PRICES,
    FN_DATE, FN_PROFIT_LOSS, FN_PROFIT, FN_FROM_DATE, FN_TO_DATE,
    FN_PIECES_CUM, FN_ALL_BANKS,
    FN_CREDIT, FN_DEBIT, FN_BALANCE,
    FORMS_TEXT,
    INFORMATION, Informations,
    JSON_KEY_ERROR_MESSAGE, JSON_KEY_META_DATA,
    KEY_ACCOUNTS, KEY_ACC_BANK_CODE, KEY_ACC_OWNER_NAME, KEY_ALPHA_VANTAGE_PRICE_PERIOD,
    KEY_ACC_ACCOUNT_NUMBER, KEY_ACC_SUBACCOUNT_NUMBER, KEY_ACC_ALLOWED_TRANSACTIONS, KEY_ACC_IBAN,
    KEY_ACC_PRODUCT_NAME, KEY_ALPHA_VANTAGE, KEY_ALPHA_VANTAGE_PARAMETER,  KEY_ALPHA_VANTAGE_FUNCTION,
    KEY_BANK_CODE, KEY_BANK_NAME, KEY_DIRECTORY, KEY_LOGGING, KEY_DOWNLOAD_ACTIVATED,
    KEY_GEOMETRY,
    KEY_MARIADB_NAME, KEY_MARIADB_PASSWORD, KEY_MARIADB_USER,
    KEY_MAX_PIN_LENGTH, KEY_MIN_PIN_LENGTH,
    KEY_PIN, KEY_BIC, KEY_PRODUCT_ID,
    KEY_SECURITY_FUNCTION,
    KEY_SERVER, KEY_IDENTIFIER_DELIMITER, KEY_SHOW_MESSAGE, KEY_STORAGE_PERIOD,
    KEY_THREADING, KEY_LEDGER,
    KEY_USER_ID, KEY_VERSION_TRANSACTION,
    MENU_TEXT, MESSAGE_TEXT, MESSAGE_TITLE,
    NOT_ASSIGNED, NUMERIC,
    OUTPUTSIZE_FULL, OUTPUTSIZE_COMPACT, ORIGIN_PRICES, ORIGIN_INSERTED,
    PERCENT,
    SCRAPER_BANKDATA,
    SEPA_AMOUNT, SEPA_CREDITOR_BIC,
    SEPA_CREDITOR_IBAN, SEPA_CREDITOR_NAME, SEPA_EXECUTION_DATE, SEPA_PURPOSE,
    SEPA_PURPOSE_1, SEPA_PURPOSE_2, SEPA_REFERENCE,
    SHELVE_KEYS,
    START_DATE_HOLDING,
    TRANSACTION_DELIVERY, TRUE, TRANSFER_DATA_SEPA_EXECUTION_DATE,
    UNKNOWN,
    WEBSITES, WARNING,
    YAHOO,
)
from banking.declarations_mariadb import (
    TABLE_FIELDS,
    BANKIDENTIFIER,
    DB_amount_currency, DB_acquisition_amount,
    DB_opening_balance, DB_opening_currency, DB_opening_status, DB_opening_entry_date,
    DB_closing_balance, DB_closing_currency, DB_closing_status, DB_closing_entry_date,
    DB_counter, DB_date,
    DB_code, DB_ISIN, DB_entry_date,
    DB_name, DB_pieces,
    DB_total_amount, DB_price_date,
    DB_total_amount_portfolio,
    DB_iban, DB_posted_amount, DB_market_price,
    DB_transaction_type, DB_symbol,
    DB_origin, DB_origin_symbol,
    DB_open, DB_low, DB_high, DB_close, DB_adjclose, DB_volume, DB_dividends, DB_splits,
    DB_amount,
    DB_account,
    DB_portfolio,

    HOLDING, HOLDING_VIEW,
    ISIN, PRICES_ISIN_VIEW, PRICES, SERVER, STATEMENT,
    TRANSACTION, TRANSACTION_VIEW,
    LEDGER, LEDGER_COA, LEDGER_VIEW,

)
from banking.formbuilts import (
    BUTTON_OK, BUTTON_SAVE, BUTTON_NEW, BUTTON_APPEND, BUTTON_DELETE,
    BUTTON_UPDATE, BUTTON_ALPHA_VANTAGE,
    BuiltRadioButtons, BuiltPandasBox,
    destroy_widget,
    FileDialogue,
    MessageBoxInfo, MessageBoxAsk,
    ProgressBar,
    TYP_DECIMAL,
    WM_DELETE_WINDOW,
)
from banking.forms import (
    Adjustments, AlphaVantageParameter, AppCustomizing,
    BankDataChange, BankDataNew, BankDelete,
    InputISIN,  Isin, InputAccount,
    InputDay, InputDate, InputDateHoldingPerc,
    InputDateFieldlist, InputDateFieldlistPrices, InputDateFieldlistHolding,
    PandasBoxLedgerCoaTable, PandasBoxLedgerTable,
    PandasBoxIsins,
    PandasBoxStatementTable, PandasBoxHoldingTable,
    PandasBoxHolding, PandasBoxBalancesAllBanks,
    PandasBoxHoldingPercent, PandasBoxTotals, PandasBoxTransactionDetail,
    PandasBoxHoldingPortfolios, PandasBoxBalances,
    PandasBoxTransactionTable, PandasBoxTransactionProfit,
    PandasBoxHoldingTransaction, PandasBoxPrices,
    PrintList, PrintMessageCode,
    SelectFields,
    SepaCreditBox,
    VersionTransaction, SelectDownloadPrices,
)
from banking.mariadb import MariaDB
from banking.scraper import AlphaVantage, BmwBank
from banking.sepa import SepaCreditTransfer
from banking.utils import (
    date_days, date_years, dec2,
    dictaccount, dict_get_first_key,
    exception_error,
    listbank_codes,
    prices_informations_append,
    shelve_exist, shelve_put_key, shelve_get_key,
    dictbank_names, delete_shelve_files,
)
from banking.declarations import NO_CURRENCY_SIGN
from banking.utils import holding_informations_append
from banking.declarations_mariadb import LEDGER_STATEMENT

'''
Ledger declaratives
'''


PRINT_LENGTH = 140
PAGE_FEED = 50


class FinTS_MariaDB_Banking(object):
    """
    Start of Application
    Execution of Application Customizing
    Execution of MARIADB Retrievals
    Execution of Bank Dialogues

    holdings : ignores download (all_banks) holdings if False
    """

    def __init__(self, title=MESSAGE_TITLE, holdings=True):

        self.holdings = holdings
        if shelve_exist(BANK_MARIADB_INI):
            self.shelve_app = shelve_get_key(
                BANK_MARIADB_INI, APP_SHELVE_KEYS)
            # Connecting DB
            try:
                MariaDBuser = self.shelve_app[KEY_MARIADB_USER]
                MariaDBpassword = self.shelve_app[KEY_MARIADB_PASSWORD]
                MariaDBname = self.shelve_app[KEY_MARIADB_NAME]
            except KeyError:
                exception_error(message=MESSAGE_TEXT['DBLOGIN'])
            try:
                self.mariadb = MariaDB(
                    MariaDBuser, MariaDBpassword, MariaDBname)
            except Exception:
                exception_error(message=MESSAGE_TEXT['CONN'].format(
                    MariaDBuser, MariaDBname))
        else:
            MariaDBname = UNKNOWN
            self.shelve_app = {}
        while True:
            self.wpd_iban = []
            self.kaz_iban = []
            self.bank_names = dictbank_names()
            self.window = None
            self.window = Tk()
            self.progress = ProgressBar(self.window)
            self.window.title(title)
            self.window.geometry('600x400+1+1')
            self.window.resizable(0, 0)
            _canvas = Canvas(self.window)
            _canvas.pack(expand=True, fill='both')
            _canvas_image = PhotoImage(file=("background.gif"))
            _canvas.create_image(0, 0, anchor='nw', image=_canvas_image)
            _canvas.create_text(300, 200, fill="lightblue", font=('Arial', 20, 'bold'),
                                text=MESSAGE_TEXT['DATABASE'].format(MariaDBname))
            self._def_styles()
            self.bank_owner_account = self._create_bank_owner_account()
            self._create_menu(MariaDBname)
            self.footer = StringVar()
            self.message_widget = Label(self.window,
                                        textvariable=self.footer, foreground='RED', justify='center')
            self.footer.set('')
            self.message_widget.pack()
            self.window.protocol(WM_DELETE_WINDOW, self._wm_deletion_window)
            if shelve_exist(BANK_MARIADB_INI):
                self.alpha_vantage = AlphaVantage(self.progress, self.shelve_app[KEY_ALPHA_VANTAGE_FUNCTION],
                                                  self.shelve_app[KEY_ALPHA_VANTAGE_PARAMETER])
            self.window.mainloop()
        try:
            self.window.destroy()
        except TclError:
            pass

    def _wm_deletion_window(self):

        try:
            self.window.destroy()
        except TclError:
            pass
        try:
            self.mariadb.destroy_connection()
        except AttributeError:
            pass
        sys.exit()

    def _bank_name(self, bank_code):

        bank_name = bank_code
        if bank_code in self.bank_names:
            bank_name = self.bank_names[bank_code]
        return bank_name

    def _show_message(self, bank, message=None):
        """
        show messages of FINTS dialogue
        """
        if Informations.bankdata_informations:
            PrintMessageCode(text=Informations.bankdata_informations)
            Informations.bankdata_informations = ''
        if bank.warning_message:
            self.footer.set(MESSAGE_TEXT['TASK_WARNING'])
        else:
            bank_name = self._bank_name(bank.bank_code)
            if message:
                self.footer.set(
                    ' '.join([message, '\n', MESSAGE_TEXT['TASK_DONE']]))
            else:
                self.footer.set(
                    ' '.join([bank_name, '\n', MESSAGE_TEXT['TASK_DONE']]))

        bank.warning_message = False

    def _show_informations(self):
        """
        show informations of threads, if exist
        """
        # downloaad prices
        title = ' '.join([MENU_TEXT['Download'], MENU_TEXT['Prices']])
        PrintMessageCode(title=title, header=Informations.PRICES_INFORMATIONS,
                         text=Informations.prices_informations)
        # download bankdata
        title = ' '.join([MENU_TEXT['Download'], MENU_TEXT['All_Banks']])
        PrintMessageCode(title=title, header=Informations.BANKDATA_INFORMATIONS,
                         text=Informations.bankdata_informations)
        # update market_price in holding
        title = ' '.join([MENU_TEXT['Update'], MENU_TEXT['Holding']])
        PrintMessageCode(title=title, header=Informations.HOLDING_INFORMATIONS,
                         text=Informations.holding_informations)

    def _delete_footer(self):

        try:
            self.footer.set('')
        except Exception:
            pass
        self._show_informations()

    def _all_banks(self):

        self._delete_footer()
        CANCELED = ''
        if self.shelve_app[KEY_THREADING] == TRUE:
            banks_credentials = listbank_codes()
            banks_download = []
            for bank_code in banks_credentials:
                if shelve_get_key(bank_code, KEY_DOWNLOAD_ACTIVATED):
                    # PIN input outside of Thread
                    bank = self._bank_init(bank_code)
                    if bank.scraper:
                        self.footer.set(MESSAGE_TEXT['CREDENTIALS_CHECK'].format(
                            self.bank_names[bank_code]))
                        if bank.credentials():
                            banks_download.append(bank_code)
                        else:
                            MessageBoxInfo(MESSAGE_TEXT['CREDENTIALS'].format(
                                self.bank_names[bank_code]))
                    else:
                        self.footer.set(MESSAGE_TEXT['CREDENTIALS_CHECK'].format(
                            self.bank_names[bank_code]))
                        if bank.dialogs._start_dialog(bank):
                            banks_download.append(bank_code)
                        else:
                            MessageBoxInfo(MESSAGE_TEXT['CREDENTIALS'].format(
                                self.bank_names[bank_code]))
            bank.opened_bank_code = None  # triggers bank opening messages
            self.progress.start()
            for bank_code in banks_download:
                bank = self._bank_init(bank_code)
                self.footer.set(
                    MESSAGE_TEXT['DOWNLOAD_RUNNING'].format(bank.bank_name))
                download_thread = Thread(
                    name=bank.bank_name, target=self.mariadb.all_accounts, args=(bank, self.holdings))
                download_thread.start()
                while download_thread.is_alive():
                    sleep(1)
                    self.progress.update_progressbar()
            self.progress.stop()
            self.footer.set(
                MESSAGE_TEXT['DOWNLOAD_DONE'].format(CANCELED, 10 * '!'))
        else:
            for bank_code in listbank_codes():
                if shelve_get_key(bank_code, KEY_DOWNLOAD_ACTIVATED):
                    self._all_accounts(bank_code)
        self._show_informations()

    def _all_accounts(self, bank_code):

        self._delete_footer()
        bank = self._bank_init(bank_code)
        if bank:
            self.footer.set(
                MESSAGE_TEXT['DOWNLOAD_RUNNING'].format(bank.bank_name))
            self.progress.start()
            self.mariadb.all_accounts(bank, self.holdings)
            self.progress.stop()
            self.footer.set(
                MESSAGE_TEXT['DOWNLOAD_DONE'].format(bank.bank_name, 10 * '!'))
            self._show_message(bank)

    def _all_holdings(self, bank_code):

        self._delete_footer()
        bank = self._bank_init(bank_code)
        if bank:
            self.footer.set(
                MESSAGE_TEXT['DOWNLOAD_RUNNING'].format(bank.bank_name))
            self.mariadb.all_holdings(bank)
            self.footer.set(
                MESSAGE_TEXT['DOWNLOAD_DONE'].format(bank.bank_name, 10 * '!'))
            self._show_message(bank)

    def _appcustomizing(self):

        self._delete_footer()
        while True:
            app_data_box = AppCustomizing(shelve_app=self.shelve_app)
            if app_data_box.button_state == WM_DELETE_WINDOW:
                return
            data = [(KEY_PRODUCT_ID,  app_data_box.field_dict[KEY_PRODUCT_ID]),
                    (KEY_ALPHA_VANTAGE,
                     app_data_box.field_dict[KEY_ALPHA_VANTAGE]),
                    (KEY_DIRECTORY,  app_data_box.field_dict[KEY_DIRECTORY]),
                    (KEY_MARIADB_NAME,
                     app_data_box.field_dict[KEY_MARIADB_NAME].upper()),
                    (KEY_MARIADB_USER,
                     app_data_box.field_dict[KEY_MARIADB_USER]),
                    (KEY_MARIADB_PASSWORD,
                     app_data_box.field_dict[KEY_MARIADB_PASSWORD]),
                    (KEY_SHOW_MESSAGE,
                     app_data_box.field_dict[KEY_SHOW_MESSAGE]),
                    (KEY_LOGGING,  app_data_box.field_dict[KEY_LOGGING]),
                    (KEY_THREADING,  app_data_box.field_dict[KEY_THREADING]),
                    (KEY_ALPHA_VANTAGE_PRICE_PERIOD,
                     app_data_box.field_dict[KEY_ALPHA_VANTAGE_PRICE_PERIOD]),
                    (KEY_LEDGER,
                     app_data_box.field_dict[KEY_LEDGER])
                    ]
            shelve_put_key(BANK_MARIADB_INI, data, flag='c')
            if app_data_box.button_state == BUTTON_SAVE:
                MessageBoxInfo(message=MESSAGE_TEXT['DATABASE_REFRESH'])
                self._wm_deletion_window()
            self.shelve_app = shelve_get_key(BANK_MARIADB_INI, APP_SHELVE_KEYS)

    def _def_styles(self):

        style = ttk.Style()
        style.theme_use(style.theme_names()[0])
        style.configure('TLabel', font=('Arial', 8, 'bold'))
        style.configure('OPT.TLabel', font=(
            'Arial', 8, 'bold'), foreground='Grey')
        style.configure('HDR.TLabel', font=('Courier', 8), foreground='Grey')
        style.configure('TButton', font=('Arial', 8, 'bold'), relief=GROOVE,
                        highlightcolor='blue', highlightthickness=5, shiftrelief=3)
        style.configure('TText', font=('Courier', 8))

    def _alpha_vantage_refresh(self):

        self.footer.set(MESSAGE_TEXT['ALPHA_VANTAGE_REFRESH_RUN'])
        self.progress.start()
        refresh = self.alpha_vantage.refresh()
        if refresh:
            self.footer.set(MESSAGE_TEXT['ALPHA_VANTAGE_REFRESH'])
        else:
            self.footer.set(MESSAGE_TEXT['ALPHA_VANTAGE_ERROR'])
        self.progress.stop()

    def _bank_data_change(self, bank_code):

        self._delete_footer()
        bank_name = self._bank_name(bank_code)
        title = ' '.join([bank_name, MENU_TEXT['Customize'],
                          MENU_TEXT['Change Login Data']])
        try:
            login_data = shelve_get_key(bank_code, [KEY_BANK_NAME, KEY_USER_ID, KEY_PIN, KEY_BIC,
                                                    KEY_SERVER, KEY_IDENTIFIER_DELIMITER, KEY_DOWNLOAD_ACTIVATED])
        except KeyError as key_error:
            MessageBoxInfo(
                title=title, message=MESSAGE_TEXT['LOGIN'].format(bank_code, key_error))
            delete_shelve_files(bank_code)
            MessageBoxInfo(title=title,
                           message=MESSAGE_TEXT['BANK_DELETED'].format(bank_code))
            return
        bank_data_box = BankDataChange(
            title, self.mariadb, bank_code, login_data)
        if bank_data_box.button_state == WM_DELETE_WINDOW:
            return
        try:
            data = [(KEY_BANK_CODE, bank_code),
                    (KEY_BANK_NAME, bank_data_box.field_dict[KEY_BANK_NAME]),
                    (KEY_USER_ID,  bank_data_box.field_dict[KEY_USER_ID]),
                    (KEY_PIN,  bank_data_box.field_dict[KEY_PIN]),
                    (KEY_BIC,  bank_data_box.field_dict[KEY_BIC]),
                    (KEY_SERVER,  bank_data_box.field_dict[KEY_SERVER]),
                    (KEY_IDENTIFIER_DELIMITER,
                     bank_data_box.field_dict[KEY_IDENTIFIER_DELIMITER]),
                    (KEY_DOWNLOAD_ACTIVATED,
                     bank_data_box.field_dict[KEY_DOWNLOAD_ACTIVATED]),
                    ]
            shelve_put_key(bank_code, data)
        except KeyError as key_error:
            exception_error(
                message=MESSAGE_TEXT['LOGIN'].format(bank_code, key_error))
            return
        if bank_code in list(SCRAPER_BANKDATA.keys()):
            self._bank_data_scraper(bank_code)
        else:
            self._bank_security_function(bank_code, False)

    def _bank_data_new(self):

        self._delete_footer()
        bankidentifier = self.mariadb.select_table(
            BANKIDENTIFIER, [DB_code], order=DB_code)
        bank_codes = self.mariadb.select_server_code()
        title = ' '.join([MENU_TEXT['Customize'], MENU_TEXT['New Bank']])
        if not bankidentifier:
            MessageBoxInfo(
                title=title, message=MESSAGE_TEXT['IMPORT_CSV'].format(BANKIDENTIFIER.upper()))
        elif not bank_codes:
            MessageBoxInfo(
                title=title, message=MESSAGE_TEXT['IMPORT_CSV'].format(SERVER.upper()))
        else:
            bank_data_box = BankDataNew(
                title, self.mariadb, bank_codes=bank_codes)
            if bank_data_box.button_state == WM_DELETE_WINDOW:
                return
            bank_code = bank_data_box.field_dict[KEY_BANK_CODE]
            try:
                data = [(KEY_BANK_CODE, bank_data_box.field_dict[KEY_BANK_CODE]),
                        (KEY_BANK_NAME,
                         bank_data_box.field_dict[KEY_BANK_NAME]),
                        (KEY_USER_ID,  bank_data_box.field_dict[KEY_USER_ID]),
                        (KEY_PIN,  bank_data_box.field_dict[KEY_PIN]),
                        (KEY_BIC,  bank_data_box.field_dict[KEY_BIC]),
                        (KEY_SERVER,  bank_data_box.field_dict[KEY_SERVER]),
                        (KEY_IDENTIFIER_DELIMITER,
                         bank_data_box.field_dict[KEY_IDENTIFIER_DELIMITER]),
                        (KEY_DOWNLOAD_ACTIVATED,
                         bank_data_box.field_dict[KEY_DOWNLOAD_ACTIVATED]),
                        ]
                shelve_put_key(bank_code, data, flag='c')
            except KeyError as key_error:
                exception_error()
                MessageBoxInfo(title=title,
                               message=MESSAGE_TEXT['LOGIN'].format(bank_code, key_error))
                return
            bank_name = shelve_get_key(bank_code, KEY_BANK_NAME)
            if bank_code in list(SCRAPER_BANKDATA.keys()):
                if bank_code == BMW_BANK_CODE:
                    self._bank_data_scraper(BMW_BANK_CODE)
                MessageBoxInfo(title=title, message=MESSAGE_TEXT['BANK_DATA_NEW_SCRAPER'].format(
                    bank_name, bank_code))
            else:
                self._bank_security_function(bank_code, True)
                MessageBoxInfo(title=title, message=MESSAGE_TEXT['BANK_DATA_NEW'].format(
                    bank_name, bank_code))
            try:
                self.window.destroy()
            except Exception:
                pass

    def _bank_data_delete(self):

        self._delete_footer()
        title = ' '.join([MENU_TEXT['Customize'], MENU_TEXT['Delete Bank']])
        deletebank = BankDelete(title)
        if deletebank.button_state == WM_DELETE_WINDOW:
            return
        bank_code = deletebank.field_dict[KEY_BANK_CODE]
        bank_name = deletebank.field_dict[KEY_BANK_NAME]
        for table in [STATEMENT, LEDGER_STATEMENT, HOLDING, TRANSACTION]:
            if self.mariadb.iban_exists(table, bank_code):
                MessageBoxInfo(title=title, message=MESSAGE_TEXT['BANK_DELETE_failed'].format(
                    bank_name, table.upper()))
                return
        delete_shelve_files(bank_code)
        MessageBoxInfo(
            title=title,
            message=MESSAGE_TEXT['BANK_DELETED'].format(bank_name, bank_code))
        self.window.destroy()

    def _bank_data_scraper(self, bank_code):

        bank = self._bank_init(bank_code)
        get_accounts = bank.get_accounts(bank)
        accounts = []
        for account in get_accounts:
            acc = {}
            account_product_name, owner_name, iban, account_number = account
            acc[KEY_ACC_IBAN] = iban
            acc[KEY_ACC_ACCOUNT_NUMBER] = account_number
            acc[KEY_ACC_SUBACCOUNT_NUMBER] = None
            acc[KEY_ACC_BANK_CODE] = bank_code
            acc[KEY_ACC_OWNER_NAME] = owner_name
            acc[KEY_ACC_PRODUCT_NAME] = account_product_name
            acc[KEY_ACC_ALLOWED_TRANSACTIONS] = ['HKKAZ']
            accounts.append(acc)
        data = [(KEY_ACCOUNTS, accounts),
                (KEY_STORAGE_PERIOD, bank.storage_period),
                (KEY_MIN_PIN_LENGTH, 6),
                (KEY_MAX_PIN_LENGTH, 16)]
        shelve_put_key(bank_code, data, flag='w')

    def _bank_init(self, bank_code):

        if bank_code in list(SCRAPER_BANKDATA.keys()):
            if bank_code == BMW_BANK_CODE:
                bank = BmwBank()
        else:
            bank = InitBank(bank_code, self.mariadb)
        return bank

    def _bank_refresh_bpd(self, bank_code):

        self._delete_footer()
        bank = InitBankAnonymous(bank_code, self.mariadb)
        bank.dialogs.anonymous(bank)
        bank_name = self._bank_name(bank_code)
        message = ' '.join([bank_name, MENU_TEXT['Customize'],
                            MENU_TEXT['Refresh BankParameterData']])
        self._show_message(bank, message=message)

    def _bank_show_shelve(self, bank_code):

        self._delete_footer()
        shelve_data = shelve_get_key(bank_code, SHELVE_KEYS)
        shelve_text = MESSAGE_TEXT['SHELVE'].format(bank_code)
        for key in SHELVE_KEYS:
            if shelve_data[key]:
                if key == KEY_ACCOUNTS:
                    shelve_text = shelve_text + '{:20}  \n'.format(key)
                    for account in shelve_data[key]:
                        shelve_text = shelve_text + \
                            '{:5} {:80} \n'.format(' ', 80 * '_')
                        for item in account.keys():
                            if isinstance(account[item], list):
                                description = item
                                for value_ in account[item]:
                                    shelve_text = shelve_text + '{:5} {:20} {} \n'.format(
                                        ' ', description, value_)
                                    description = len(description) * ' '
                            else:
                                shelve_text = shelve_text + '{:5} {:20} {}\n'.format(
                                    ' ', item, account[item])
                else:
                    if isinstance(shelve_data[key], list) or isinstance(shelve_data[key],
                                                                        ValueList):
                        description = key
                        for item in shelve_data[key]:
                            shelve_text = shelve_text + \
                                '{:20} {} \n'.format(description, item)
                            description = len(description) * ' '
                    elif isinstance(shelve_data[key], dict):
                        description = key
                        for _key in list(shelve_data[key].keys()):
                            shelve_text = shelve_text + \
                                '{:20} {} \n'.format(description, _key)
                            description = len(description) * ' '
                            shelve_text = (shelve_text + '{:20} {} \n'.format(
                                description, shelve_data[key][_key]))
                    else:
                        shelve_text = shelve_text + \
                            '{:20} {} \n'.format(key, shelve_data[key])
            else:
                shelve_text = shelve_text + '{:20} {} \n'.format(key, 'None')
        bank_name = self._bank_name(bank_code)
        title = ' '.join([bank_name, MENU_TEXT['Customize'],
                          MENU_TEXT['Show Data']])
        PrintList(title=title, text=shelve_text, fullscreen=True)

    def _bank_sync(self, bank_code):

        self._delete_footer()
        bank = InitBankSync(bank_code, self.mariadb)
        bank.dialogs.sync(bank)
        bank_name = self._bank_name(bank_code)
        message = ' '.join(
            [bank_name, MENU_TEXT['Customize'], MENU_TEXT['Synchronize']])
        self._show_message(bank, message=message)

    def _bank_version_transaction(self, bank_code):

        self._delete_footer()
        bank_name = self._bank_name(bank_code)
        title = ' '.join([bank_name, MENU_TEXT['Customize'],
                          MENU_TEXT['Change FinTS Transaction Version']])
        transaction_versions = shelve_get_key(
            bank_code, KEY_VERSION_TRANSACTION)
        try:
            transaction_version_box = VersionTransaction(
                title, bank_code, transaction_versions)
            if transaction_version_box.button_state == WM_DELETE_WINDOW:
                return
            for key in transaction_version_box.field_dict.keys():
                transaction_versions[key[2:5]
                                     ] = transaction_version_box.field_dict[key]
            data = (KEY_VERSION_TRANSACTION, transaction_versions)
            shelve_put_key(bank_code, data)
        except KeyError as key_error:
            MessageBoxInfo(title=title, message=MESSAGE_TEXT['LOGIN'].format(
                bank_name, key_error))

    def _create_menu(self, MariaDBname):

        menu_font = font.Font(family='Arial', size=11)
        menu = Menu(self.window)
        self.window.config(menu=menu, borderwidth=10, relief=GROOVE)
        if MariaDBname != UNKNOWN:
            if self.shelve_app[KEY_LEDGER]:
                self._create_menu_ledger(menu, menu_font)
        if self.bank_names != {} and MariaDBname != UNKNOWN:
            self._create_menu_show(menu, self.bank_owner_account, menu_font)
            self._create_menu_download(menu, menu_font)
            self._create_menu_transfer(menu, menu_font)
        if MariaDBname != UNKNOWN:
            self._create_menu_database(
                menu, menu_font, self.bank_owner_account)
        self._create_menu_customizing(menu, menu_font, MariaDBname)

    def _create_menu_ledger(self, menu, menu_font):
        """
         LEDGER Menu
        """
        ledger_menu = Menu(
            menu, tearoff=0, font=menu_font, bg='Lightblue')
        menu.add_cascade(
            label=MENU_TEXT['Ledger'], menu=ledger_menu)
        result = self.mariadb.select_table(
            LEDGER_COA, 'COUNT(*)')  # count rows in LEDGER_COA table
        if result[0][0] != 0:
            ledger_menu.add_command(
                label=MENU_TEXT['Check Upload'], command=self._ledger_upload_check)
            ledger_menu.add_command(
                label=MENU_TEXT['Check Bank Statement'], command=self._ledger_bank_statement_check)
            ledger_menu.add_separator()
            ledger_menu.add_command(
                label=MENU_TEXT['Balances'], command=self._ledger_balances)
            ledger_menu.add_command(
                label=MENU_TEXT['Assets'], command=self._ledger_assets)
            ledger_menu.add_command(
                label=MENU_TEXT['Journal'], command=self._ledger_journal)

            ledger_menu.add_command(
                label=MENU_TEXT['Account'], command=self._ledger_account)
            ledger_menu.add_separator()
        ledger_menu.add_command(
            label=MENU_TEXT['Chart of Accounts'], command=self._ledger_coa_table)

    def _create_menu_show(self, menu, bank_owner_account, menu_font):
        """
         SHOW Menu
        """
        show_menu = Menu(menu, tearoff=0, font=menu_font, bg='Lightblue')
        menu.add_cascade(label=MENU_TEXT['Show'], menu=show_menu)
        site_menu = Menu(show_menu, tearoff=0,
                         font=menu_font, bg='Lightblue')
        show_menu.add_cascade(
            label=MENU_TEXT["WebSites"], menu=site_menu, underline=0)
        for website in WEBSITES.keys():
            site_menu.add_command(label=website,
                                  command=lambda x=WEBSITES[website]: self._websites(x))

        if self.shelve_app[KEY_ALPHA_VANTAGE]:
            show_menu.add_command(
                label=MENU_TEXT['Alpha Vantage'], command=self._show_alpha_vantage)
        if self.shelve_app[KEY_ALPHA_VANTAGE]:
            show_menu.add_command(
                label=MENU_TEXT['Alpha Vantage Symbol Search'], command=self._show_alpha_vantage_search_symbol)
        show_menu.add_command(
            label=MENU_TEXT['Balances'], command=self._show_balances_all_banks)
        self._create_menu_banks(
            MENU_TEXT['Show'], bank_owner_account, show_menu, menu_font)

    def _create_menu_download(self, menu, menu_font):
        """
        DOWNLOAD Menu
        """
        download_menu = Menu(
            menu, tearoff=0, font=menu_font, bg='Lightblue')
        menu.add_cascade(label=MENU_TEXT['Download'], menu=download_menu)
        download_menu.add_command(
            label=MENU_TEXT['All_Banks'], command=self._all_banks)
        download_menu.add_separator()
        download_menu.add_command(
            label=MENU_TEXT['Prices'], command=self._import_prices)
        download_menu.add_separator()
        for bank_name in self.bank_names.values():
            bank_code = dict_get_first_key(self.bank_names, bank_name)
            download_menu.add_cascade(
                label=bank_name,
                command=lambda x=bank_code: self._all_accounts(x))
            accounts = shelve_get_key(bank_code, KEY_ACCOUNTS)
            if accounts:
                for acc in accounts:
                    if 'HKWPD' in acc[KEY_ACC_ALLOWED_TRANSACTIONS]:
                        download_menu.add_cascade(
                            label=' '.join(
                                [bank_name, MENU_TEXT['Holding'], acc[KEY_ACC_PRODUCT_NAME], acc[KEY_ACC_ACCOUNT_NUMBER]]),
                            command=lambda x=bank_code: self._all_holdings(x))
            download_menu.add_separator()

    def _create_menu_transfer(self, menu, menu_font):
        '''
        TRANSFER Menu
        '''
        transfer_menu = Menu(menu, tearoff=0, font=menu_font, bg='Lightblue')
        menu.add_cascade(label=MENU_TEXT['Transfer'], menu=transfer_menu)
        bank_names = {}
        for bank_name in self.bank_names.values():
            bank_code = dict_get_first_key(self.bank_names, bank_name)
            accounts = shelve_get_key(bank_code, KEY_ACCOUNTS)
            if accounts:
                for acc in accounts:
                    if 'HKCCS' in acc[KEY_ACC_ALLOWED_TRANSACTIONS]:
                        bank_names[bank_code] = bank_name
        for bank_name in bank_names.values():
            bank_code = dict_get_first_key(bank_names, bank_name)
            accounts = shelve_get_key(bank_code, KEY_ACCOUNTS)
            account_menu = Menu(transfer_menu, tearoff=0,
                                font=menu_font, bg='Lightblue')
            if accounts:
                for acc in accounts:
                    if 'HKCCS' in acc[KEY_ACC_ALLOWED_TRANSACTIONS]:
                        label = acc[KEY_ACC_PRODUCT_NAME]
                        if not label:
                            label = acc[KEY_ACC_ACCOUNT_NUMBER]
                        label = ' '.join([MENU_TEXT['Statement'], label])
                        account_menu.add_command(
                            label=label,
                            command=(lambda x=bank_code,
                                     y=acc: self.sepa_credit_transfer(x, y)))
            transfer_menu.add_cascade(
                label=bank_name, menu=account_menu, underline=0)

    def _create_menu_database(self, menu, menu_font, bank_owner_account):
        """
        DATABASE Menu
        """
        database_menu = Menu(
            menu, tearoff=0, font=menu_font, bg='Lightblue')
        menu.add_cascade(label=MENU_TEXT['Database'], menu=database_menu)
        bank_names = {}
        for bank_name in self.bank_names.values():
            bank_code = dict_get_first_key(self.bank_names, bank_name)
            accounts = shelve_get_key(bank_code, KEY_ACCOUNTS)
            if accounts:
                for acc in accounts:
                    if 'HKWPD' in acc[KEY_ACC_ALLOWED_TRANSACTIONS]:
                        bank_names[bank_code] = bank_name
        if bank_names != {}:
            all_banks_menu = Menu(
                database_menu, tearoff=0, font=menu_font, bg='Lightblue')
            database_menu.add_cascade(
                label=MENU_TEXT['All_Banks'], menu=all_banks_menu, underline=0)
            all_banks_menu.add_command(
                label=MENU_TEXT['Holding Performance'],
                command=(lambda x=FN_ALL_BANKS, y='':
                         self._data_holding_performance(x, y)))
            all_banks_menu.add_command(
                label=MENU_TEXT['Holding ISIN Comparision'],
                command=(lambda x=FN_ALL_BANKS, y='', z=EURO: self._data_holding_isin_comparision(x, y, z)))
            all_banks_menu.add_command(
                label=MENU_TEXT['Holding ISIN Comparision'] + '%',
                command=(lambda x=FN_ALL_BANKS, y='', z=PERCENT: self._data_holding_isin_comparision(x, y, z)))
            all_banks_menu.add_command(label=MENU_TEXT['Balances'],
                                       command=self._data_balances)

            all_banks_menu.add_command(
                label=MENU_TEXT['Transaction Detail'],
                command=(lambda x=FN_ALL_BANKS,
                         y=None: self._data_transaction_detail(x, y)))
            self._create_menu_banks(
                MENU_TEXT['Database'], bank_owner_account, database_menu, menu_font)
            database_menu.add_separator()
        database_menu.add_command(
            label=MENU_TEXT['ISIN Table'], command=self._isin_table)
        database_menu.add_command(
            label=MENU_TEXT['Prices ISINs'],
            command=(lambda x=None: self._data_prices(x)))
        database_menu.add_command(
            label=MENU_TEXT['Prices ISINs'] + '%',
            command=(lambda x=PERCENT: self._data_prices(x)))
        database_menu.add_command(
            label=MENU_TEXT['Historical Prices'],  command=self._import_prices_histclose)

    def _create_menu_customizing(self, menu, menu_font, MariaDBname):
        """
        CUSTOMIZE Menu
        """
        customize_menu = Menu(menu, tearoff=0, font=menu_font, bg='Lightblue')
        menu.add_cascade(label=MENU_TEXT['Customize'], menu=customize_menu)
        customize_menu.add_command(label=MENU_TEXT['Application INI File'],
                                   command=self._appcustomizing)
        customize_menu.add_command(label=MENU_TEXT['Reset Screen Positions'],
                                   command=self._reset)
        if self.shelve_app:
            customize_menu.add_separator()
            customize_menu.add_command(label=MENU_TEXT['Import Bankidentifier CSV-File'],
                                       command=self._import_bankidentifier)
            customize_menu.add_command(label=MENU_TEXT['Import Server CSV-File'],
                                       command=self._import_server)
            customize_menu.add_separator()
            if self.shelve_app[KEY_ALPHA_VANTAGE]:
                customize_menu.add_command(label=MENU_TEXT['Refresh Alpha Vantage'],
                                           command=self._alpha_vantage_refresh)
                customize_menu.add_separator()
            if MariaDBname != UNKNOWN:
                if self.mariadb.select_server:
                    customize_menu.add_command(label=MENU_TEXT['New Bank'],
                                               command=self._bank_data_new)
                    customize_menu.add_command(label=MENU_TEXT['Delete Bank'],
                                               command=self._bank_data_delete)
                else:
                    MessageBoxInfo(message=MESSAGE_TEXT['PRODUCT_ID'])
            if self.bank_names:
                customize_menu.add_separator()
                for bank_name in self.bank_names.values():
                    bank_code = dict_get_first_key(self.bank_names, bank_name)
                    cust_bank_menu = Menu(customize_menu, tearoff=0,
                                          font=menu_font, bg='Lightblue')
                    cust_bank_menu.add_command(label=MENU_TEXT['Change Login Data'],
                                               command=lambda x=bank_code: self._bank_data_change(x))
                    if bank_code not in list(SCRAPER_BANKDATA.keys()):
                        cust_bank_menu.add_command(label=MENU_TEXT['Synchronize'],
                                                   command=lambda x=bank_code: self._bank_sync(x))
                        cust_bank_menu.add_command(label=MENU_TEXT['Change Security Function'],
                                                   command=lambda
                                                   x=bank_code: self._bank_security_function(x, False))
                        cust_bank_menu.add_command(label=MENU_TEXT['Refresh BankParameterData'],
                                                   command=lambda
                                                   x=bank_code: self._bank_refresh_bpd(x))
                        cust_bank_menu.add_command(label=MENU_TEXT['Change FinTS Transaction Version'],
                                                   command=lambda
                                                   x=bank_code: self._bank_version_transaction(x))
                    cust_bank_menu.add_command(label=MENU_TEXT['Show Data'],
                                               command=lambda x=bank_code: self._bank_show_shelve(x))
                    customize_menu.add_cascade(
                        label=bank_name, menu=cust_bank_menu, underline=0)

    def _create_menu_banks(self, menu_text, bank_owner_account, typ_menu, menu_font):

        for bank_code in self.bank_names.keys():
            bank_name = self.bank_names[bank_code]
            if bank_code in bank_owner_account.keys():
                owner_menu = Menu(typ_menu, tearoff=0,
                                  font=menu_font, bg='Lightblue')
                owner_menu.add_command(label=MENU_TEXT['Balances'],
                                       command=lambda x=bank_code, y=bank_name: self._show_balances(x, y))
                if bank_owner_account:
                    owners_exist = False
                    for owner_name in bank_owner_account[bank_code].keys():
                        account_menu = Menu(
                            owner_menu, tearoff=0, font=menu_font, bg='Lightblue')
                        accounts = bank_owner_account[bank_code][owner_name]
                        if menu_text == MENU_TEXT['Show']:
                            accounts_exist = self._create_menu_show_accounts(
                                accounts, account_menu, bank_code, bank_name, owner_name=owner_name)
                        elif menu_text == MENU_TEXT['Database']:
                            accounts_exist = self._create_menu_database_accounts(
                                accounts, account_menu, bank_name, menu_font)
                        if accounts_exist:
                            owners_exist = True
                            owner_menu.add_cascade(
                                label=owner_name, menu=account_menu, underline=0)
                    if owners_exist:
                        typ_menu.add_cascade(
                            label=bank_name, menu=owner_menu, underline=0)
            else:
                account_menu = Menu(
                    typ_menu, tearoff=0, font=menu_font, bg='Lightblue')
                bank_code = dict_get_first_key(self.bank_names, bank_name)
                accounts = shelve_get_key(bank_code, KEY_ACCOUNTS)
                if menu_text == MENU_TEXT['Show']:
                    accounts_exist = self._create_menu_show_accounts(
                        accounts, account_menu, bank_code, bank_name)
                elif menu_text == MENU_TEXT['Database']:
                    accounts_exist = self._create_menu_database_accounts(
                        accounts, account_menu, bank_name, menu_font)
                if accounts_exist:
                    typ_menu.add_cascade(
                        label=bank_name, menu=account_menu, underline=0)

    def _create_menu_show_accounts(self, accounts, account_menu, bank_code, bank_name, owner_name=None):

        accounts_exist = True
        account_menu.add_command(label=MENU_TEXT['Balances'],
                                 command=lambda x=bank_code, y=bank_name: self._show_balances(x, y, owner_name=owner_name))
        if accounts:
            for acc in accounts:
                if 'HKKAZ' in acc[KEY_ACC_ALLOWED_TRANSACTIONS]:
                    self.kaz_iban.append(acc[KEY_ACC_IBAN])
                    label = ' '.join(
                        [MENU_TEXT['Statement'], acc[KEY_ACC_PRODUCT_NAME], acc[KEY_ACC_ACCOUNT_NUMBER]])
                    account_menu.add_command(
                        label=label,
                        command=lambda x=bank_code, y=acc: self._show_statements(x, y))
                if 'HKWPD' in acc[KEY_ACC_ALLOWED_TRANSACTIONS]:
                    label = ' '.join(
                        [MENU_TEXT['Holding'], acc[KEY_ACC_PRODUCT_NAME], acc[KEY_ACC_ACCOUNT_NUMBER]])
                    account_menu.add_command(
                        label=label,
                        command=lambda x=bank_code, y=acc: self._show_holdings(x, y))
                    label = label + '%'
                    account_menu.add_command(
                        label=label,
                        command=lambda x=bank_code, y=acc: self._show_holdings_perc(x, y))
                if 'HKWDU' in acc[KEY_ACC_ALLOWED_TRANSACTIONS] or \
                        'HKWPD' in acc[KEY_ACC_ALLOWED_TRANSACTIONS]:
                    label = ' '.join(
                        [MENU_TEXT['Holding'], acc[KEY_ACC_PRODUCT_NAME], acc[KEY_ACC_ACCOUNT_NUMBER], TRANSACTION.upper()])
                    account_menu.add_command(
                        label=label,
                        command=(lambda x=bank_code, y=acc: self._show_transactions(x, y)))
        return accounts_exist

    def _create_menu_database_accounts(self, accounts, account_menu, bank_name, menu_font):

        accounts_exist = False
        if accounts:
            for acc in accounts:
                if 'HKWPD' in acc[KEY_ACC_ALLOWED_TRANSACTIONS]:
                    accounts_exist = True
                    account_menu.add_command(
                        label=MENU_TEXT['Holding Performance'],
                        command=(lambda x=bank_name,
                                 y=acc[KEY_ACC_IBAN]: self._data_holding_performance(x, y)))
                    account_menu.add_command(
                        label=MENU_TEXT['Holding ISIN Comparision'],
                        command=(lambda x=bank_name, y=acc[KEY_ACC_IBAN],
                                 z=EURO: self._data_holding_isin_comparision(x, y, z)))
                    account_menu.add_command(
                        label=MENU_TEXT['Holding ISIN Comparision'] + '%',
                        command=(lambda x=bank_name, y=acc[KEY_ACC_IBAN],
                                 z=PERCENT: self._data_holding_isin_comparision(x, y, z)))
                    account_menu.add_command(
                        label=MENU_TEXT['Transaction Detail'],
                        command=(lambda x=bank_name,
                                 y=acc[KEY_ACC_IBAN]: self._data_transaction_detail(x, y)))
                    account_menu.add_command(
                        label=MENU_TEXT['Profit of closed Transactions'],
                        command=(lambda x=bank_name,
                                 y=acc[KEY_ACC_IBAN]: self._transactions_profit(x, y)))
                    account_menu.add_command(
                        label=MENU_TEXT['Profit Transactions incl. current Depot Positions'],
                        command=(lambda x=bank_name,
                                 y=acc[KEY_ACC_IBAN]: self._transactions_profit_all(x, y)))
                    account_menu.add_command(
                        label=MENU_TEXT['Prices ISINs'],
                        command=(lambda x=None: self._data_prices(x)))
                    account_menu.add_command(
                        label=MENU_TEXT['Prices ISINs'] + '%',
                        command=(lambda x=PERCENT: self._data_prices(x)))

                    account_menu.add_separator()
                    account_menu.add_command(
                        label=MENU_TEXT['Transactions Table'],
                        command=(lambda x=bank_name,
                                 y=acc[KEY_ACC_IBAN]: self._data_transaction_table(x, y)))
                    account_menu.add_command(
                        label=MENU_TEXT['Holding Table'],
                        command=(lambda x=bank_name,
                                 y=acc[KEY_ACC_IBAN]: self._data_holding_table(x, y)))
                    account_menu.add_separator()
                    account_menu.add_command(
                        label=MENU_TEXT['Update Holding Prices'],
                        command=(lambda x=bank_name,
                                 y=acc[KEY_ACC_IBAN]:
                                 self._data_update_holding_prices(x, y)))
                    account_menu.add_command(
                        label=MENU_TEXT['Update Portfolio Total Amount'],
                        command=(lambda x=bank_name,
                                 y=acc[KEY_ACC_IBAN]:
                                 self._update_holding_total_amount_portfolio(x, y)))
                    account_menu.add_separator()
                    account_menu.add_command(
                        label=MENU_TEXT['Import Transactions'],
                        command=(lambda x=bank_name,
                                 y=acc[KEY_ACC_IBAN]: self._import_transaction(x, y)))
                    account_menu.add_command(
                        label=MENU_TEXT['Check Transactions Pieces'],
                        command=(lambda x=bank_name,
                                 y=acc[KEY_ACC_IBAN]: self._transactions_pieces(x, y)))
        return accounts_exist

    def _create_bank_owner_account(self):
        '''
        create  multiple bank_owner_account hierarchy as dicts
        returns: dict : key--> bank_name: 
                            value/key--> owner:
                                value --> list  accounts
                                    list_item  --> dict account_data
        '''
        bank_owner_account = {}
        for bank_code in self.bank_names.keys():
            accounts = shelve_get_key(bank_code, KEY_ACCOUNTS)
            account_product_names = []
            if accounts:
                for acc in accounts:
                    account_product_names.append(acc[KEY_ACC_PRODUCT_NAME])
                # all account names are different
                if len(account_product_names) == len(set(account_product_names)):
                    pass  # owner name not used in menu
                else:
                    owners = {}  # list of owner accounts
                    if accounts:
                        owners = {}  # list of owner accounts
                        for acc in accounts:
                            if acc[KEY_ACC_OWNER_NAME] is None:
                                acc[KEY_ACC_OWNER_NAME] = bank_code
                            owners[acc[KEY_ACC_OWNER_NAME]] = []
                        for acc in accounts:
                            if acc[KEY_ACC_OWNER_NAME] is None:
                                acc[KEY_ACC_OWNER_NAME] = bank_code
                            owners[acc[KEY_ACC_OWNER_NAME]
                                   ] = owners[acc[KEY_ACC_OWNER_NAME]] + [acc]
                    bank_owner_account[bank_code] = owners
        return bank_owner_account

    def _date_init(self, iban, timedelta_days=1):

        to_date = date.today()
        while int(to_date.strftime('%w')) in [6, 0]:
            to_date = to_date - timedelta(days=1)
        if iban == '':
            from_date = self.mariadb.select_max_column_value(
                HOLDING, DB_price_date, period=(date(2000, 1, 1), to_date - timedelta(days=timedelta_days)))
        else:
            from_date = self.mariadb.select_max_column_value(
                HOLDING, DB_price_date, iban=iban, period=(date(2000, 1, 1), to_date - timedelta(days=timedelta_days)))
        if not from_date:
            return None, None
        while int(from_date.strftime('%w')) in [6, 0]:
            from_date = from_date - timedelta(days=1)
        if to_date < from_date:
            to_date = from_date
        return from_date, to_date

    def _data_holding_performance(self, bank_name, iban):

        self._delete_footer()
        _data_holding_performance = None
        from_date = date.today() - timedelta(days=360)
        to_date = date.today()
        title = ' '.join([bank_name, MENU_TEXT['Holding Performance']])
        while True:
            input_date = InputDate(title=title,
                                   from_date=from_date, to_date=to_date)
            if isinstance(_data_holding_performance, BuiltPandasBox):
                destroy_widget(_data_holding_performance.dataframe_window)
            if input_date.button_state == WM_DELETE_WINDOW:
                return
            from_date = input_date.field_dict[FN_FROM_DATE]
            to_date = input_date.field_dict[FN_TO_DATE]
            if bank_name == FN_ALL_BANKS:
                select_holding_total = self.mariadb.select_holding_all_total(
                    period=(from_date, to_date))
            else:
                select_holding_total = self.mariadb.select_holding_total(
                    iban=iban, period=(from_date, to_date))
            if select_holding_total:
                title_period = ' '.join([title, ' ',
                                         MESSAGE_TEXT['PERIOD'].format(from_date, to_date)])
                while True:
                    table = PandasBoxHoldingPortfolios(
                        title=title_period, dataframe=select_holding_total, mode=NUMERIC)
                    if table.button_state == WM_DELETE_WINDOW:
                        break
            else:
                self.footer.set(
                    MESSAGE_TEXT['DATA_NO'].format(bank_name, iban))

    def _data_holding_isin_comparision(self, bank_name, iban, sign):

        self._delete_footer()
        percent = ''
        if sign == PERCENT:
            percent = '%'
        from_date, to_date = self._date_init(iban, timedelta_days=90)
        title = ' '.join(
            [bank_name, MENU_TEXT['Holding ISIN Comparision'], percent])
        if iban:
            select_holding_all_isin = self.mariadb.select_dict(
                HOLDING_VIEW, DB_name, DB_ISIN, iban=iban)
        else:
            select_holding_all_isin = self.mariadb.select_dict(
                HOLDING_VIEW, DB_name, DB_ISIN, period=(from_date, to_date))
        if not select_holding_all_isin:
            MessageBoxInfo(title=title, message=(
                MESSAGE_TEXT['DATA_NO'].format('', '')))
            return
        default_texts = []

        while True:
            date_field_list = InputDateFieldlist(
                title=title,
                from_date=from_date, standard=title,
                default_texts=default_texts,
                field_list=list(select_holding_all_isin.keys()))
            if date_field_list.button_state == WM_DELETE_WINDOW:
                return
            default_texts = date_field_list.field_list
            from_date = date_field_list.field_dict[FN_FROM_DATE]
            to_date = date_field_list.field_dict[FN_TO_DATE]
            title1 = ' '.join([
                title, MESSAGE_TEXT['PERIOD'].format(from_date, to_date)])
            while True:
                selected_fields = BuiltRadioButtons(
                    title=title1,
                    button1_text=BUTTON_OK, button2_text=None,
                    button3_text=None, button4_text=None, button5_text=None,
                    default_value=None,
                    radiobutton_dict={DB_pieces: ' ',
                                      DB_market_price: ' ',
                                      DB_total_amount: ' ',
                                      DB_acquisition_amount: ' ',
                                      FN_PROFIT_LOSS: ' '}
                )
                if selected_fields.button_state == WM_DELETE_WINDOW:
                    break
                else:
                    db_field = selected_fields.field
                if db_field == FN_PROFIT_LOSS:
                    db_fields = [DB_name, DB_price_date,
                                 DB_total_amount, DB_acquisition_amount]
                else:
                    db_fields = [DB_name, DB_price_date, db_field]
                if iban:
                    select_holding_data = self.mariadb.select_holding_data(
                        field_list=db_fields, iban=iban, name=date_field_list.field_list,
                        period=(from_date, to_date))
                else:
                    select_holding_data = self.mariadb.select_holding_data(
                        field_list=db_fields, name=date_field_list.field_list, period=(from_date, to_date))
                if select_holding_data:
                    self.footer.set('')
                    title2 = ' '.join([title1, db_field.upper()])
                    while True:
                        table = PandasBoxIsins(title=title2, dataframe=(
                            db_field, select_holding_data, sign, date_field_list.field_list),
                            dataframe_typ=TYP_DECIMAL, mode=NUMERIC)
                        if table.button_state == WM_DELETE_WINDOW:
                            break
                else:
                    self.footer.set(
                        MESSAGE_TEXT['DATA_NO'].format(bank_name, iban))

    def _data_holding_table(self, bank_name, iban):

        self._delete_footer()
        title = ' '.join([bank_name,
                          MENU_TEXT['Holding Table']])
        from_date = date.today()
        to_date = date.today()
        while True:
            date_field_list = InputDateFieldlist(title=title,
                                                 from_date=from_date, to_date=to_date,
                                                 standard=MENU_TEXT['Holding Table'],
                                                 field_list=TABLE_FIELDS[HOLDING_VIEW][3:])
            if date_field_list.button_state == WM_DELETE_WINDOW:
                break
            from_date = date_field_list.field_dict[FN_FROM_DATE]
            to_date = date_field_list.field_dict[FN_TO_DATE]
            field_list = date_field_list.field_list
            message = None
            period = ' '.join([from_date, '-', to_date])
            title_period = ' '.join([title, period])
            while True:
                data = self.mariadb.select_table(
                    HOLDING_VIEW, [DB_iban, DB_price_date, DB_ISIN] + field_list, result_dict=True,
                    date_name=DB_price_date, iban=iban, period=(from_date, to_date))
                holding_table = PandasBoxHoldingTable(
                    title_period, data, self.mariadb, message, iban, mode=EDIT_ROW)
                message = holding_table.message
                if holding_table.button_state == WM_DELETE_WINDOW:
                    break
            else:
                self.footer.set(message)

    def _data_update_holding_prices(self, bank_name, iban):
        '''
        For a working day:
        Replaces market_price (table HOLDING) by close price (table PRICES)
        If not existing: creates holding positions 
        '''
        title = ' '.join([bank_name, 'holding_update_prices'])
        holdings = []
        date_day = date.today()
        input_date = InputDay(
            title=title, header=MESSAGE_TEXT['SELECT'], date=date_day)
        if input_date.button_state == WM_DELETE_WINDOW:
            return
        if input_date:
            date_day = input_date.field_dict[FN_DATE]
            while True:
                holdings = self.mariadb.select_table(
                    HOLDING_VIEW, '*', result_dict=True, iban=iban, price_date=date_day)
                if holdings:
                    for holding_dict in holdings:
                        title_download = ' '.join(
                            [title, MENU_TEXT['Download'], MENU_TEXT['Prices']])
                        result = self._data_update_holding_price(
                            title_download, bank_name, iban, holding_dict)
                        if not result:
                            isin = Isin(
                                title, self.mariadb, self.shelve_app[KEY_ALPHA_VANTAGE], isin_name=holding_dict[DB_name])
                            if isin.button_state == WM_DELETE_WINDOW:
                                result = False
                            if isin.button_state == MENU_TEXT['Prices']:
                                result = self._data_update_holding_price(
                                    title_download, bank_name, iban, holding_dict)
                            if not result:
                                origin_symbol = self.mariadb.select_table(
                                    ISIN, DB_origin_symbol, isin_code=holding_dict[DB_ISIN])
                                if origin_symbol:
                                    origin_symbol = origin_symbol[0]
                                else:
                                    origin_symbol = NOT_ASSIGNED
                                holding_informations_append(WARNING, MESSAGE_TEXT['PRICES_NO'].format(
                                    ' '.join(['\n', bank_name, HOLDING.upper(), DB_price_date.upper(
                                    ), date_days.convert(holding_dict[DB_price_date])]),
                                    holding_dict[DB_symbol], origin_symbol, holding_dict[DB_ISIN], holding_dict[DB_name]))
                    self._show_informations()
                    break
                else:
                    if date_days.isweekend(date_day):
                        MessageBoxInfo(
                            title=title, message=MESSAGE_TEXT['DATE_NO_WORKDAY'].format(date_day))
                        break
                    else:
                        period = (START_DATE_HOLDING, date_day)
                        message_box_ask = MessageBoxAsk(
                            title=title, message=MESSAGE_TEXT['HOLDING_INSERT'].format(date_day))
                        if message_box_ask.result:
                            holdings = self.mariadb.select_table_next(
                                HOLDING, '*', DB_price_date, '<', date_day,  result_dict=True, date_name=DB_price_date, iban=iban, period=period)
                            for holding_dict in holdings:
                                holding_dict[DB_price_date] = date_day
                                holding_dict[DB_origin] = ORIGIN_INSERTED
                                self.mariadb.execute_insert(
                                    HOLDING, holding_dict)
                                holding_informations_append(INFORMATION, ' '.join(['\n', bank_name, MESSAGE_TEXT['HOLDING_INSERT'].format(
                                    date_day), '\n', holding_dict[DB_ISIN], '\n']))
                        else:
                            MessageBoxInfo(title=title, message=MESSAGE_TEXT['DATA_NO'].format(
                                HOLDING.upper(), (date_days.convert(START_DATE_HOLDING), date_day)))
                            break
        if holdings:
            self.mariadb.update_total_holding_amount(
                iban=iban, period=(date_day, date_day))
        self._show_informations()

    def _data_update_holding_price(self, title, bank_name, iban, holding_dict):
        '''
        Imports prices
        Updates market_price, total_amount
        '''
        self._import_prices_run(self.mariadb, title, [
                                holding_dict[DB_name]], BUTTON_APPEND)
        price = self.mariadb.select_table(
            PRICES_ISIN_VIEW, DB_close, result_dict=True, isin_code=holding_dict[DB_ISIN], price_date=holding_dict[DB_price_date])
        if price:
            price_dict = price[0]
            field_dict = {}
            field_dict[DB_market_price] = price_dict[DB_close]
            field_dict[DB_total_amount] = dec2.multiply(
                field_dict[DB_market_price], holding_dict[DB_pieces])
            field_dict[DB_origin] = ORIGIN_PRICES
            self.mariadb.execute_update(
                HOLDING, field_dict, iban=iban, isin_code=holding_dict[DB_ISIN], price_date=holding_dict[DB_price_date])
            holding_informations_append(INFORMATION, ' '.join(['\n', bank_name, DB_ISIN.upper(), holding_dict[DB_ISIN], holding_dict[DB_name], '\n          ',
                                                               DB_price_date.upper(), date_days.convert(holding_dict[DB_price_date]), '\n']))
            return True
        else:
            return False

    def _data_transaction_detail(self, bank_name, iban):

        self._delete_footer()
        title = ' '.join([bank_name, MENU_TEXT['Transaction Detail']])
        Transaction = DataTransactionDetail(
            title=title, mariadb=self.mariadb, table=TRANSACTION_VIEW,
            bank_name=bank_name, iban=iban)
        self.footer.set(Transaction.footer)

    def _data_transaction_table(self, bank_name, iban):

        self._delete_footer()
        title = ' '.join([bank_name,
                          MENU_TEXT['Transactions Table']])
        field_list = TABLE_FIELDS[TRANSACTION_VIEW]
        from_date = date(2000, 1, 1)
        to_date = date(datetime.now().year, 12, 31)
        name_isin_dict = dict(self.mariadb.select_table(
            ISIN, [DB_name, DB_ISIN], order=DB_name))
        isin = ''
        name = ''
        while True:
            input_isin = InputISIN(title=title, default_values=(
                name, isin, from_date, to_date), names=name_isin_dict)
            if input_isin.button_state == WM_DELETE_WINDOW:
                return
            isin = input_isin.field_dict[DB_ISIN]
            name = input_isin.field_dict[DB_name]
            from_date = input_isin.field_dict[FN_FROM_DATE]
            to_date = input_isin.field_dict[FN_TO_DATE]
            title_period = ' '.join(
                [title, name, isin, from_date, '-', to_date])
            message = None
            while True:
                data = self.mariadb.select_table(
                    TRANSACTION_VIEW, field_list, result_dict=True, iban=iban, isin_code=isin, period=(from_date, to_date))
                transaction_table = PandasBoxTransactionTable(
                    title_period, data, self.mariadb, message, iban, isin, name, mode=EDIT_ROW)
                message = transaction_table.message
                if transaction_table.button_state == WM_DELETE_WINDOW:
                    break
                else:
                    self.footer.set(message)

    def _data_profit_delivery_negative(self, dict_):
        """ set delivery pieces negative """
        if dict_[DB_transaction_type] == TRANSACTION_DELIVERY:
            dict_[DB_pieces] = - dict_[DB_pieces]

        return dict_

    def _data_profit_pieces_cumulate(self, previous_dict, dict_):
        """ accumulate pieces"""
        dict_[FN_PIECES_CUM] = dict_[DB_pieces]
        dict_[FN_PIECES_CUM] = dict_[FN_PIECES_CUM] + \
            previous_dict[FN_PIECES_CUM]
        if dict_[FN_PIECES_CUM] < 0:
            MessageBoxInfo(message=MESSAGE_TEXT['TRANSACTION_PIECES_NEGATIVE'].format(
                dict_[DB_price_date]))
        return dict_

    def _data_prices(self, sign):

        self._delete_footer()
        if sign:
            title = MENU_TEXT['Prices ISINs'] + ' %'
        else:
            title = MENU_TEXT['Prices ISINs']
        select_isin_ticker = self.mariadb.select_isin_with_ticker(
            [DB_name, DB_symbol], order=DB_name)
        if not select_isin_ticker:
            MessageBoxInfo(title=title, message=(
                MESSAGE_TEXT['DATA_NO'].format(ISIN.upper(), DB_symbol.upper())))
            return
        name_symbol = dict(select_isin_ticker)
        from_date = START_DATE_PRICES
        to_date = date.today()
        default_texts = []
        default_texts_prices = shelve_get_key(BANK_MARIADB_INI, title + PRICES)
        if not default_texts_prices:
            default_texts_prices = []
        while True:
            date_field_list = InputDateFieldlistPrices(
                title=title,
                from_date=from_date, standard=None,
                default_texts=default_texts,
                field_list=list(name_symbol.keys()))
            if date_field_list.button_state == WM_DELETE_WINDOW:
                return
            if not date_field_list.field_list:
                self.footer.set(MESSAGE_TEXT['DATA_NO'].format(
                    ', '.join(date_field_list.field_list), ''))
                break
            # selected names e.g. Amazon, ...
            default_texts = date_field_list.field_list
            from_date = date_field_list.field_dict[FN_FROM_DATE]
            to_date = date_field_list.field_dict[FN_TO_DATE]
            if sign == PERCENT:
                symbol_list = list(map(name_symbol.get, default_texts))
                from_date = self.mariadb.select_first_price_date_of_prices(
                    symbol_list, period=(from_date, to_date))
                if not from_date:
                    self.footer.set(MESSAGE_TEXT['DATA_NO'].format(
                        ', '.join(date_field_list.field_list), ''))
                    break
            selected_fields = SelectFields(
                title=title, standard=title + PRICES,
                default_texts=default_texts_prices,
                checkbutton_texts=[DB_open, DB_low, DB_high, DB_close, DB_adjclose, DB_volume,
                                   DB_dividends, DB_splits])
            if selected_fields.button_state == WM_DELETE_WINDOW:
                break
            else:
                # selected data fields e.g. close, ..
                field_list = selected_fields.field_list
            db_fields = [DB_name, DB_price_date, *field_list]
            select_data = self.mariadb.select_table(PRICES_ISIN_VIEW, db_fields, order=DB_name, result_dict=True,
                                                    name=date_field_list.field_list, period=(from_date, to_date))
            select_origin_dict = dict(self.mariadb.select_table(
                ISIN, [DB_name, DB_origin_symbol], name=date_field_list.field_list))
            if select_data:
                self.footer.set('')
                while True:
                    price_table = PandasBoxPrices(title=title, dataframe=(
                        field_list, select_data, select_origin_dict, sign), dataframe_typ=TYP_DECIMAL, mode=NUMERIC)
                    if price_table.button_state == WM_DELETE_WINDOW:
                        break
            else:
                self.footer.set(
                    MESSAGE_TEXT['DATA_NO'].format(', '.join(date_field_list.field_list), ''))

    def _data_balances(self):

        self._delete_footer()
        to_date = date.today()
        from_date = date(2021, 10, 3)
        title = ' '.join(
            [MENU_TEXT['All_Banks'], MENU_TEXT['Balances']])
        while True:
            input_date = InputDate(title=title,
                                   header=MESSAGE_TEXT['SELECT'],
                                   from_date=from_date, to_date=to_date
                                   )
            if input_date.button_state == WM_DELETE_WINDOW:
                return input_date.button_state, None, None
            self.footer.set(MESSAGE_TEXT['TASK_STARTED'].format(title))
            from_date = input_date.field_dict[FN_FROM_DATE]
            to_date = input_date.field_dict[FN_TO_DATE]
            data_total_amounts = self.mariadb.select_total_amounts(
                period=(from_date, to_date))
            title_period = ' '.join([title, MESSAGE_TEXT['PERIOD'].format(
                from_date, to_date)])
            self.footer.set(MESSAGE_TEXT['TASK_DONE'])
            if data_total_amounts:
                while True:
                    table = PandasBoxTotals(
                        title=title_period, dataframe=data_total_amounts, mode=NUMERIC)
                    if table.button_state == WM_DELETE_WINDOW:
                        break
            else:
                MessageBoxInfo(title=title_period, message=(
                    MESSAGE_TEXT['DATA_NO'].format('', '')))

    def _import_bankidentifier(self):

        title = MENU_TEXT['Import Bankidentifier CSV-File']
        MessageBoxInfo(title=title, message=MESSAGE_TEXT['IMPORT_CSV'].format(
            BANKIDENTIFIER.upper()))
        webbrowser.open(BUNDESBANK_BLZ_MERKBLATT)
        webbrowser.open(BUNDEBANK_BLZ_DOWNLOAD)
        file_dialogue = FileDialogue(title=title)
        if file_dialogue.filename not in ['', None]:
            self.mariadb.import_bankidentifier(
                file_dialogue.filename)
            MessageBoxInfo(title=title,  message=MESSAGE_TEXT['LOAD_DATA'].format(
                file_dialogue.filename))
            data = self.mariadb.select_table(
                BANKIDENTIFIER, field_list=TABLE_FIELDS[BANKIDENTIFIER],  result_dict=True)
            dataframe = DataFrame(data)
            BuiltPandasBox(title=title, dataframe=dataframe)

    def _import_prices(self, isin_code=None):

        self._delete_footer()
        title = ' '.join([MENU_TEXT['Download'], MENU_TEXT['Prices']])
        select_isin_ticker = self.mariadb.select_isin_with_ticker(
            [DB_name], order=DB_name)
        if select_isin_ticker:
            select_isin_ticker = list(map(lambda x: x[0], select_isin_ticker))
            download_prices = None
            while True:
                select_isins = SelectDownloadPrices(
                    title=title, checkbutton_texts=select_isin_ticker)
                if select_isins.button_state == WM_DELETE_WINDOW:
                    self._show_informations()
                    return
                state = select_isins.button_state
                field_list = select_isins.field_list
                if self.shelve_app[KEY_THREADING] == TRUE:
                    download_prices = Thread(name=MENU_TEXT['Prices'], target=self._import_prices_run,
                                             args=(self.mariadb, title, field_list, state))
                    download_prices.start()
                else:
                    self._import_prices_run(
                        self.mariadb, title, field_list, state)
        else:
            self.footer.set(MESSAGE_TEXT['SYMBOL_MISSING_ALL'].format(title))

    def _import_prices_histclose(self):
        '''
        download of historical prices may contain adjusted close prices
        e.g. extra dividends, splits, ... are represented by multiplication with a factor (r-factor)
        Such close prices generate faulty total_amount of holding positions in the past  (table holding)
        To get the historical precise close prices in table holding close prices must be readjusted (see Isin table)
        '''
        self._delete_footer()
        names, names_symbol, names_adjustments = self.mariadb.select_isin_adjustments()
        title = ' '.join([MENU_TEXT['Historical Prices']])
        while True:
            select_isins = SelectDownloadPrices(
                title=title, checkbutton_texts=names,
                button1_text=BUTTON_UPDATE, button2_text=None, button3_text=None,)
            if select_isins.button_state == WM_DELETE_WINDOW:
                self._show_informations()
                return
            field_list = select_isins.field_list
            for name in field_list:
                self.mariadb.update_prices_histclose(
                    name, names_symbol[name], names_adjustments[name])

    def _import_prices_run(self, mariadb, title, field_list, state):

        for name in field_list:
            select_isin_data = self.mariadb.select_table(
                ISIN, [DB_ISIN, DB_symbol, DB_origin_symbol], name=name, result_dict=True)
            if select_isin_data:
                select_isin_data = select_isin_data[0]
                symbol = select_isin_data[DB_symbol]
                origin_symbol = select_isin_data[DB_origin_symbol]
                message_symbol = symbol + '/' + origin_symbol
                isin = select_isin_data[DB_ISIN]
                if state == BUTTON_DELETE:
                    self.mariadb.execute_delete(PRICES, symbol=symbol)
                    MessageBoxInfo(title=title, information_storage=Informations.PRICES_INFORMATIONS,
                                   message=MESSAGE_TEXT['PRICES_DELETED'].format(
                                       name, message_symbol, isin))
                else:
                    if symbol == NOT_ASSIGNED or origin_symbol == NOT_ASSIGNED:
                        MessageBoxInfo(title=title, information_storage=Informations.PRICES_INFORMATIONS, information=WARNING,
                                       message=MESSAGE_TEXT['SYMBOL_MISSING'].format(isin, name))
                    else:
                        from_date = date_days.convert(START_DATE_PRICES)
                        start_date_prices = from_date
                        if state == BUTTON_APPEND:
                            max_price_date = self.mariadb.select_max_column_value(
                                PRICES, DB_price_date, symbol=symbol)
                            if max_price_date:
                                from_date = max_price_date + timedelta(days=1)
                        if origin_symbol == YAHOO:
                            tickers = Ticker(symbol)
                            f = io.StringIO()
                            with redirect_stdout(f):
                                dataframe = tickers.history(auto_adjust=False,
                                                            period=None, start=from_date, end=date.today())
                            if f.getvalue():
                                prices_informations_append(
                                    INFORMATION, f.getvalue())
                            columns = {"Date": DB_price_date, 'Open': DB_open, 'High': DB_high,
                                       'Low': DB_low, 'Close': DB_close, 'Adj Close': DB_adjclose,
                                       'Dividends': DB_dividends, 'Stock Splits': DB_splits,
                                       'Volume': DB_volume}
                        elif origin_symbol == ALPHA_VANTAGE:
                            function = self.shelve_app[KEY_ALPHA_VANTAGE_PRICE_PERIOD]
                            '''
                            By default, outputsize=compact. Strings compact and full are accepted with the following specifications:
                            compact returns only the latest 100 data points;
                            full returns the full-length time series of 20+ years of historical data
                            '''
                            url = 'https://www.alphavantage.co/query?function=' + function + '&symbol=' + \
                                symbol + '&outputsize='
                            if from_date == start_date_prices:
                                url = url + OUTPUTSIZE_FULL + '&apikey=' + \
                                    self.shelve_app[KEY_ALPHA_VANTAGE]
                            else:
                                url = url + OUTPUTSIZE_COMPACT + '&apikey=' + \
                                    self.shelve_app[KEY_ALPHA_VANTAGE]
                            data = requests.get(url).json()
                            keys = [*data]  # list of keys of dictionary data
                            dataframe = None
                            if len(keys) == 2:
                                try:
                                    '''
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
                                    '''
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
                            self.mariadb.execute_delete(
                                PRICES, symbol=symbol, period=period)
                            if mariadb.import_prices(title, dataframe):
                                MessageBoxInfo(title=title, information_storage=Informations.PRICES_INFORMATIONS,
                                               message=MESSAGE_TEXT['PRICES_LOADED'].format(
                                                   name, period, message_symbol, isin))

    def _import_server(self):

        title = MENU_TEXT['Import Server CSV-File']
        MessageBoxInfo(title=title, message=MESSAGE_TEXT['IMPORT_CSV'].format(
            SERVER.upper()) + FINTS_SERVER)
        self._websites(FINTS_SERVER_ADDRESS)
        file_dialogue = FileDialogue(title=title)
        if file_dialogue.filename not in ['', None]:
            self.mariadb.import_server(
                file_dialogue.filename)
            MessageBoxInfo(title=title, message=MESSAGE_TEXT['LOAD_DATA'].format(
                file_dialogue.filename))
            data = self.mariadb.select_table(
                SERVER, field_list=TABLE_FIELDS[SERVER],  result_dict=True)
            dataframe = DataFrame(data)
            BuiltPandasBox(title=title, dataframe=dataframe)

    def _import_transaction(self, bank_name, iban):
        """
        import transactions from CSV_File.
        CSV File Columns ((price_date, ISIN, name, pieces, transaction_type, price)
        price_date: YYYY-MM-DD
        decimals: decimal_point
        """
        title = MENU_TEXT['Import Transactions']
        _text = ("\n\nStructure of CSV_File: \n"
                 "\nColumns: \n price_date, ISIN, name, pieces, price\n"
                 "\n         PriceDate Format: YYYY-MM-DD"
                 "\n         Pieces and Price DecimalPoint"
                 "\n         Pieces NEGATIVE for Deliveries \n"
                 "\nHeader_line will be ignored"
                 )
        MessageBoxInfo(title=title, message=' '.join(
            [bank_name, MESSAGE_TEXT['IMPORT_CSV'].format(TRANSACTION.upper()), _text]))
        file_dialogue = FileDialogue(title=title)
        if file_dialogue.filename not in ['', None]:
            self.mariadb.import_transaction(iban, file_dialogue.filename)
            MessageBoxInfo(title=title, message=MESSAGE_TEXT['LOAD_DATA'].format(
                file_dialogue.filename))
            data = self.mariadb.select_table(
                TRANSACTION, field_list=TABLE_FIELDS[TRANSACTION],  result_dict=True)
            dataframe = DataFrame(data)
            BuiltPandasBox(title=title, dataframe=dataframe)

    def _isin_table(self):

        self._delete_footer()
        isin_name = ''
        title = ' '.join([MENU_TEXT['Database'], MENU_TEXT['ISIN Table']])
        while True:
            self._show_informations()
            isin = Isin(title, self.mariadb,
                        self.shelve_app[KEY_ALPHA_VANTAGE], isin_name=isin_name)
            if isin.button_state == WM_DELETE_WINDOW:
                self._show_informations()
                return
            if isin.button_state == MENU_TEXT['Prices']:
                title_prices = ' '.join(
                    [MENU_TEXT['Download'], MENU_TEXT['Prices'], isin.field_dict[DB_name]])
                self._import_prices_run(
                    self.mariadb, title_prices, [isin.field_dict[DB_name]], BUTTON_APPEND)
            if isin.button_state == FORMS_TEXT['Adjust Prices']:
                while True:
                    adjustments = Adjustments(
                        self.mariadb, isin.field_dict[DB_ISIN])
                    if adjustments.button_state == WM_DELETE_WINDOW:
                        break
            if isin.field_dict:
                isin_name = isin.field_dict[DB_name]

    def sepa_credit_transfer(self, bank_code, account):

        self._delete_footer()
        bank = self._bank_init(bank_code)
        label = account[KEY_ACC_PRODUCT_NAME]
        if not label:
            label = account[KEY_ACC_ACCOUNT_NUMBER]
        bank_name = self._bank_name(bank_code)
        title = ' '.join(
            [MENU_TEXT['Transfer'], bank_name, label])
        bank.account_number = account[KEY_ACC_ACCOUNT_NUMBER]
        bank.iban = account[KEY_ACC_IBAN]
        bank.subaccount_number = account[KEY_ACC_SUBACCOUNT_NUMBER]
        sepa_credit_box = SepaCreditBox(
            bank, self.mariadb, account, title=title)
        if sepa_credit_box.button_state == WM_DELETE_WINDOW:
            return
        transfer_data = {}
        account_data = dictaccount(bank_code,
                                   bank.account_number)
        transfer_data[SEPA_CREDITOR_NAME] = sepa_credit_box.field_dict[SEPA_CREDITOR_NAME]
        transfer_data[SEPA_CREDITOR_IBAN] = sepa_credit_box.field_dict[SEPA_CREDITOR_IBAN].upper()
        transfer_data[SEPA_CREDITOR_BIC] = sepa_credit_box.field_dict[SEPA_CREDITOR_BIC].upper()
        transfer_data[SEPA_AMOUNT] = sepa_credit_box.field_dict[SEPA_AMOUNT].replace(
            ',', '.')
        transfer_data[SEPA_PURPOSE] = sepa_credit_box.field_dict[
            SEPA_PURPOSE_1] + ' ' + sepa_credit_box.field_dict[SEPA_PURPOSE_2]
        transfer_data[SEPA_REFERENCE] = sepa_credit_box.field_dict[SEPA_REFERENCE]
        if 'HKCSE' in account[KEY_ACC_ALLOWED_TRANSACTIONS]:
            if sepa_credit_box.field_dict[SEPA_EXECUTION_DATE] == str(date.today()):
                transfer_data[SEPA_EXECUTION_DATE] = TRANSFER_DATA_SEPA_EXECUTION_DATE
            else:
                transfer_data[SEPA_EXECUTION_DATE] = sepa_credit_box.field_dict[SEPA_EXECUTION_DATE]
        else:
            transfer_data[SEPA_EXECUTION_DATE] = TRANSFER_DATA_SEPA_EXECUTION_DATE
        SepaCreditTransfer(bank, account_data, transfer_data)
        if transfer_data[SEPA_EXECUTION_DATE] == TRANSFER_DATA_SEPA_EXECUTION_DATE:
            bank.dialogs.transfer(bank)
        else:
            bank.dialogs.date_transfer(bank)
        self._show_message(bank)

    def _bank_security_function(self, bank_code, new):

        self._delete_footer()
        bank = InitBankAnonymous(bank_code, self.mariadb)
        bank.dialogs.anonymous(bank)
        security_function_dict = {}
        default_value = None
        for twostep in bank.twostep_parameters:
            security_function, security_function_name = twostep
            security_function_dict[security_function] = security_function_name
            if (shelve_get_key(bank_code, KEY_SECURITY_FUNCTION) and shelve_get_key(
                    bank_code, KEY_SECURITY_FUNCTION)[0:3] == security_function[0:3]):
                default_value = security_function
        bank_name = self._bank_name(bank.bank_code)
        title = ' '.join([bank_name, MENU_TEXT['Customize'],
                          MENU_TEXT['Change Security Function']])
        if new:
            security_function_box = BuiltRadioButtons(
                title=title,
                header=MESSAGE_TEXT['TWOSTEP'], default_value=default_value,
                button2_text=None, radiobutton_dict=security_function_dict)
        else:
            security_function_box = BuiltRadioButtons(
                title=title,
                header=MESSAGE_TEXT['TWOSTEP'], default_value=default_value,
                radiobutton_dict=security_function_dict)
        if security_function_box.button_state == WM_DELETE_WINDOW:
            return
        if security_function_box.button_state == BUTTON_SAVE:
            data = (KEY_SECURITY_FUNCTION, security_function_box.field[0:3])
            shelve_put_key(bank_code, data)
        self.footer.set(MESSAGE_TEXT['SYNC_START'].format(bank_name))

    def _reset(self):

        if shelve_exist(BANK_MARIADB_INI):
            GEOMETRY_DICT = {}
            shelve_put_key(BANK_MARIADB_INI, (KEY_GEOMETRY, GEOMETRY_DICT))
        self.footer.set(MESSAGE_TEXT['TASK_DONE'])

    def _show_alpha_vantage(self):

        self._delete_footer()
        title = MENU_TEXT['Alpha Vantage']
        alpha_vantage_symbols = self.mariadb.select_dict(
            ISIN, DB_name, DB_symbol, origin_symbol=ALPHA_VANTAGE)
        alpha_vantage_names = list(alpha_vantage_symbols.keys())
        field_list = []
        while True:
            checkbutton = SelectFields(
                title=title,
                button2_text=None, button3_text=None, button4_text=None, default_texts=field_list,
                checkbutton_texts=self.alpha_vantage.function_list)
            if checkbutton.button_state == WM_DELETE_WINDOW:
                return
            field_list = checkbutton.field_list
            dataframe = None
            for function in checkbutton.field_list:
                default_values = []
                while True:
                    title_function = ' '.join([title, function])
                    parameters = AlphaVantageParameter(
                        title_function, function, self.shelve_app[KEY_ALPHA_VANTAGE],
                        self.alpha_vantage.parameter_dict[function], default_values,
                        alpha_vantage_names)
                    if parameters.button_state == WM_DELETE_WINDOW:
                        break
                    elif parameters.button_state == MENU_TEXT['ISIN Table']:
                        self._isin_table()
                        return
                    elif parameters.button_state == BUTTON_ALPHA_VANTAGE:
                        self._websites(ALPHA_VANTAGE_DOCUMENTATION)
                    else:
                        default_values = list(parameters.field_dict.values())
                        url = 'https://www.alphavantage.co/query?function=' + function
                        for key, value in parameters.field_dict.items():
                            if value:
                                if key.lower() == DB_symbol:
                                    value = alpha_vantage_symbols[value]
                                api_parameter = ''.join(
                                    ['&', key.lower(), '=', value])
                                url = url + api_parameter
                        try:
                            data_json = requests.get(url).json()
                        except Exception:
                            exception_error(
                                message=MESSAGE_TEXT['ALPHA_VANTAGE_ERROR'])
                            break
                        key_list = list(data_json.keys())
                        if JSON_KEY_META_DATA in data_json.keys():
                            if isinstance(dataframe, DataFrame):
                                dataframe_next = DataFrame(
                                    data_json[key_list[1]]).T
                                dataframe = dataframe.join(dataframe_next)
                            else:
                                dataframe = DataFrame(
                                    data_json[key_list[1]]).T
                        elif JSON_KEY_ERROR_MESSAGE in data_json.keys():
                            MessageBoxInfo(title=title_function, message=MESSAGE_TEXT[
                                'ALPHA_VANTAGE_ERROR_MSG'].format(data_json[JSON_KEY_ERROR_MESSAGE], url))
                        elif data_json == {}:
                            MessageBoxInfo(title=title_function, message=MESSAGE_TEXT[
                                'ALPHA_VANTAGE_NO_DATA'].format(url))
                        else:
                            self._websites(url)
                        break
            if isinstance(dataframe, DataFrame):
                title_function = ' '.join([title_function, url])
                while True:
                    table = BuiltPandasBox(
                        title=title_function, dataframe=dataframe, mode=NO_CURRENCY_SIGN)
                    if table.button_state == WM_DELETE_WINDOW:
                        break

    def _show_alpha_vantage_search_symbol(self):

        function = 'SYMBOL_SEARCH'
        title = MENU_TEXT['Alpha Vantage Symbol Search']
        while True:
            parameters = AlphaVantageParameter(
                title, function, self.shelve_app[KEY_ALPHA_VANTAGE],
                self.alpha_vantage.parameter_dict[function], [], [])
            if parameters.button_state == WM_DELETE_WINDOW:
                break
            elif parameters.button_state == MENU_TEXT['ISIN Table']:
                self._isin_table()
            elif parameters.button_state == BUTTON_ALPHA_VANTAGE:
                self._websites(ALPHA_VANTAGE_DOCUMENTATION)
            else:
                url = 'https://www.alphavantage.co/query?function=' + function
                for key, value in parameters.field_dict.items():
                    if value:
                        api_parameter = ''.join(
                            ['&', key.lower(), '=', value])
                        url = url + api_parameter
                try:
                    data_json = requests.get(url).json()
                except Exception:
                    exception_error(
                        message=MESSAGE_TEXT['ALPHA_VANTAGE_ERROR'])
                    break
                if JSON_KEY_ERROR_MESSAGE in data_json.keys():
                    MessageBoxInfo(title=title, message=MESSAGE_TEXT[
                        'ALPHA_VANTAGE_ERROR_MSG'].format(data_json[JSON_KEY_ERROR_MESSAGE], url))
                elif data_json == {}:
                    MessageBoxInfo(title=title, message=MESSAGE_TEXT[
                        'ALPHA_VANTAGE_NO_DATA'].format(url))
                else:
                    self._websites(url)

    def _show_balances_all_banks(self):

        self._delete_footer()
        title = ' '.join([MENU_TEXT['Show'], MENU_TEXT['Balances']])
        message = title
        total_df = []
        if self.bank_names != {}:
            for bank_name in self.bank_names.values():
                message = message + '\n' + bank_name
                bank_code = dict_get_first_key(self.bank_names, bank_name)
                bank_balances = self._show_balances_get(
                    bank_code, owner_name=None)
                if bank_balances:
                    dataframe = DataFrame(bank_balances, columns=[KEY_ACC_BANK_CODE, KEY_ACC_ACCOUNT_NUMBER,
                                                                  KEY_ACC_PRODUCT_NAME, DB_entry_date,
                                                                  DB_closing_status, DB_closing_balance, DB_closing_currency,
                                                                  DB_opening_status, DB_opening_balance, DB_opening_currency])
                    total_df.append(dataframe)
            if total_df:
                PandasBoxBalancesAllBanks(
                    title=title, dataframe=total_df, mode=CURRENCY_SIGN, cellwidth_resizeable=False)
            else:
                self.footer.set(
                    ' '.join([message, MESSAGE_TEXT['DATA_NO'].format('', '')]))

    def _show_balances(self, bank_code, bank_name, owner_name=None):

        self._delete_footer()
        title = ' '.join([bank_name, MENU_TEXT['Show'], MENU_TEXT['Balances']])
        bank_balances = self._show_balances_get(
            bank_code, owner_name=owner_name)
        if bank_balances:
            if owner_name:
                title = ' '.join([title, owner_name])
            dataframe = DataFrame(bank_balances, columns=[KEY_ACC_BANK_CODE, KEY_ACC_ACCOUNT_NUMBER,
                                                          KEY_ACC_PRODUCT_NAME, DB_entry_date,
                                                          DB_closing_status, DB_closing_balance, DB_closing_currency,
                                                          DB_opening_status, DB_opening_balance, DB_opening_currency])
            # ignore F_keys because Columns  dropped in PandasBoxBalances
            PandasBoxBalances(title=title, dataframe=dataframe, dataframe_sum=[
                              DB_closing_balance, DB_opening_balance], mode=CURRENCY_SIGN,
                              cellwidth_resizeable=False)
        else:
            self.footer.set(MESSAGE_TEXT['DATA_NO'].format(title, ''))

    def _show_balances_get(self, bank_code, owner_name=None):

        if bank_code in self.bank_owner_account and owner_name:
            accounts = self.bank_owner_account[bank_code][owner_name]
        else:
            accounts = shelve_get_key(bank_code, KEY_ACCOUNTS)
        balances = []
        if accounts:
            for acc in accounts:
                iban = acc[KEY_ACC_IBAN]
                max_entry_date = self.mariadb.select_max_column_value(
                    STATEMENT, DB_entry_date, iban=iban)
                if max_entry_date:
                    fields = [DB_counter,
                              DB_closing_status, DB_closing_balance, DB_closing_currency, DB_closing_entry_date,
                              DB_opening_status, DB_opening_balance, DB_opening_currency, DB_opening_entry_date]
                    balance = self.mariadb.select_table(
                        STATEMENT, fields, result_dict=True, date_name=DB_date, iban=iban, entry_date=max_entry_date, order=DB_counter)
                    if balance:
                        # STATEMENT Account
                        current_date = date.today()
                        # Monday is 0 and Sunday is 6
                        if date.weekday(current_date) == 5:
                            current_date = current_date - timedelta(1)
                        # Monday is 0 and Sunday is 6
                        elif date.weekday(current_date) == 6:
                            current_date = current_date - timedelta(2)
                        if balance[-1][DB_closing_entry_date] == current_date:
                            balances.append(Balance(bank_code,
                                                    acc[KEY_ACC_ACCOUNT_NUMBER],
                                                    acc[KEY_ACC_PRODUCT_NAME],
                                                    max_entry_date,
                                                    balance[-1][DB_closing_status],
                                                    balance[-1][DB_closing_balance],
                                                    balance[-1][DB_closing_currency],
                                                    balance[0][DB_opening_status],
                                                    balance[0][DB_opening_balance],
                                                    balance[0][DB_opening_currency],
                                                    ))
                        else:
                            balances.append(Balance(bank_code,
                                                    acc[KEY_ACC_ACCOUNT_NUMBER],
                                                    acc[KEY_ACC_PRODUCT_NAME],
                                                    max_entry_date,
                                                    balance[-1][DB_closing_status],
                                                    balance[-1][DB_closing_balance],
                                                    balance[-1][DB_closing_currency],
                                                    balance[-1][DB_closing_status],
                                                    balance[-1][DB_closing_balance],
                                                    balance[-1][DB_closing_currency],
                                                    ))

                else:
                    # HOLDING Account
                    max_price_date = self.mariadb.select_max_column_value(
                        HOLDING, DB_price_date, iban=iban)
                    if max_price_date:

                        fields = [DB_total_amount_portfolio,
                                  DB_amount_currency]
                        balance = self.mariadb.select_table(
                            HOLDING, fields, result_dict=True, iban=iban, price_date=max_price_date)
                        if balance:
                            # HOLDING Account contains only 1 record per day
                            balance = balance[0]
                            # HOLDING previous entry
                            clause = ' ' + DB_price_date + ' < ' + \
                                '"' + max_price_date.strftime("%Y-%m-%d") + '"'
                            max_price_date_previous = self.mariadb.select_max_column_value(
                                HOLDING, DB_price_date, iban=iban, clause=clause)
                            balance_previous = self.mariadb.select_table(
                                HOLDING, fields, result_dict=True, iban=iban, price_date=max_price_date_previous)
                            if balance_previous:
                                balance_previous = balance_previous[0]
                            else:
                                balance_previous = balance
                            balances.append(Balance(bank_code,
                                                    acc[KEY_ACC_ACCOUNT_NUMBER],
                                                    acc[KEY_ACC_PRODUCT_NAME],
                                                    max_price_date,
                                                    '',
                                                    balance[DB_total_amount_portfolio],
                                                    balance[DB_amount_currency],
                                                    '',
                                                    balance_previous[DB_total_amount_portfolio],
                                                    balance_previous[DB_amount_currency]
                                                    ))
        return balances

    def _show_statements(self, bank_code, account):

        self._delete_footer()
        iban = account[KEY_ACC_IBAN]
        label = account[KEY_ACC_PRODUCT_NAME]
        if not label:
            label = account[KEY_ACC_ACCOUNT_NUMBER]
        bank_name = self._bank_name(bank_code)
        title = ' '.join([MENU_TEXT['Show'], bank_name,
                          MENU_TEXT['Statement'], label])
        field_list = TABLE_FIELDS[STATEMENT]
        from_date = date(datetime.now().year, 1, 1)
        to_date = date(datetime.now().year, 12, 31)
        while True:
            date_field_list = InputDateFieldlist(title=title,
                                                 from_date=date.today() - timedelta(days=30),
                                                 standard=MENU_TEXT['Show'] +
                                                 MENU_TEXT['Statement'],
                                                 field_list=TABLE_FIELDS[STATEMENT])
            if date_field_list.button_state == WM_DELETE_WINDOW:
                break
            from_date = date_field_list.field_dict[FN_FROM_DATE]
            to_date = date_field_list.field_dict[FN_TO_DATE]
            field_list = date_field_list.field_list
            for field in [DB_iban, DB_entry_date, DB_counter]:
                if field not in field_list:
                    field_list.append(field)
            message = None
            period = ' '.join([from_date, '-', to_date])
            title_period = ' '.join([title, period])
            data = self.mariadb.select_table(
                STATEMENT, field_list, result_dict=True,
                date_name=DB_date, iban=iban, period=(from_date, to_date))
            if data:
                while True:
                    table = PandasBoxStatementTable(
                        title_period, data, self.mariadb, message, mode=EDIT_ROW)
                    message = table.message
                    if table.button_state == WM_DELETE_WINDOW:
                        break
            else:
                self.footer.set(
                    MESSAGE_TEXT['DATA_NO'].format(title, period))
                break

    def _show_transactions(self, bank_code, account):

        self._delete_footer()
        iban = account[KEY_ACC_IBAN]
        field_list = TABLE_FIELDS[TRANSACTION_VIEW]
        from_date = date(2000, 1, 1)
        to_date = date.today()
        label = account[KEY_ACC_PRODUCT_NAME]
        if not label:
            label = account[KEY_ACC_ACCOUNT_NUMBER]
        bank_name = self._bank_name(bank_code)
        default_texts = []
        title = ' '.join(
            [MENU_TEXT['Show'], bank_name, MENU_TEXT['Holding'], label, TRANSACTION.upper()])
        while True:
            date_field_list = InputDateFieldlist(title=title,
                                                 from_date=from_date, to_date=to_date,
                                                 default_texts=default_texts,
                                                 standard=MENU_TEXT['Prices ISINs'], field_list=field_list)
            if date_field_list.button_state == WM_DELETE_WINDOW:
                return
            default_texts = date_field_list.field_list
            from_date = date_field_list.field_dict[FN_FROM_DATE]
            to_date = date_field_list.field_dict[FN_TO_DATE]
            data_list = self.mariadb.select_table(
                TRANSACTION_VIEW, date_field_list.field_list, result_dict=True, date_name=DB_price_date,
                iban=iban, period=(from_date, to_date))

            title_period = ' '.join(
                [title, MESSAGE_TEXT['PERIOD'].format(from_date, to_date)])
            if data_list:
                dataframe_sum = []
                if DB_posted_amount in date_field_list.field_list:
                    dataframe_sum.append(DB_posted_amount)
                if DB_acquisition_amount in date_field_list.field_list:
                    dataframe_sum.append(DB_acquisition_amount)
                while True:
                    table = PandasBoxHoldingTransaction(
                        title=title_period, dataframe=data_list, dataframe_sum=dataframe_sum, mode=NO_CURRENCY_SIGN)
                    if table.button_state == WM_DELETE_WINDOW:
                        break
            else:
                self.footer.set(
                    MESSAGE_TEXT['DATA_NO'].format(title_period, ''))

    def _show_holdings(self, bank_code, account):

        self._delete_footer()
        iban = account[KEY_ACC_IBAN]
        field_list = TABLE_FIELDS[HOLDING_VIEW]

        label = account[KEY_ACC_PRODUCT_NAME]
        if not label:
            label = account[KEY_ACC_ACCOUNT_NUMBER]
        bank_name = self._bank_name(bank_code)
        title = ' '.join(
            [MENU_TEXT['Show'], bank_name, MENU_TEXT['Holding'], label])
        max_price_date, _ = self._date_init(iban, timedelta_days=0)
        if not max_price_date:
            self.footer.set(MESSAGE_TEXT['DATA_NO'].format(title, ''))
            return
        date_ = max_price_date
        default_texts = []
        while True:
            date_field_list = InputDateFieldlistHolding(title=title, date=date_,
                                                        field_list=field_list,
                                                        default_texts=default_texts,
                                                        mariadb=self.mariadb, iban=iban)
            if date_field_list.button_state == WM_DELETE_WINDOW:
                return
            default_texts = date_field_list.field_list
            date_ = date_field_list.field_dict[FN_DATE]
            data_date_ = self.mariadb.select_holding_data(
                field_list=date_field_list.field_list, iban=iban, price_date=date_)
            if data_date_:
                data_list = sorted(data_date_,
                                   key=lambda i: (i[DB_name]))
                title_period = ' '.join(
                    [title, date_])
                while True:
                    table = PandasBoxHolding(title=title_period, dataframe=(data_list, date_field_list.field_list), dataframe_sum=[
                                             DB_total_amount, DB_acquisition_amount, FN_PROFIT], mode=NO_CURRENCY_SIGN,
                                             cellwidth_resizeable=False)
                    if table.button_state == WM_DELETE_WINDOW:
                        break

    def _show_holdings_perc(self, bank_code, account):

        self._delete_footer()
        iban = account[KEY_ACC_IBAN]
        label = account[KEY_ACC_PRODUCT_NAME]
        if not label:
            label = account[KEY_ACC_ACCOUNT_NUMBER]
        bank_name = self._bank_name(bank_code)
        title = ' '.join(
            [MENU_TEXT['Show'], bank_name, MENU_TEXT['Holding'] + '%', label])
        from_date = (date.today() - timedelta(days=1))
        to_date = date.today()
        while True:
            input_date = InputDateHoldingPerc(title=title, from_date=from_date,
                                              to_date=to_date,
                                              mariadb=self.mariadb, iban=iban)
            if input_date.button_state == WM_DELETE_WINDOW:
                return
            from_date = input_date.field_dict[FN_FROM_DATE]
            data_from_date = self.mariadb.select_holding_data(
                iban=iban, price_date=from_date)
            to_date = input_date.field_dict[FN_TO_DATE]
            data_to_date = self.mariadb.select_holding_data(
                iban=iban, price_date=to_date)
            title_period = ' '.join(
                [title, MESSAGE_TEXT['PERIOD'].format(from_date, to_date)])
            while True:
                table = PandasBoxHoldingPercent(title=title_period, dataframe=(
                    data_to_date, data_from_date), mode=CURRENCY_SIGN,
                    cellwidth_resizeable=False)
                if table.button_state == WM_DELETE_WINDOW:
                    break

    def _transactions_pieces(self, bank_name, iban):

        self._delete_footer()
        from_date = date(2000, 1, 1)
        to_date = date.today()
        title = ' '.join([bank_name, MENU_TEXT['Check Transactions Pieces']])
        while True:
            input_date = InputDate(title=title, header=MESSAGE_TEXT['SELECT'],
                                   from_date=from_date, to_date=to_date)
            if input_date.button_state == WM_DELETE_WINDOW:
                return
            from_date = input_date.field_dict[FN_FROM_DATE]
            to_date = input_date.field_dict[FN_TO_DATE]
            result = self.mariadb.transaction_portfolio(
                iban=iban, period=(from_date, to_date))
            if result:
                dataframe = DataFrame(list(result), columns=['ORIGIN',
                                                             DB_ISIN, DB_name, DB_pieces])
                title = title + MESSAGE_TEXT['TRANSACTION_PIECES_PORTFOLIO']
                while True:
                    table = BuiltPandasBox(
                        dataframe=dataframe, title=title, cellwidth_resizeable=False)
                    if table.button_state == WM_DELETE_WINDOW:
                        break
            else:
                MessageBoxInfo(title=title,
                               message=MESSAGE_TEXT['TRANSACTION_CHECK'].format('NO '))

    def _transactions_profit(self, bank_name, iban):

        self._delete_footer()
        from_date = date(2000, 1, 1)
        to_date = date.today()
        title = ' '.join(
            [bank_name, MENU_TEXT['Profit of closed Transactions']])
        while True:
            input_date = InputDate(title=title,
                                   header=MESSAGE_TEXT['SELECT'],
                                   from_date=from_date, to_date=to_date)
            if input_date.button_state == WM_DELETE_WINDOW:
                return
            from_date = input_date.field_dict[FN_FROM_DATE]
            to_date = input_date.field_dict[FN_TO_DATE]
            self._transactions_profit_closed(title, iban, from_date, to_date)

    def _transactions_profit_closed(self, title, iban, from_date, to_date):

        self._delete_footer()
        result = self.mariadb.transaction_profit_closed(
            iban=iban, period=(from_date, to_date))
        if result:
            title_period = ' '.join(
                [title, MESSAGE_TEXT['PERIOD'].format(from_date, to_date)])
            while True:
                table = PandasBoxTransactionProfit(
                    title=title_period, dataframe=list(result), mode=NO_CURRENCY_SIGN,
                    cellwidth_resizeable=False)
                if table.button_state == WM_DELETE_WINDOW:
                    break

        else:
            MessageBoxInfo(title=title,
                           message=MESSAGE_TEXT['TRANSACTION_CLOSED_EMPTY'].format(from_date, to_date))

    def _transactions_profit_all(self, bank_name, iban):

        self._delete_footer()
        from_date = date(2000, 1, 1)
        to_date = date.today()
        title = ' '.join(
            [bank_name, MENU_TEXT['Profit Transactions incl. current Depot Positions']])
        while True:
            input_date = InputDate(title=title,
                                   header=MESSAGE_TEXT['SELECT'],
                                   from_date=from_date, to_date=to_date, cellwidth_resizeable=False)
            if input_date.button_state == WM_DELETE_WINDOW:
                return
            from_date = input_date.field_dict[FN_FROM_DATE]
            to_date = input_date.field_dict[FN_TO_DATE]
            result = self.mariadb.transaction_profit_all(
                iban=iban, period=(from_date, to_date))
            if result:
                title_period = ' '.join(
                    [title, MESSAGE_TEXT['PERIOD'].format(from_date, to_date)])
                while True:
                    table = PandasBoxTransactionProfit(
                        title=title_period, dataframe=list(result), mode=NO_CURRENCY_SIGN,
                        cellwidth_resizeable=False)
                    if table.button_state == WM_DELETE_WINDOW:
                        break
            else:
                MessageBoxInfo(title=title,
                               message=MESSAGE_TEXT['TRANSACTION_NO'].format(from_date, to_date))
                self._transactions_profit_closed(
                    bank_name, iban, from_date, to_date)

    def _transactions_table(self, bank_name, iban):

        self._delete_footer()
        title = ' '.join([bank_name, MENU_TEXT['Transactions Table']])
        field_list = TABLE_FIELDS[TRANSACTION_VIEW]
        from_date = date(2000, 1, 1)
        to_date = date(datetime.now().year, 12, 31)
        period = (from_date, to_date)
        name_isin_dict = dict(self.mariadb.select_table(
            ISIN, [DB_name, DB_ISIN], order=DB_name))
        isin = ''
        name = ''
        while True:
            input_isin = InputISIN(
                title=MESSAGE_TEXT['TRANSACTION_TITLE'].format(bank_name, ''),
                default_values=(name, isin, from_date, to_date),
                names=name_isin_dict)
            if input_isin.button_state == WM_DELETE_WINDOW:
                return
            isin = input_isin.field_dict[DB_ISIN]
            name = input_isin.field_dict[DB_name]
            from_date = input_isin.field_dict[FN_FROM_DATE]
            to_date = input_isin.field_dict[FN_TO_DATE]
            _title = ' '.join([name, isin, from_date, '-', to_date])
            while True:
                data = self.mariadb.select_table(TRANSACTION_VIEW, field_list, order=[
                                                 DB_price_date, DB_counter], result_dict=True, iban=iban, isin_code=isin)
                if data:
                    transaction_table = PandasBoxTransactionTable(
                        title + _title, '', bank_name, iban, isin, name, period, data, self.mariadb, mode=EDIT_ROW)

                    if transaction_table.button_state == WM_DELETE_WINDOW:
                        return
                else:
                    self.footer.set(
                        MESSAGE_TEXT['DATA_NO'].format(title, _title))
                    break

    def _update_holding_total_amount_portfolio(self, bank_name, iban):
        """
        Update Table holding total_amount_portfolio
        """
        title = ' '.join(
            [bank_name, iban, MENU_TEXT['Update Portfolio Total Amount']])
        from_date = date.today()
        to_date = date.today()
        while True:
            input_date = InputDate(
                title=title, from_date=from_date, to_date=to_date)
            if input_date.button_state == WM_DELETE_WINDOW:
                return
            from_date = input_date.field_dict[FN_FROM_DATE]
            to_date = input_date.field_dict[FN_TO_DATE]
            period = (from_date, to_date)
            self.mariadb.update_total_holding_amount(iban=iban, period=period)
            self.footer.set(' '.join(
                [MESSAGE_TEXT['TASK_DONE'],  "\n", MENU_TEXT['Update Portfolio Total Amount'],
                 "\n", bank_name, iban,   MESSAGE_TEXT['PERIOD'].format(from_date, to_date)])
            )

    def _websites(self, site):

        webbrowser.open(site)

    '''
    Ledger Methods
    '''

    def _ledger_balances(self):
        '''
        Show ledger balances
            date referred to entry_date field in Ledger
        '''
        self._delete_footer()
        title = ' '.join([MENU_TEXT['Ledger'],
                         MENU_TEXT['Balances']])
        input_date = InputDate(title=title, from_date=date(
            date.today().year, 1, 1), to_date=date(date.today().year, 12, 31))
        if input_date.button_state == WM_DELETE_WINDOW:
            return
        from_date = input_date.field_dict[FN_FROM_DATE]
        to_date = input_date.field_dict[FN_TO_DATE]
        ledger_coa = self.mariadb.select_table(
            LEDGER_COA, [DB_account, DB_name, DB_iban, DB_portfolio], order=DB_account, result_dict=True)
        data = self._ledger_balance_table(from_date, to_date, ledger_coa)
        if data:
            title = ' '.join(
                [title, MESSAGE_TEXT['PERIOD'].format(from_date, to_date)])
            BuiltPandasBox(title=title, dataframe=DataFrame(
                data), mode=NO_CURRENCY_SIGN, cellwidth_resizeable=False)
        else:
            self.footer.set(MESSAGE_TEXT['DATA_NO'].format(title, ''))

    def _ledger_assets(self):
        '''
        Show ledger assets
            date referred to entry_date field in Ledger
        '''
        self._delete_footer()
        title = ' '.join([MENU_TEXT['Ledger'],
                         MENU_TEXT['Assets']])
        ledger_coa = self.mariadb.select_table(
            LEDGER_COA, [DB_account, DB_name, DB_iban, DB_portfolio], order=DB_account, result_dict=True, asset_accounting=True)
        from_date = date(datetime.now().year, 1, 1)
        to_date = date(datetime.now().year, 12, 31)
        data = self._ledger_balance_table(from_date, to_date, ledger_coa)
        if data:
            title = ' '.join(
                [title, MESSAGE_TEXT['PERIOD'].format(from_date, to_date)])
            BuiltPandasBox(title=title, dataframe=DataFrame(data, columns=[DB_account, DB_name, FN_BALANCE]),
                           dataframe_sum=[FN_BALANCE], mode=NO_CURRENCY_SIGN, cellwidth_resizeable=False)
        else:
            self.footer.set(MESSAGE_TEXT['DATA_NO'].format(title, ''))

    def _ledger_balance_table(self, from_date, to_date, ledger_coa):

        data = []
        for ledger_coa_dict in ledger_coa:
            account = ledger_coa_dict[DB_account]
            _name = ledger_coa_dict[DB_name]
            iban = ledger_coa_dict[DB_iban]
            portfolio = ledger_coa_dict[DB_portfolio]
            credit = 0
            debit = 0
            if portfolio:
                balance = self._ledger_balance_holding(ledger_coa_dict, iban)
                credit = ''
                debit = ''
            else:
                if iban != NOT_ASSIGNED:
                    # get opening balance of asset current year
                    order = [DB_entry_date, DB_counter]
                    period = (from_date, to_date)
                    balance_dict = self.mariadb.select_table_first_or_last(STATEMENT, [
                                                                           DB_opening_balance, DB_opening_status], date_name=DB_entry_date, order=order, result_dict=True, iban=iban, period=period)
                    if balance_dict and balance_dict[DB_opening_status] == CREDIT:
                        credit = balance_dict[DB_opening_balance]
                    elif balance_dict and balance_dict[DB_opening_status] == DEBIT:
                        debit = balance_dict[DB_opening_balance]
                    else:
                        # get closing balance of asset last year
                        # necessary if there is no account turnover in the current year
                        order = ' '.join(
                            [DB_entry_date, 'DESC,', DB_counter, 'DESC'])
                        period = (date_years.subtract(from_date, 1),
                                  date_years.subtract(to_date, 1))
                        balance_dict = self.mariadb.select_table_first_or_last(STATEMENT, [
                                                                               DB_closing_balance, DB_closing_status], date_name=DB_entry_date, order=order, result_dict=True, iban=iban, period=period)
                        if balance_dict and balance_dict[DB_closing_status] == CREDIT:
                            credit = balance_dict[DB_closing_balance]
                        elif balance_dict and balance_dict[DB_closing_status] == DEBIT:
                            debit = balance_dict[DB_closing_balance]
                period = (from_date, to_date)
                credit_sum = self.mariadb.select_table_sum(
                    LEDGER, DB_amount, date_name=DB_entry_date, period=period, credit_account=account)
                if credit_sum:
                    credit = credit + credit_sum
                debit_sum = self.mariadb.select_table_sum(
                    LEDGER, DB_amount, date_name=DB_entry_date, period=period, debit_account=account)
                if debit_sum:
                    debit = debit_sum + debit
                balance = credit-debit
            account_dict = dict(zip([DB_account, DB_name, FN_CREDIT, FN_DEBIT, FN_BALANCE],
                                    [account, _name, credit, debit, balance]))
            if credit or debit or balance:
                data.append(account_dict)
        return data

    def _ledger_balance_holding(self, ledger_coa_dict, iban):
        '''
        Return latest total_amount_portfolio, otherwise return 0
        '''
        max_price_date = self.mariadb.select_max_column_value(
            HOLDING, DB_price_date, iban=iban)
        if max_price_date:
            result = self.mariadb.select_table(
                HOLDING, [DB_total_amount_portfolio], iban=iban, price_date=max_price_date)
            if result:
                # HOLDING Account contains only 1 record per day
                return result[0][0]
        return 0

    def _ledger_upload_check(self):
        '''
        Check (last upload ledger)
        '''
        self._delete_footer()
        title = ' '.join([MENU_TEXT['Ledger'],
                         MENU_TEXT['Check Upload']])

        field_list = TABLE_FIELDS[LEDGER_VIEW]
        from_date = date(datetime.now().year - 1, 1, 1)
        to_date = date(datetime.now().year, 12, 31)
        period = (from_date, to_date)
        while True:
            data = self.mariadb.select_table(
                LEDGER_VIEW, field_list, result_dict=True,
                date_name=DB_entry_date, period=period, upload_check=False)
            if data:
                table = PandasBoxLedgerTable(
                    title, data, self.mariadb, None)
                if table.button_state == WM_DELETE_WINDOW:
                    break
            else:
                period = MESSAGE_TEXT['PERIOD'].format(
                    date_days.convert(from_date), date_days.convert(to_date))
                self.footer.set(MESSAGE_TEXT['DATA_NO'].format(title, period))
                break

    def _ledger_bank_statement_check(self):
        '''
        Check (Bank Statement of an account)
        '''
        title = ' '.join([MENU_TEXT['Ledger'],
                         MENU_TEXT['Check Bank Statement']])
        self._ledger_account(title=title, iban_clause=True)

    def _ledger_account(self, title=None, iban_clause=False):

        self._delete_footer()
        if title is None:
            title = ' '.join([MENU_TEXT['Ledger'],
                             MENU_TEXT['Account']])
        field_list = TABLE_FIELDS[LEDGER_VIEW]
        from_date = date(datetime.now().year, 1, 1)
        to_date = date(datetime.now().year, 12, 31)
        period = (from_date, to_date)
        while True:
            input_account = InputAccount(
                self.mariadb, title=title, period=period, iban_clause=iban_clause)
            if input_account.button_state == WM_DELETE_WINDOW:
                return
            from_date = input_account.field_dict[FN_FROM_DATE]
            to_date = input_account.field_dict[FN_TO_DATE]
            period = (from_date, to_date)
            account_name = input_account.field_dict[DB_account]
            account = account_name[:4]
            message = None
            while True:
                title_period = '  '.join(
                    [title, account_name[5:], MESSAGE_TEXT['PERIOD'].format(from_date, to_date)])
                if title.startswith(' '.join([MENU_TEXT['Ledger'], MENU_TEXT['Check Bank Statement']])):
                    # caller is _ledger_statement_check
                    data = self.mariadb.select_ledger_account(
                        field_list, account, result_dict=True, date_name=DB_entry_date, period=period, bank_statement_checked=False)
                    if data:
                        table = PandasBoxLedgerTable(
                            title_period, data, self.mariadb, message, mode=EDIT_ROW)
                        message = table.message
                        if table.button_state == WM_DELETE_WINDOW:
                            return
                else:
                    data = self.mariadb.select_ledger_account(
                        field_list, account, result_dict=True, date_name=DB_entry_date, period=period)
                    table = PandasBoxLedgerTable(
                        title_period, data, self.mariadb, message, mode=EDIT_ROW)
                    message = table.message
                    if table.button_state == WM_DELETE_WINDOW:
                        return

    def _ledger_journal(self):

        self._delete_footer()
        title = ' '.join([MENU_TEXT['Ledger'],
                         MENU_TEXT['Journal']])
        field_list = TABLE_FIELDS[LEDGER_VIEW]
        from_date = date(datetime.now().year, 1, 1)
        to_date = date(datetime.now().year, 12, 31)
        while True:
            input_date = InputDate(
                title=title, from_date=from_date, to_date=to_date)
            if input_date.button_state == WM_DELETE_WINDOW:
                return
            from_date = input_date.field_dict[FN_FROM_DATE]
            to_date = input_date.field_dict[FN_TO_DATE]
            title_period = ' '.join([title, from_date, '-', to_date])
            message = None
            while True:
                data = self.mariadb.select_table(
                    LEDGER_VIEW, field_list, result_dict=True,
                    date_name=DB_entry_date, period=(from_date, to_date))
                if data:
                    table = PandasBoxLedgerTable(
                        title_period, data, self.mariadb, message, mode=EDIT_ROW)
                    message = table.message
                    if table.button_state == WM_DELETE_WINDOW:
                        break
                else:
                    self.footer.set(
                        MESSAGE_TEXT['DATA_NO'].format(' ', title_period))
                    break

    def _ledger_coa_table(self):

        self._delete_footer()
        title = ' '.join([MENU_TEXT['Ledger'],
                         MENU_TEXT['Chart of Accounts']])
        field_list = TABLE_FIELDS[LEDGER_COA]
        message = None
        while True:
            data = self.mariadb.select_table(
                LEDGER_COA, field_list, result_dict=True)
            ledger_coa_table = PandasBoxLedgerCoaTable(
                title, data, self.mariadb, message, mode=EDIT_ROW)
            message = ledger_coa_table.message
            if ledger_coa_table.button_state == WM_DELETE_WINDOW:
                return


class Data_ISIN_Period(object):
    """
    Get ISIN and period for table query
    ARGS
            title        message-key of title
            header       message-key header text
            table        MARIA DB table/view
            mariadb      MARIA DB connector
    """

    def __init__(self, title=MESSAGE_TITLE, header_key='SELECT', mariadb=None, table=TRANSACTION_VIEW,
                 bank_name='', iban=None, button2_text=None):

        self.header_key = header_key
        self.mariadb = mariadb
        self.table = table
        self.bank_name = bank_name
        self.iban = iban
        self.footer = ''
        if button2_text == BUTTON_NEW:
            transaction_isin = self.mariadb.select_dict(ISIN, DB_name, DB_ISIN)
        elif not iban:
            transaction_isin = self.mariadb.select_dict(
                self.table, DB_name, DB_ISIN, )
        else:
            transaction_isin = self.mariadb.select_dict(
                self.table, DB_name, DB_ISIN, iban=self.iban)
        if transaction_isin == {}:
            self.footer = MESSAGE_TEXT['DATA_NO'].format(
                self.bank_name, self.iban)
        else:
            names_list = list(transaction_isin.keys())
            name_ = names_list[0]
            from_date = date(2000, 1, 1)
            to_date = date.today() + timedelta(days=360)
            while True:
                self.title = title
                input_isin = InputISIN(
                    title=self.title, header=MESSAGE_TEXT[self.header_key],
                    default_values=(name_, transaction_isin[name_], from_date,
                                    to_date),
                    names=transaction_isin)
                if input_isin.button_state == WM_DELETE_WINDOW:
                    return
                self.name_, self.isin, from_date, to_date = tuple(
                    list(input_isin.field_dict.values()))
                name_ = self.name_
                self.period = (from_date, to_date)
                self.title = ' '.join([title, self.name_])
                self._data_processing()

    def _data_processing(self):

        pass


class DataTransactionDetail(Data_ISIN_Period):
    """
    Show transactions of ISIN in period
    """

    def _data_processing(self):

        field_list = 'price_date, counter, transaction_type, price, pieces, posted_amount'

        if self.iban:
            select_isin_transaction = self.mariadb.select_transactions_data(
                field_list=field_list, iban=self.iban, isin_code=self.isin, period=self.period)
        else:
            select_isin_transaction = self.mariadb.select_transactions_data(
                field_list=field_list, isin_code=self.isin, period=self.period)
        if select_isin_transaction:
            count_transactions = len(select_isin_transaction)
            if self.iban:
                select_holding_ibans = [self.iban]
            else:
                select_holding_ibans = self.mariadb.select_holding_fields(
                    field_list=DB_iban)
            for iban in select_holding_ibans:
                select_isin_transaction = self._data_transaction_add_portfolio(
                    iban, select_isin_transaction)
            from_date, to_date = self.period
            title_period = ' '.join(
                [self.title, MESSAGE_TEXT['PERIOD'].format(from_date, to_date)])
            while True:
                table = PandasBoxTransactionDetail(title=title_period, dataframe=(
                    count_transactions, select_isin_transaction), mode=NO_CURRENCY_SIGN)
                if table.button_state == WM_DELETE_WINDOW:
                    break
        else:
            self.footer = MESSAGE_TEXT['DATA_NO'].format(
                self.bank_name, self.iban)

    def _data_transaction_add_portfolio(self, iban, select_isin_transaction):

        # add portfolio position, adds not realized profit/loss to transactions
        select_holding_last = self.mariadb.select_holding_last(
            iban, self.isin, self.period, field_list='price_date, market_price, pieces, total_amount')
        if select_holding_last:
            if select_holding_last[0] < select_isin_transaction[-1][0]:
                return select_isin_transaction
            self.period = (self.period[0], select_holding_last[0])
            select_holding_last = (
                select_holding_last[0], 0, TRANSACTION_DELIVERY,  *select_holding_last[1:])
            select_isin_transaction.append(select_holding_last)
        return select_isin_transaction
