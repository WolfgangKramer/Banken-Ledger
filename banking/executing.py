"""
Created on 09.12.2019
__updated__ = "2025-07-17"
Author: Wolfang Kramer
"""
import sys
import requests
import webbrowser
from PIL import ImageTk

from time import sleep
from datetime import date, timedelta, datetime
from threading import Thread
from tkinter import Tk, Menu, TclError, GROOVE, ttk, Canvas, StringVar, font
from tkinter.ttk import Label
from fints.types import ValueList
from pandas import DataFrame

from banking.bank import InitBank, InitBankSync, InitBankAnonymous
from banking.declarations import (
    ALPHA_VANTAGE, ALPHA_VANTAGE_DOCUMENTATION,
    Balance,
    BMW_BANK_CODE, BUNDESBANK_BLZ_MERKBLATT, BUNDEBANK_BLZ_DOWNLOAD,
    CURRENCY_SIGN, CREDIT,
    DEBIT,
    EDIT_ROW,
    FINTS_SERVER, FINTS_SERVER_ADDRESS,
    START_DATE_PRICES, START_DATE_TRANSACTIONS,
    FN_COMPARATIVE,
    FN_DATE, FN_FROM_DATE, FN_TO_DATE,
    FN_PIECES_CUM, FN_ALL_BANKS,
    FN_CREDIT, FN_DEBIT, FN_BALANCE,
    FN_PROFIT_LOSS,
    INFORMATION, Informations,
    JSON_KEY_ERROR_MESSAGE, JSON_KEY_META_DATA,
    KEY_ACCOUNTS, KEY_ACC_BANK_CODE, KEY_ACC_OWNER_NAME,
    KEY_ACC_SUBACCOUNT_NUMBER, KEY_ACC_ALLOWED_TRANSACTIONS, KEY_ACC_IBAN,
    KEY_ACC_ACCOUNT_NUMBER, KEY_MAX_PIN_LENGTH, KEY_MIN_PIN_LENGTH,
    KEY_ACC_PRODUCT_NAME,
    KEY_BANK_CODE, KEY_BANK_NAME, KEY_DOWNLOAD_ACTIVATED,
    KEY_PIN, KEY_BIC,
    KEY_SECURITY_FUNCTION,
    KEY_SERVER, KEY_IDENTIFIER_DELIMITER, KEY_STORAGE_PERIOD,
    KEY_USER_ID, KEY_VERSION_TRANSACTION,
    MENU_TEXT, MESSAGE_TEXT, MESSAGE_TITLE,
    NOT_ASSIGNED, NUMERIC, NO_CURRENCY_SIGN,
    ORIGIN, ORIGIN_PRICES, ORIGIN_INSERTED,
    PERCENT,
    SCRAPER_BANKDATA,
    SEPA_AMOUNT, SEPA_CREDITOR_BIC,
    SEPA_CREDITOR_IBAN, SEPA_CREDITOR_NAME, SEPA_EXECUTION_DATE, SEPA_PURPOSE,
    SEPA_PURPOSE_1, SEPA_PURPOSE_2, SEPA_REFERENCE,
    SHELVE_KEYS,
    START_DATE_HOLDING,
    TRANSACTION_DELIVERY, TRANSFER_DATA_SEPA_EXECUTION_DATE,
    WEBSITES, WARNING,
    # form declaratives
    BUTTON_APPEND, BUTTON_SAVE,
    BUTTON_PRICES_IMPORT, BUTTON_REPLACE, BUTTON_RESTORE,
    BUTTON_ALPHA_VANTAGE,
    TYP_DECIMAL,
    WM_DELETE_WINDOW,
)
from banking.declarations_mariadb import (
    PRODUCTIVE_DATABASE_NAME,
    TABLE_FIELDS, TABLE_FIELDS_PROPERTIES,
    DB_acquisition_amount, DB_amount_currency, DB_amount, DB_account, DB_applicant_name,
    DB_alpha_vantage,
    DB_alpha_vantage_function, DB_alpha_vantage_parameter,
    DB_opening_balance, DB_opening_currency, DB_opening_status, DB_opening_entry_date,
    DB_closing_balance, DB_closing_currency, DB_closing_status, DB_closing_entry_date,
    DB_counter, DB_date, DB_category, DB_code, DB_currency, DB_credit_account,
    DB_close,
    DB_debit_account,
    DB_entry_date,
    DB_ISIN, DB_iban, DB_id_no,
    DB_market_price,
    DB_name,
    DB_ledger,
    DB_origin, DB_origin_symbol,
    DB_row_id,
    DB_pieces, DB_portfolio, DB_purpose_wo_identifier,
    DB_threading,
    DB_total_amount, DB_price_date,
    DB_total_amount_portfolio, DB_transaction_type,
    DB_symbol, DB_status,
    APPLICATION, GEOMETRY,
    HOLDING, HOLDING_VIEW,
    BANKIDENTIFIER, LEDGER_STATEMENT,
    ISIN, PRICES_ISIN_VIEW, PRICES, SERVER, STATEMENT,
    TRANSACTION, TRANSACTION_VIEW,
    LEDGER, LEDGER_COA, LEDGER_VIEW,
    SHELVES,
)
from banking.formbuilts import (
    BuiltRadioButtons, BuiltPandasBox,
    destroy_widget,
    FileDialogue,
    ProgressBar,
)
from banking.messagebox import (MessageBoxAsk, MessageBoxInfo)
from banking.forms import (
    import_prices_run,
    AlphaVantageParameter, AppCustomizing,
    BankDataChange, BankDataNew, BankDelete,
    InputISIN,
    InputDate, InputPeriod, InputDateHolding,
    InputIsins, InputDateTable, InputDateTransactions, InputDatePrices,
    PandasBoxLedgerCoaTable, PandasBoxLedgerTable,
    PandasBoxIsinComparision, PandasBoxIsinComparisionPercent,
    PandasBoxStatementTable, PandasBoxHoldingTable, PandasBoxIsinTable,
    PandasBoxBalancesAllBanks,
    PandasBoxHoldingPercent, PandasBoxTotals, PandasBoxTransactionDetail,
    PandasBoxHoldingPortfolios, PandasBoxBalances,
    PandasBoxTransactionTable, PandasBoxTransactionTableShow, PandasBoxTransactionProfit,
    PandasBoxPrices, PandasBoxLedgerAccountCategory,
    PrintList, PrintMessageCode,
    SelectFields, SelectLedgerAccount, SelectLedgerAccountCategory,
    SepaCreditBox,
    TechnicalIndicator,
    VersionTransaction, SelectDownloadPrices,
)
from banking.mariadb import MariaDB
from banking.scraper import AlphaVantage, BmwBank
from banking.sepa import SepaCreditTransfer
from banking.utils import (
    application_store,
    date_days, date_years, dec2,
    dict_get_first_key,
    exception_error,
    holding_informations_append,
)


class BankenLedger(object):
    """
    Start of Application
    Execution of Application Customizing
    Execution of MARIADB Retrievals
    Execution of Bank Dialogues

    holdings : ignores download (all_banks) holdings if False
    """

    def __init__(self, user, password, database, host, title=MESSAGE_TITLE):

        self.user = user
        self.database = database
        self.host = host
        self.mariadb = MariaDB()
        self._application_store_load_data()
        self.bank_names = self.mariadb.dictbank_names()
        while True:
            self.wpd_iban = []
            self.kaz_iban = []
            self.window = None
            self.window = Tk()
            self.progress = ProgressBar(self.window)
            self.window.title(title)
            self.window.geometry('600x500+1+1')
            self.window.resizable(0, 1)
            self.canvas = Canvas(self.window, width=600, height=400)
            self.canvas.pack(fill="both", expand=True)
            try:
                self.bg_photo = ImageTk.PhotoImage(file="background.gif")
                self.canvas.create_image(0, 0, image=self.bg_photo, anchor="nw")
            except Exception as e:
                print('BankenLedger', MESSAGE_TEXT['CONNECT_IMAGE_ERROR'].format(e))
            if self.database.lower() != PRODUCTIVE_DATABASE_NAME:
                fill_colour = 'red'
            else:
                fill_colour = 'lightblue'
            self.canvas.create_text(300, 200, fill=fill_colour, font=(
                'Arial', 20, 'bold'), text=MESSAGE_TEXT['DATABASE'].format(self.database))
            self._def_styles()
            self.bank_owner_account = self._create_bank_owner_account()
            self._create_menu(self.database)
            self.footer = StringVar()
            self.message_widget = Label(self.window,
                                        textvariable=self.footer, foreground='RED', justify='center')
            # self.footer.set('')
            self.message_widget.pack(side='bottom', fill='both', expand=True)
            self.load_timer = None
            self.window.protocol(WM_DELETE_WINDOW, self._wm_deletion_window)
            if application_store.get(DB_alpha_vantage):
                self.alpha_vantage_function = self.mariadb.alpha_vantage_get(DB_alpha_vantage_function)
                self.alpha_vantage_parameter = self.mariadb.alpha_vantage_get(DB_alpha_vantage_parameter)
                self.alpha_vantage = AlphaVantage(self.progress, self.alpha_vantage_function, self.alpha_vantage_parameter)
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

    def _application_store_load_data(self):

        result = self.mariadb.select_table(APPLICATION, '*', result_dict=True, row_id=1)
        if result:
            application_data = {k: v for d in result for k, v in d.items()}
        else:
            application_data = {}
        application_store.load_data(application_data)

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
        if application_store.get(DB_threading):
            banks_credentials = self.mariadb.listbank_codes()
            banks_download = []
            for bank_code in banks_credentials:
                if self.mariadb.shelve_get_key(bank_code, KEY_DOWNLOAD_ACTIVATED):
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
                        bank.logoff()
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
                    name=bank.bank_name, target=self.mariadb.all_accounts, args=(bank,))
                download_thread.start()
                seconds = 0
                while download_thread.is_alive() and seconds < 60:
                    sleep(1)
                    seconds += 1
                    self.progress.update_progressbar()
                if bank.scraper:
                    bank.logoff()
            self.progress.stop()
            self.footer.set(
                MESSAGE_TEXT['DOWNLOAD_DONE'].format(CANCELED, 10 * '!'))
        else:
            for bank_code in self.mariadb.listbank_codes():
                if self.mariadb.shelve_get_key(bank_code, KEY_DOWNLOAD_ACTIVATED):
                    self._all_accounts(bank_code)
        self._show_informations()

    def _all_accounts(self, bank_code):

        self._delete_footer()
        bank = self._bank_init(bank_code)
        if bank:
            self.footer.set(
                MESSAGE_TEXT['DOWNLOAD_RUNNING'].format(bank.bank_name))
            self.progress.start()
            self.mariadb.all_accounts(bank)
            if bank.scraper:
                bank.logoff()
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
        field_dict = application_store.get(None)
        while True:
            app_data_box = AppCustomizing(field_dict)
            if app_data_box.button_state == WM_DELETE_WINDOW:
                return
            field_dict = app_data_box.field_dict
            if app_data_box.button_state == BUTTON_SAVE:
                app_data_box.field_dict[DB_row_id] = 1
                self.mariadb.execute_replace(APPLICATION, app_data_box.field_dict)
                MessageBoxInfo(message=MESSAGE_TEXT['DATABASE_REFRESH'])
                self._wm_deletion_window()
            elif app_data_box.button_state == BUTTON_RESTORE:
                field_dict = application_store.get(None)
            elif app_data_box.button_state == WM_DELETE_WINDOW:
                break

    def _def_styles(self):

        style = ttk.Style()
        style.theme_use(style.theme_names()[0])
        style.configure('TLabel', font=('Arial', 8, 'bold'))
        style.configure('OPT.TLabel', font=(
            'Arial', 8, 'bold'), foreground='Grey')
        style.configure('HDR.TLabel', font=(
            'Courier', 12, 'bold'), foreground='Grey')
        style.configure('TButton', font=('Arial', 8, 'bold'), relief=GROOVE,
                        highlightcolor='blue', highlightthickness=5, shiftrelief=3)
        style.configure('TText', font=('Courier', 8))

    def _alpha_vantage_refresh(self):

        self.footer.set(MESSAGE_TEXT['ALPHA_VANTAGE_REFRESH_RUN'])
        refresh = self.alpha_vantage.refresh()
        if refresh:
            self.footer.set(MESSAGE_TEXT['ALPHA_VANTAGE_REFRESH'])
        else:
            self.footer.set(MESSAGE_TEXT['ALPHA_VANTAGE_ERROR'])

    def _bank_data_change(self, bank_code):

        self._delete_footer()
        bank_name = self._bank_name(bank_code)
        title = ' '.join([bank_name, MENU_TEXT['Customize'],
                          MENU_TEXT['Change Login Data']])
        login_data = self.mariadb.shelve_get_key(
            bank_code, [KEY_BANK_NAME, KEY_USER_ID, KEY_PIN, KEY_BIC, KEY_SERVER, KEY_IDENTIFIER_DELIMITER, KEY_DOWNLOAD_ACTIVATED])
        bank_data_box = BankDataChange(
            title, bank_code, login_data)
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
            self.mariadb.shelve_put_key(bank_code, data)
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
                title=title, message=MESSAGE_TEXT['IMPORT_CSV'].format(BANKIDENTIFIER.upper(), NOT_ASSIGNED))
        elif not bank_codes:
            MessageBoxInfo(
                title=title, message=MESSAGE_TEXT['IMPORT_CSV'].format(SERVER.upper(), NOT_ASSIGNED))
        else:
            bank_data_box = BankDataNew(
                title, bank_codes=bank_codes)
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
                self.mariadb.shelve_put_key(bank_code, data)
            except KeyError as key_error:
                exception_error()
                MessageBoxInfo(title=title,
                               message=MESSAGE_TEXT['LOGIN'].format(bank_code, key_error))
                return
            bank_name = self.mariadb.shelve_get_key(bank_code, KEY_BANK_NAME)
            if bank_code in list(SCRAPER_BANKDATA.keys()):
                if bank_code == BMW_BANK_CODE:
                    self._bank_data_scraper(BMW_BANK_CODE)
                MessageBoxInfo(title=title, message=MESSAGE_TEXT['BANK_DATA_NEW_SCRAPER'].format(
                    bank_name, bank_code))
            else:
                self._bank_security_function(bank_code, True)
                MessageBoxInfo(title=title, message=MESSAGE_TEXT['BANK_DATA_NEW'].format(
                    bank_name, bank_code))
            self._wm_deletion_window()  # to show new bank in menu after restart

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
        self.mariadb.execute_delete(SHELVES, code=bank_code)
        del self.bank_names[bank_code]
        MessageBoxInfo(
            title=title,
            message=MESSAGE_TEXT['BANK_DELETED'].format(bank_name, bank_code))
        self.window.destroy()

    def _bank_data_scraper(self, bank_code):

        bank = self._bank_init(bank_code)
        get_accounts = bank.get_accounts()
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
        self.mariadb.shelve_put_key(bank_code, data)

    def _bank_init(self, bank_code):

        if bank_code in list(SCRAPER_BANKDATA.keys()):
            if bank_code == BMW_BANK_CODE:
                bank = BmwBank()
        else:
            bank = InitBank(bank_code)
        return bank

    def _bank_refresh_bpd(self, bank_code):

        self._delete_footer()
        bank = InitBankAnonymous(bank_code)
        bank.dialogs.anonymous(bank)
        bank_name = self._bank_name(bank_code)
        message = ' '.join([bank_name, MENU_TEXT['Customize'],
                            MENU_TEXT['Refresh BankParameterData']])
        self._show_message(bank, message=message)

    def _bank_show_shelve(self, bank_code):

        self._delete_footer()
        shelve_data = self.mariadb.shelve_get_key(bank_code, SHELVE_KEYS)
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
        bank = InitBankSync(bank_code)
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
        transaction_versions = self.mariadb.shelve_get_key(
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
            self.mariadb.shelve_put_key(bank_code, data)
        except KeyError as key_error:
            MessageBoxInfo(title=title, message=MESSAGE_TEXT['LOGIN'].format(
                bank_name, key_error))

    def _create_menu(self, MariaDBname):

        menu_font = font.Font(family='Arial', size=11)
        menu = Menu(self.window)
        self.window.config(menu=menu, borderwidth=10, relief=GROOVE)
        if application_store.get(DB_ledger):
            self._create_menu_ledger(menu, menu_font)
        if self.bank_names != {} and application_store.get(None):  # application customizing is done
            self._create_menu_show(menu, self.bank_owner_account, menu_font)
            self._create_menu_download(menu, menu_font)
            """
            Deactivated: Verification of Payyee
            self._create_menu_transfer(menu, self.bank_owner_account, menu_font)
            """
        if application_store.get(None):  # application customizing is done
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
            ledger_menu.add_command(
                label=MENU_TEXT['Account Category'], command=self._ledger_account_category)
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
        show_menu.add_separator()
        if application_store.get(DB_alpha_vantage):
            show_menu.add_command(
                label=MENU_TEXT['Alpha Vantage'], command=self._show_alpha_vantage)
            show_menu.add_command(
                label=MENU_TEXT['Alpha Vantage Symbol Search'], command=self._show_alpha_vantage_search_symbol)
        show_menu.add_separator()
        show_menu.add_command(
            label=MENU_TEXT['Balances'], command=self._show_balances_all_banks)
        show_menu.add_separator()
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
            accounts = self.mariadb.shelve_get_key(bank_code, KEY_ACCOUNTS)
            if accounts:
                for acc in accounts:
                    if 'HKWPD' in acc[KEY_ACC_ALLOWED_TRANSACTIONS]:
                        download_menu.add_cascade(
                            label=' '.join(
                                [bank_name, MENU_TEXT['Holding'], acc[KEY_ACC_PRODUCT_NAME], acc[KEY_ACC_ACCOUNT_NUMBER]]),
                            command=lambda x=bank_code: self._all_holdings(x))
            download_menu.add_separator()

    def _create_menu_transfer(self, menu, bank_owner_account, menu_font):
        """
        TRANSFER Menu
        """
        transfer_menu = Menu(menu, tearoff=0, font=menu_font, bg='Lightblue')
        menu.add_cascade(label=MENU_TEXT['Transfer'], menu=transfer_menu)
        self._create_menu_banks(
            MENU_TEXT['Transfer'], bank_owner_account, transfer_menu, menu_font)

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
            accounts = self.mariadb.shelve_get_key(bank_code, KEY_ACCOUNTS)
            if accounts:
                for acc in accounts:
                    if 'HKWPD' in acc[KEY_ACC_ALLOWED_TRANSACTIONS]:
                        bank_names[bank_code] = bank_name
        if bank_names != {}:
            all_banks_menu = Menu(
                database_menu, tearoff=0, font=menu_font, bg='Lightblue')
            database_menu.add_cascade(
                label=MENU_TEXT['All_Banks'], menu=all_banks_menu, underline=0)
            database_menu.add_separator()
            all_banks_menu.add_command(
                label=MENU_TEXT['Holding Performance'],
                command=(lambda x=FN_ALL_BANKS, y='':
                         self._data_holding_performance(x, y)))
            all_banks_menu.add_command(
                label=MENU_TEXT['Holding ISIN Comparision'],
                command=(lambda x=FN_ALL_BANKS: self._data_holding_isin_comparision(x, '')))
            all_banks_menu.add_command(
                label=MENU_TEXT['Holding ISIN Comparision'] + '%',
                command=(lambda x=FN_ALL_BANKS: self._data_holding_isin_comparision_percent(x, '')))
            all_banks_menu.add_command(label=MENU_TEXT['Balances'],
                                       command=self._data_balances)

            all_banks_menu.add_command(
                label=MENU_TEXT['Transaction Detail'],
                command=(lambda x=FN_ALL_BANKS,
                         y=None: self._data_transaction_detail(x, y)))
            self._create_menu_banks(
                MENU_TEXT['Database'], bank_owner_account, database_menu, menu_font)
        database_menu.add_command(
            label=MENU_TEXT['ISIN Table'], command=self._data_isin_table)
        database_menu.add_separator()
        database_menu.add_command(
            label=MENU_TEXT['Technical Indicators'], command=self._data_technical_indicators)
        database_menu.add_separator()
        database_menu.add_command(
            label=MENU_TEXT['Prices ISINs'],
            command=(lambda x=None: self._data_prices(x)))
        database_menu.add_command(
            label=MENU_TEXT['Prices ISINs'] + '%',
            command=(lambda x=PERCENT: self._data_prices(x)))

    def _create_menu_customizing(self, menu, menu_font, MariaDBname):
        """
        CUSTOMIZE Menu
        """
        customize_menu = Menu(menu, tearoff=0, font=menu_font, bg='Lightblue')
        menu.add_cascade(label=MENU_TEXT['Customize'], menu=customize_menu)
        customize_menu.add_command(label=MENU_TEXT['Application INI File'],
                                   command=self._appcustomizing)
        if application_store.get(None):  # Customizing is done
            customize_menu.add_separator()
            customize_menu.add_command(label=MENU_TEXT['Import Bankidentifier CSV-File'],
                                       command=self._import_bankidentifier)
            customize_menu.add_command(label=MENU_TEXT['Import Server CSV-File'],
                                       command=self._import_server)
            customize_menu.add_separator()
            customize_menu.add_command(label=MENU_TEXT['Reset Screen Positions'],
                                       command=self._reset)
            if application_store.get(DB_alpha_vantage):
                customize_menu.add_command(label=MENU_TEXT['Refresh Alpha Vantage'],
                                           command=self._alpha_vantage_refresh)
                customize_menu.add_separator()
            if application_store.get(None):  # application customizing is done
                if self.mariadb.select_server:
                    customize_menu.add_command(label=MENU_TEXT['New Bank'],
                                               command=self._bank_data_new)
                    customize_menu.add_command(label=MENU_TEXT['Delete Bank'],
                                               command=self._bank_data_delete)
                else:
                    MessageBoxInfo(message=MESSAGE_TEXT['PRODUCT_ID'])
            if self.bank_names:
                for bank_name in self.bank_names.values():
                    bank_code = dict_get_first_key(self.bank_names, bank_name)
                    cust_bank_menu = Menu(customize_menu, tearoff=0,
                                          font=menu_font, bg='Lightblue')
                    cust_bank_menu.add_command(label=MENU_TEXT['Change Login Data'],
                                               command=lambda x=bank_code: self._bank_data_change(x))
                    if bank_code not in list(SCRAPER_BANKDATA.keys()):
                        cust_bank_menu.add_command(label=MENU_TEXT['Change Security Function'],
                                                   command=lambda
                                                   x=bank_code: self._bank_security_function(x, False))
                        cust_bank_menu.add_command(label=MENU_TEXT['Synchronize'],
                                                   command=lambda x=bank_code: self._bank_sync(x))
                        cust_bank_menu.add_command(label=MENU_TEXT['Change FinTS Transaction Version'],
                                                   command=lambda
                                                   x=bank_code: self._bank_version_transaction(x))
                        """
                        cust_bank_menu.add_command(label=MENU_TEXT['Refresh BankParameterData'],
                                                   command=lambda
                                                   x=bank_code: self._bank_refresh_bpd(x))
                        """                           
                    cust_bank_menu.add_command(label=MENU_TEXT['Show Data'],
                                               command=lambda x=bank_code: self._bank_show_shelve(x))
                    customize_menu.add_separator()
                    customize_menu.add_cascade(
                        label=bank_name, menu=cust_bank_menu, underline=0)

    def _create_menu_banks(self, menu_text, bank_owner_account, typ_menu, menu_font):

        for bank_code in self.bank_names.keys():
            bank_name = self.bank_names[bank_code]
            if bank_code in bank_owner_account.keys():
                owner_menu = Menu(typ_menu, tearoff=0,
                                  font=menu_font, bg='Lightblue')
                if menu_text == MENU_TEXT['Show']:
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
                        if menu_text == MENU_TEXT['Transfer']:
                            accounts_exist = self._create_menu_transfer_accounts(
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
                        typ_menu.add_separator()
            else:
                account_menu = Menu(
                    typ_menu, tearoff=0, font=menu_font, bg='Lightblue')
                bank_code = dict_get_first_key(self.bank_names, bank_name)
                accounts = self.mariadb.shelve_get_key(bank_code, KEY_ACCOUNTS)
                if menu_text == MENU_TEXT['Show']:
                    accounts_exist = self._create_menu_show_accounts(
                        accounts, account_menu, bank_code, bank_name)
                if menu_text == MENU_TEXT['Transfer']:
                    accounts_exist = self._create_menu_transfer_accounts(
                        accounts, account_menu, bank_code, bank_name)
                elif menu_text == MENU_TEXT['Database']:
                    accounts_exist = self._create_menu_database_accounts(
                        accounts, account_menu, bank_name, menu_font)
                if accounts_exist:
                    typ_menu.add_cascade(
                        label=bank_name, menu=account_menu, underline=0)
                    typ_menu.add_separator()

    def _create_menu_show_accounts(self, accounts, account_menu, bank_code, bank_name, owner_name=None):

        accounts_exist = True
        account_menu.add_command(label=MENU_TEXT['Balances'],
                                 command=lambda x=bank_code, y=bank_name: self._show_balances(x, y, owner_name=owner_name))
        if accounts:
            for acc in accounts:
                if 'HKKAZ' in acc[KEY_ACC_ALLOWED_TRANSACTIONS] or 'HKCAZ' in acc[KEY_ACC_ALLOWED_TRANSACTIONS]:
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
                if 'HKWDU' in acc[KEY_ACC_ALLOWED_TRANSACTIONS] or \
                        'HKWPD' in acc[KEY_ACC_ALLOWED_TRANSACTIONS]:
                    label = ' '.join(
                        [MENU_TEXT['Transactions'], acc[KEY_ACC_PRODUCT_NAME], acc[KEY_ACC_ACCOUNT_NUMBER], TRANSACTION.upper()])
                    account_menu.add_command(
                        label=label,
                        command=(lambda x=bank_code, y=acc: self._show_transactions(x, y)))
        return accounts_exist

    def _create_menu_transfer_accounts(self, accounts, account_menu, bank_code, bank_name, owner_name=None):

        accounts_exist = False
        if accounts:
            for acc in accounts:
                if 'HKCCS' in acc[KEY_ACC_ALLOWED_TRANSACTIONS]:
                    accounts_exist = True
                    label = acc[KEY_ACC_PRODUCT_NAME]
                    if not label:
                        label = acc[KEY_ACC_ACCOUNT_NUMBER]
                    label = ' '.join([MENU_TEXT['Statement'], label])
                    account_menu.add_command(
                        label=label,
                        command=(lambda x=bank_code,
                                 y=acc: self._sepa_credit_transfer(x, y)))
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
                        command=(lambda x=bank_name, y=acc[KEY_ACC_IBAN]: self._data_holding_isin_comparision(x, y)))
                    account_menu.add_command(
                        label=MENU_TEXT['Holding ISIN Comparision'] + '%',
                        command=(lambda x=bank_name, y=acc[KEY_ACC_IBAN]: self._data_holding_isin_comparision_percent(x, y)))
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
                        label=MENU_TEXT['Update Holding Market Price by Closing Price'],
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
        """
        create  multiple bank_owner_account hierarchy as dicts
        returns: dict : key--> bank_name:
                            value/key--> owner:
                                value --> list  accounts
                                    list_item  --> dict account_data
        """
        bank_owner_account = {}
        for bank_code in self.bank_names.keys():
            accounts = self.mariadb.shelve_get_key(bank_code, KEY_ACCOUNTS)
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

    def _data_holding_performance(self, bank_name, iban):

        self._delete_footer()
        _data_holding_performance = None
        title = ' '.join([bank_name, MENU_TEXT['Holding Performance']])
        data_dict = {FN_FROM_DATE: date.today() - timedelta(days=360),
                     FN_TO_DATE: date.today()}
        while True:
            input_period = InputPeriod(title=title, data_dict=data_dict)
            if isinstance(_data_holding_performance, BuiltPandasBox):
                destroy_widget(_data_holding_performance.dataframe_window)
            if input_period.button_state == WM_DELETE_WINDOW:
                return
            data_dict = input_period.field_dict

            if bank_name == FN_ALL_BANKS:
                select_holding_total = self.mariadb.select_holding_all_total(
                    period=(data_dict[FN_FROM_DATE], data_dict[FN_TO_DATE]))
            else:
                select_holding_total = self.mariadb.select_holding_total(
                    iban=iban, period=(data_dict[FN_FROM_DATE], data_dict[FN_TO_DATE]))
            if select_holding_total:
                title_period = ' '.join([title, ' ',
                                         MESSAGE_TEXT['PERIOD'].format(data_dict[FN_FROM_DATE], data_dict[FN_TO_DATE])])
                while True:
                    table = PandasBoxHoldingPortfolios(
                        title=title_period, dataframe=select_holding_total, mode=NUMERIC)
                    if table.button_state == WM_DELETE_WINDOW:
                        break
            else:
                self.footer.set(
                    MESSAGE_TEXT['DATA_NO'].format(bank_name, iban))

    def _data_holding_isin_comparision(self, bank_name, iban):

        self._delete_footer()
        title = ' '.join([bank_name, MENU_TEXT['Holding ISIN Comparision']])
        from_date = date_days.subtract(date.today(), 360)
        data_dict_period = {
            FN_FROM_DATE: from_date,  FN_TO_DATE: date.today()}
        while True:
            input_period = InputPeriod(
                title=title, data_dict=data_dict_period, selection_name=title + 'A')
            if input_period.button_state == WM_DELETE_WINDOW:
                return
            data_dict_period = input_period.field_dict
            period = (data_dict_period[FN_FROM_DATE],
                      data_dict_period[FN_TO_DATE])
            if iban:
                isin_dict = self.mariadb.select_dict(
                    HOLDING_VIEW, DB_ISIN, DB_name, iban=iban, period=period, order=DB_name)
            else:
                isin_dict = self.mariadb.select_dict(
                    HOLDING_VIEW, DB_ISIN, DB_name, period=period, order=DB_name)
            if isin_dict:
                data_dict_isins = {FN_COMPARATIVE: DB_total_amount}
                for isin_code in isin_dict.keys():
                    data_dict_isins[isin_code] = 0
                input_isins = InputIsins(table=isin_dict, selection_name=title + 'B',
                                         title=title, data_dict=data_dict_isins, separator=[FN_COMPARATIVE])
                if input_isins.button_state == WM_DELETE_WINDOW:
                    return
                data_dict_isins = input_isins.field_dict
                selected_isins = list(
                    filter(lambda x: data_dict_isins[x] == 1, list(data_dict_isins.keys())))
                # more than one isin selected
                if len(selected_isins) > 1:
                    if data_dict_isins[FN_COMPARATIVE] == FN_PROFIT_LOSS:
                        db_fields = [DB_name, DB_price_date,
                                     ''.join([DB_total_amount, '-', DB_acquisition_amount, ' AS ', FN_PROFIT_LOSS])]
                    else:
                        db_fields = [DB_name, DB_price_date,
                                     data_dict_isins[FN_COMPARATIVE]]
                    if iban:
                        selected_holding_data = self.mariadb.select_holding_data(
                            field_list=db_fields, iban=iban, isin_code=selected_isins,
                            period=period)
                    else:
                        selected_holding_data = self.mariadb.select_holding_data(
                            field_list=db_fields, isin_code=selected_isins, period=period)
                    if selected_holding_data:
                        self.footer.set('')
                        title_period = ' '.join([title, data_dict_isins[FN_COMPARATIVE].upper(), MESSAGE_TEXT['PERIOD'].format(
                            period[0], period[1])])
                        while True:
                            table = PandasBoxIsinComparision(title=title_period, dataframe=(
                                data_dict_isins[FN_COMPARATIVE], selected_holding_data),
                                dataframe_typ=TYP_DECIMAL, mode=NUMERIC)
                            if table.button_state == WM_DELETE_WINDOW:
                                break
                    else:
                        self.footer.set(MESSAGE_TEXT['FIELDLIST_INTERSECTION_EMPTY'])
                else:
                    self.footer.set(MESSAGE_TEXT['FIELDLIST_MIN'].format("2"))
            else:
                self.footer.set(
                    MESSAGE_TEXT['DATA_NO'].format(bank_name, iban))

    def _data_holding_isin_comparision_percent(self, bank_name, iban):
        """
        Name, price_date, comparision_field of isins
        in their maximum common time interval in a given period
        """
        self._delete_footer()
        title = ' '.join([bank_name, MENU_TEXT['Holding ISIN Comparision %']])
        from_date = date_days.subtract(date.today(), 360)
        data_dict_period = {
            FN_FROM_DATE: from_date,  FN_TO_DATE: date.today()}

        while True:
            input_period = InputPeriod(
                title=title, data_dict=data_dict_period, selection_name=title + 'A')
            if input_period.button_state == WM_DELETE_WINDOW:
                return
            data_dict_period = input_period.field_dict
            period = (data_dict_period[FN_FROM_DATE],
                      data_dict_period[FN_TO_DATE])
            if iban:
                isin_dict = self.mariadb.select_dict(
                    HOLDING_VIEW, DB_ISIN, DB_name, iban=iban, period=period, order=DB_name)
            else:
                isin_dict = self.mariadb.select_dict(
                    HOLDING_VIEW, DB_ISIN, DB_name, period=period, order=DB_name)
            if isin_dict:
                data_dict_isins = {FN_COMPARATIVE: DB_total_amount}
                for isin_code in isin_dict.keys():
                    data_dict_isins[isin_code] = 0
                input_isins = InputIsins(table=isin_dict, selection_name=title + 'B',
                                         title=title, data_dict=data_dict_isins, separator=[FN_COMPARATIVE])
                if input_isins.button_state == WM_DELETE_WINDOW:
                    return
                data_dict_isins = input_isins.field_dict
                selected_isins = list(
                    filter(lambda x: data_dict_isins[x] == 1, list(data_dict_isins.keys())))
                # more than one isin selected
                if len(selected_isins) > 1:
                    from_date, to_date, data = self.mariadb.select_holding_isins_interval(
                        iban, data_dict_isins[FN_COMPARATIVE], selected_isins, period=period)
                    if data:
                        self.footer.set('')
                        title_period = ' '.join([title, data_dict_isins[FN_COMPARATIVE].upper(), MESSAGE_TEXT['PERIOD'].format(
                            from_date, to_date)])
                        while True:
                            table = PandasBoxIsinComparisionPercent(title=title_period, dataframe=(
                                data_dict_isins[FN_COMPARATIVE], data),
                                dataframe_typ=TYP_DECIMAL, mode=NUMERIC)
                            if table.button_state == WM_DELETE_WINDOW:
                                break
                    else:
                        self.footer.set(MESSAGE_TEXT['FIELDLIST_INTERSECTION_EMPTY'])
                else:
                    self.footer.set(MESSAGE_TEXT['FIELDLIST_MIN'].format("2"))
            else:
                self.footer.set(
                    MESSAGE_TEXT['DATA_NO'].format(bank_name, iban))

    def _data_isin_table(self):

        self._delete_footer()
        title = ' '.join([MENU_TEXT['Database'], MENU_TEXT['ISIN Table']])
        selected_row = 0
        message = MESSAGE_TEXT['HELP_PANDASTABLE']
        while True:
            data = self.mariadb.select_table(
                ISIN, '*', result_dict=True, order=DB_name)
            isin_table = PandasBoxIsinTable(
                title, data, message, mode=EDIT_ROW, selected_row=selected_row)
            selected_row = isin_table.selected_row
            message = isin_table.message
            if isin_table.button_state == WM_DELETE_WINDOW:
                break
            if isin_table.button_state == BUTTON_PRICES_IMPORT:
                import_prices_run(title, self.mariadb, [isin_table.selected_row_dict[DB_name]], BUTTON_REPLACE)
                self._show_informations()
            self.footer.set(message)
            message = None

    def _data_holding_table(self, bank_name, iban):

        self._delete_footer()
        title = ' '.join([bank_name,
                          MENU_TEXT['Holding Table']])
        data_dict = {FN_FROM_DATE: date.today(), FN_TO_DATE: date.today()}
        message = MESSAGE_TEXT['HELP_PANDASTABLE']
        while True:
            date_holding_view = InputDateTable(
                title=title, data_dict=data_dict, table=HOLDING_VIEW)
            if date_holding_view.button_state == WM_DELETE_WINDOW:
                return
            data_dict = date_holding_view.field_dict
            selected_check_button = list(
                filter(lambda x: data_dict[x] == 1, list(data_dict.keys())))
            period = ' '.join(
                [data_dict[FN_FROM_DATE], '-', data_dict[FN_TO_DATE]])
            title_period = ' '.join([title, period])

            data = self.mariadb.select_table(
                HOLDING_VIEW, [DB_iban, DB_price_date, DB_ISIN] + selected_check_button, result_dict=True,
                date_name=DB_price_date, iban=iban, period=(data_dict[FN_FROM_DATE], data_dict[FN_TO_DATE]))
            if data:
                while True:
                    holding_table = PandasBoxHoldingTable(
                        title_period, data, message, iban, mode=EDIT_ROW)
                    message = holding_table.message
                    if holding_table.button_state == WM_DELETE_WINDOW:
                        break
                    self.footer.set(message)
                    message = None

    def _data_update_holding_prices(self, bank_name, iban):
        """
        For a working day:
        Replaces market_price (table HOLDING) by close price (table PRICES)
        If not existing: creates holding positions
        """
        title = ' '.join(
            [bank_name, MENU_TEXT['Update Holding Market Price by Closing Price']])
        while True:
            input_date = InputDate(title=title)
            if input_date.button_state == WM_DELETE_WINDOW:
                return
            if input_date:
                date_day = input_date.field_dict[FN_DATE]
            if date_days.isweekend(date_day):
                MessageBoxInfo(
                    title=title, message=MESSAGE_TEXT['DATE_NO_WORKDAY'].format(date_day))
            break
        holdings = self.mariadb.select_table(
            HOLDING_VIEW, '*', result_dict=True, iban=iban, price_date=date_day)
        if not holdings:  # duplicate holding positions
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
                return
            holdings = self.mariadb.select_table(
                HOLDING_VIEW, '*', result_dict=True, iban=iban, price_date=date_day)
        if holdings:  # update holding positions
            for holding_dict in holdings:
                title_download = ' '.join(
                    [title, MENU_TEXT['Download'], MENU_TEXT['Prices']])
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
            self.mariadb.update_total_holding_amount(
                iban=iban, period=(date_day, date_day))
        self._show_informations()

    def _data_update_holding_price(self, title, bank_name, iban, holding_dict):
        """
        Imports prices
        Updates market_price, total_amount
        """
        price = self.mariadb.select_table(
            PRICES_ISIN_VIEW, DB_close, result_dict=True, isin_code=holding_dict[DB_ISIN], price_date=holding_dict[DB_price_date])
        if not price:
            # import price data
            data = self.mariadb.select_table(
                ISIN, '*', result_dict=True, isin_code=holding_dict[DB_ISIN])
            message = MESSAGE_TEXT['HELP_PANDASTABLE']
            isin_table = PandasBoxIsinTable(
                title, data, message, mode=EDIT_ROW)
            message = isin_table.message
            if isin_table.button_state == WM_DELETE_WINDOW:
                return
            if isin_table.button_state == BUTTON_PRICES_IMPORT:
                import_prices_run(title, self.mariadb, [isin_table.selected_row_dict[DB_name]], BUTTON_REPLACE)
        if price:
            # update holding market price
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
        return False
    
    def _data_technical_indicators(self):
        """      
        def destroy_withdrawn():
            for widget in root.winfo_children():
                if isinstance(widget, Toplevel):
                    if not widget.winfo_viewable():  # = withdrawn oder iconified
                        widget.destroy()        
        """
        self._delete_footer()
        title = MENU_TEXT['Technical Indicators']
        names_dict = dict(self.mariadb.select_isin_with_ticker([DB_name, DB_symbol], order=DB_name))
        data_dict = {FN_FROM_DATE: date_days.subtract(date.today(), 360),
                     FN_TO_DATE: date.today()}
        while True:
            ta_data = TechnicalIndicator(
                title=title, data_dict=data_dict, container_dict=names_dict, selection_name=title)
            if ta_data.button_state == WM_DELETE_WINDOW:
                break
            data_dict[DB_ISIN] = ta_data.field_dict[DB_ISIN]
            data_dict[DB_name] = ta_data.field_dict[DB_name]
            data_dict[FN_FROM_DATE] = ta_data.field_dict[FN_FROM_DATE]
            data_dict[FN_TO_DATE] = ta_data.field_dict[FN_TO_DATE]

    def _data_transaction_detail(self, bank_name, iban):

        self._delete_footer()
        title = ' '.join([bank_name,
                          MENU_TEXT['Transaction Detail']])
        data_dict = {}
        if iban:
            data_dict[DB_iban] = iban
        while True:
            date_transations = InputDateTransactions(
                title=title, data_dict=data_dict, upper=[DB_name])
            if date_transations.button_state == WM_DELETE_WINDOW:
                return
            data_dict = date_transations.field_dict
            title_period = ' '.join(
                [title, data_dict[FN_FROM_DATE], '-', data_dict[FN_TO_DATE]])
            period = (data_dict[FN_FROM_DATE], data_dict[FN_TO_DATE])
            if iban in data_dict.keys():
                select_isin_transaction = self.mariadb.select_transactions_data(
                    iban=data_dict[DB_iban], name=data_dict[DB_name], period=period)
            else:
                select_isin_transaction = self.mariadb.select_transactions_data(
                    name=data_dict[DB_name], period=period)
            if select_isin_transaction:
                count_transactions = len(select_isin_transaction)
                if iban:
                    select_holding_ibans = [iban]
                else:
                    select_holding_ibans = self.mariadb.select_holding_fields(
                        field_list=DB_iban)
                for iban in select_holding_ibans:
                    select_isin_transaction = self._data_transaction_add_portfolio(
                        iban, data_dict[DB_name], period, select_isin_transaction)
                title_period = ' '.join(
                    [title, MESSAGE_TEXT['PERIOD'].format(data_dict[FN_FROM_DATE], data_dict[FN_TO_DATE])])
                while True:
                    table = PandasBoxTransactionDetail(title=title_period, dataframe=(
                        count_transactions, select_isin_transaction), mode=NO_CURRENCY_SIGN)
                    if table.button_state == WM_DELETE_WINDOW:
                        break
                    else:
                        self.footer.set(
                            MESSAGE_TEXT['DATA_NO'].format(bank_name, iban))

    def _data_transaction_add_portfolio(self, iban, name, period, select_isin_transaction):

        # add portfolio position, adds not realized profit/loss to transactions
        select_holding_last = self.mariadb.select_holding_last(
            iban, name, period, field_list='price_date, market_price, pieces, total_amount')
        if select_holding_last:
            if select_holding_last[0] < select_isin_transaction[-1][0]:
                return select_isin_transaction
            period = (period[0], select_holding_last[0])
            select_holding_last = (
                select_holding_last[0], 0, TRANSACTION_DELIVERY,  *select_holding_last[1:])
            select_isin_transaction.append(select_holding_last)
        return select_isin_transaction

    def _data_transaction_table(self, bank_name, iban):

        self._delete_footer()
        title = ' '.join([bank_name,
                          MENU_TEXT['Transactions Table']])
        field_list = TABLE_FIELDS[TRANSACTION_VIEW]
        data_dict = {DB_name: '', DB_ISIN: '',
                     FN_FROM_DATE: START_DATE_TRANSACTIONS,
                     FN_TO_DATE: date(datetime.now().year, 12, 31)}
        names_dict = self.mariadb.select_dict(
                    ISIN, DB_name, DB_ISIN, order=DB_name)
        while True:
            input_isin = InputISIN(title=title, data_dict=data_dict, container_dict=names_dict)
            if input_isin.button_state == WM_DELETE_WINDOW:
                return
            isin = data_dict[DB_ISIN] = input_isin.field_dict[DB_ISIN]
            name = data_dict[DB_name] = input_isin.field_dict[DB_name]
            from_date = data_dict[FN_FROM_DATE] = input_isin.field_dict[FN_FROM_DATE]
            to_date = data_dict[FN_TO_DATE] = input_isin.field_dict[FN_TO_DATE]
            title_period = ' '.join(
                [title, name, isin, from_date, '-', to_date])
            message = MESSAGE_TEXT['HELP_PANDASTABLE']
            while True:
                data = self.mariadb.select_table(
                    TRANSACTION_VIEW, field_list, result_dict=True, iban=iban, isin_code=isin, period=(from_date, to_date))
                transaction_table = PandasBoxTransactionTable(
                    title_period, data, message, iban, isin, name, mode=EDIT_ROW)
                message = transaction_table.message
                if transaction_table.button_state == WM_DELETE_WINDOW:
                    break
                else:
                    self.footer.set(message)
                    message = None

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
        data_dict = {FN_FROM_DATE: START_DATE_PRICES,
                     FN_TO_DATE: date_days.convert(date.today())}
        while True:
            while True:
                date_prices = InputDatePrices(
                    title=title, data_dict=data_dict)
                if date_prices.button_state == WM_DELETE_WINDOW:
                    return
                data_dict = date_prices.field_dict
                selected_check_button = list(
                    filter(lambda x: data_dict[x] == 1, list(data_dict.keys())))
                db_fields = list(TABLE_FIELDS_PROPERTIES[PRICES].keys())
                # intersection: price fields of table PRICES
                selected_fields = list(set(db_fields) & set(selected_check_button))
                selected_isins = list(set(db_fields) ^ set(
                    selected_check_button))  # symetric_difference: selected isin_codes
                if selected_fields and selected_isins:
                    result = self.mariadb.select_table(ISIN, DB_name, isin_code=selected_isins)
                    field_names = [x[0] for x in result]
                    import_prices_run(title, self.mariadb, field_names, BUTTON_APPEND)
                    break
                else:
                    MessageBoxInfo(title=title, message=MESSAGE_TEXT['SELECT_INCOMPLETE'])
            select_data = self.mariadb.select_table(PRICES_ISIN_VIEW, [DB_name, DB_price_date] + selected_fields,
                                                    order=DB_name, result_dict=True,
                                                    isin_code=selected_isins,
                                                    period=(data_dict[FN_FROM_DATE], data_dict[FN_TO_DATE]))
            select_origin_dict = dict(self.mariadb.select_table(
                ISIN, [DB_name, DB_origin_symbol], isin_code=selected_isins))
            if select_data:
                self.footer.set('')
                while True:
                    price_table = PandasBoxPrices(title=title, dataframe=(
                        selected_fields, select_data, select_origin_dict, sign), dataframe_typ=TYP_DECIMAL, mode=NUMERIC)
                    if price_table.button_state == WM_DELETE_WINDOW:
                        break
            else:
                MessageBoxInfo(title=title, message=MESSAGE_TEXT['DATA_NO'].format(', '.join(selected_isins), ''))

    def _data_balances(self):

        self._delete_footer()
        title = ' '.join(
            [MENU_TEXT['All_Banks'], MENU_TEXT['Balances']])
        data_dict = {}
        while True:
            input_period = InputPeriod(title=title, data_dict=data_dict)
            if input_period.button_state == WM_DELETE_WINDOW:
                return input_period.button_state, None, None
            self.footer.set(MESSAGE_TEXT['TASK_STARTED'].format(title))
            data_dict = input_period.field_dict
            period = (data_dict[FN_FROM_DATE], data_dict[FN_TO_DATE])
            data_total_amounts = self.mariadb.select_total_amounts(period)
            title_period = ' '.join([title, MESSAGE_TEXT['PERIOD'].format(
                data_dict[FN_FROM_DATE], data_dict[FN_TO_DATE])])
            self.footer.set(MESSAGE_TEXT['TASK_DONE'])
            if data_total_amounts:
                while True:
                    table = PandasBoxTotals(
                        title_period, data_total_amounts)
                    if table.button_state == WM_DELETE_WINDOW:
                        break
            else:
                MessageBoxInfo(title=title_period, message=(
                    MESSAGE_TEXT['DATA_NO'].format('', '')))

    def _import_bankidentifier(self):

        title = MENU_TEXT['Import Bankidentifier CSV-File']
        MessageBoxInfo(title=title, message=MESSAGE_TEXT['IMPORT_CSV'].format(
            BANKIDENTIFIER.upper(), 'Deutsche Bundesbank \nBankleitzahlendateien ungepackt \nCSV-Format'))
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
                if application_store.get(DB_threading):
                    download_prices = Thread(name=MENU_TEXT['Prices'], target=import_prices_run,
                                             args=(title, self.mariadb, field_list, state))
                    download_prices.start()
                else:
                    import_prices_run(title, self.mariadb, field_list, state)
        else:
            self.footer.set(MESSAGE_TEXT['SYMBOL_MISSING_ALL'].format(title))

    def _import_server(self):

        title = MENU_TEXT['Import Server CSV-File']
        MessageBoxInfo(title=title, message=MESSAGE_TEXT['IMPORT_CSV'].format(
            SERVER.upper(), 'FinTS Download') + FINTS_SERVER)
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
            [bank_name, MESSAGE_TEXT['IMPORT_CSV'].format(TRANSACTION.upper(), NOT_ASSIGNED), _text]))
        file_dialogue = FileDialogue(title=title)
        if file_dialogue.filename not in ['', None]:
            self.mariadb.import_transaction(iban, file_dialogue.filename)
            MessageBoxInfo(title=title, message=MESSAGE_TEXT['LOAD_DATA'].format(
                file_dialogue.filename))
            data = self.mariadb.select_table(
                TRANSACTION, field_list=TABLE_FIELDS[TRANSACTION],  result_dict=True)
            dataframe = DataFrame(data)
            BuiltPandasBox(title=title, dataframe=dataframe)

    def _sepa_credit_transfer(self, bank_code, account):

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
        bank.owner_name = account[KEY_ACC_OWNER_NAME]
        sepa_credit_box = SepaCreditBox(
            bank, account, title=title)
        if sepa_credit_box.button_state == WM_DELETE_WINDOW:
            return
        transfer_data = {}
        account_data = self.mariadb.dictaccount(bank_code,
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
        bank = InitBankAnonymous(bank_code)
        bank.dialogs.anonymous(bank)
        security_function_dict = {}
        default_value = None
        for twostep in bank.twostep_parameters:
            security_function, security_function_name = twostep
            security_function_dict[security_function] = security_function_name
            if (self.mariadb.shelve_get_key(bank_code, KEY_SECURITY_FUNCTION) and self.mariadb.shelve_get_key(
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
            self.mariadb.shelve_put_key(bank_code, data)
        self.footer.set(MESSAGE_TEXT['SYNC_START'].format(bank_name))

    def _reset(self):

        self.mariadb.execute_delete(GEOMETRY)
        self.footer.set(MESSAGE_TEXT['TASK_DONE'])

    def _show_alpha_vantage(self):

        self._delete_footer()
        title = MENU_TEXT['Alpha Vantage']
        alpha_vantage_symbols = self.mariadb.select_dict(
            ISIN, DB_name, DB_symbol, origin_symbol=ALPHA_VANTAGE)
        alpha_vantage_names = list(alpha_vantage_symbols.keys())
        function_list = self.mariadb.alpha_vantage_get(DB_alpha_vantage_function)
        parameter_dict = self.mariadb.alpha_vantage_get(DB_alpha_vantage_parameter)
        field_list = []
        while True:
            checkbutton = SelectFields(
                title=title,
                button2_text=None, button3_text=None, button4_text=None, default_texts=field_list,
                checkbutton_texts=function_list)
            if checkbutton.button_state == WM_DELETE_WINDOW:
                return
            field_list = checkbutton.field_list
            dataframe = None
            for function in checkbutton.field_list:
                default_values = []
                while True:
                    title_function = ' '.join([title, function])
                    parameters = AlphaVantageParameter(
                        title_function, function, application_store.get(DB_alpha_vantage),
                        parameter_dict[function], default_values,
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
                title, function, application_store.get(DB_alpha_vantage),
                self.alpha_vantage.parameter_dict[function], [], [])
            if parameters.button_state == WM_DELETE_WINDOW:
                break
            elif parameters.button_state == MENU_TEXT['ISIN Table']:
                self._data_isin_table()
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
                max_entry_date = ''
                if bank_balances:
                    dataframe = DataFrame(bank_balances, columns=[KEY_ACC_BANK_CODE, KEY_ACC_ACCOUNT_NUMBER,
                                                                  KEY_ACC_PRODUCT_NAME, DB_entry_date,
                                                                  DB_closing_status, DB_closing_balance, DB_closing_currency,
                                                                  DB_opening_status, DB_opening_balance, DB_opening_currency])
                    total_df.append(dataframe)
                    entry_date = dataframe[DB_entry_date].max()
                    if max_entry_date:
                        if entry_date > max_entry_date:
                            max_entry_date = entry_date
                    else:
                        max_entry_date = entry_date
            if total_df:
                # BuiltPandasBox.CELLWIDTH_FIXED[title] = True
                PandasBoxBalancesAllBanks(
                    title=' '.join([title, date_days.convert(max_entry_date)]), dataframe=total_df, mode=CURRENCY_SIGN, bank_names=self.mariadb.dictbank_names())
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
            PandasBoxBalances(title=' '.join([title, date_days.convert(date.today())]), dataframe=dataframe, dataframe_sum=[
                              DB_closing_balance, DB_opening_balance], mode=CURRENCY_SIGN,
                              cellwidth_resizeable=False)
        else:
            self.footer.set(MESSAGE_TEXT['DATA_NO'].format(title, ''))

    def _show_balances_get(self, bank_code, owner_name=None):

        if bank_code in self.bank_owner_account and owner_name:
            accounts = self.bank_owner_account[bank_code][owner_name]
        else:
            accounts = self.mariadb.shelve_get_key(bank_code, KEY_ACCOUNTS)
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
                    all_max_price_date = self.mariadb.select_max_column_value(
                        HOLDING, DB_price_date)
                    max_price_date = self.mariadb.select_max_column_value(
                        HOLDING, DB_price_date, iban=iban)
                    price_date = date_days.subtract(date.today(), 1)
                    if date_days.isweekend(price_date):
                        price_date = date_days.subtract(price_date, 1)
                    if max_price_date and max_price_date >= all_max_price_date:  # if its an emty holding account
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
                    else:
                        ledger_total_amount = self.mariadb.select_ledger_total_amount(iban)
                        if ledger_total_amount:
                            balances.append(Balance(bank_code,
                                                    acc[KEY_ACC_ACCOUNT_NUMBER],
                                                    acc[KEY_ACC_PRODUCT_NAME],
                                                    ledger_total_amount[DB_entry_date],
                                                    ledger_total_amount[DB_status],
                                                    ledger_total_amount[DB_amount],
                                                    ledger_total_amount[DB_entry_date],
                                                    ledger_total_amount[DB_status],
                                                    ledger_total_amount[DB_amount],
                                                    ''
                                                    ))
                        else:
                            balances.append(Balance(bank_code,
                                                    acc[KEY_ACC_ACCOUNT_NUMBER],
                                                    acc[KEY_ACC_PRODUCT_NAME],
                                                    price_date,
                                                    '',
                                                    0,
                                                    '',
                                                    '',
                                                    0,
                                                    ''
                                                    ))
        return balances

    def _show_statements(self, bank_code, account):

        self._delete_footer()
        iban = account[KEY_ACC_IBAN]
        bank_name = self._bank_name(bank_code)
        selection_name = ' '.join(
            [MENU_TEXT['Show'], bank_name, MENU_TEXT['Statement']])
        label = account[KEY_ACC_PRODUCT_NAME]
        if not label:
            label = account[KEY_ACC_ACCOUNT_NUMBER]
        title = ' '.join([selection_name, label])
        data_dict = {FN_FROM_DATE: date(datetime.now().year, 1, 1), FN_TO_DATE: date(
            datetime.now().year, 12, 31)}
        while True:
            date_statement = InputDateTable(
                title=title, data_dict=data_dict, table=STATEMENT, selection_name=selection_name)
            if date_statement.button_state == WM_DELETE_WINDOW:
                return
            data_dict = date_statement.field_dict
            if DB_amount in data_dict:
                data_dict[DB_status] = 1
            if DB_opening_balance in data_dict:
                data_dict[DB_closing_status] = 1
            if DB_opening_balance in data_dict:
                data_dict[DB_opening_status] = 1
            selected_check_button = list(
                filter(lambda x: data_dict[x] == 1, list(data_dict.keys())))
            message = MESSAGE_TEXT['HELP_PANDASTABLE']
            period = (data_dict[FN_FROM_DATE], data_dict[FN_TO_DATE])
            data = self.mariadb.select_table(
                STATEMENT, selected_check_button, result_dict=True,
                date_name=DB_date, iban=iban, period=period)
            title_period = ' '.join([title, str(period)])
            if data:
                while True:
                    table = PandasBoxStatementTable(
                        title_period, data, message, mode=EDIT_ROW)
                    message = table.message
                    if table.button_state == WM_DELETE_WINDOW:
                        break
            else:
                self.footer.set(
                    MESSAGE_TEXT['DATA_NO'].format(title_period, selected_check_button))
                break

    def _show_transactions(self, bank_code, account):

        self._delete_footer()
        iban = account[KEY_ACC_IBAN]
        label = account[KEY_ACC_PRODUCT_NAME]
        if not label:
            label = account[KEY_ACC_ACCOUNT_NUMBER]
        bank_name = self._bank_name(bank_code)
        title = ' '.join([MENU_TEXT['Show'], bank_name,
                          MENU_TEXT['Transactions'], label])
        data_dict = {FN_FROM_DATE: date_days.subtract(
            date.today(), 360), FN_TO_DATE: date.today()}
        message = MESSAGE_TEXT['HELP_PANDASTABLE']
        while True:
            date_transaction_view = InputDateTable(
                title=title, data_dict=data_dict, table=TRANSACTION_VIEW)
            if date_transaction_view.button_state == WM_DELETE_WINDOW:
                return
            data_dict = date_transaction_view.field_dict
            selected_check_button = list(
                filter(lambda x: data_dict[x] == 1, list(data_dict.keys())))
            period = (data_dict[FN_FROM_DATE], data_dict[FN_TO_DATE])
            data = self.mariadb.select_table(
                TRANSACTION_VIEW, selected_check_button, result_dict=True,
                date_name=DB_price_date, iban=iban, period=period, order=DB_price_date)
            title_period = ' '.join([title, str(period)])
            if data:
                while True:
                    table = PandasBoxTransactionTableShow(
                        title_period, data, iban, message, mode=EDIT_ROW)
                    message = table.message
                    if table.button_state == WM_DELETE_WINDOW:
                        break
            else:
                self.footer.set(
                    MESSAGE_TEXT['DATA_NO'].format(title_period, selected_check_button))
                break

    def _show_holdings(self, bank_code, account):

        self._delete_footer()
        iban = account[KEY_ACC_IBAN]
        label = account[KEY_ACC_PRODUCT_NAME]
        if not label:
            label = account[KEY_ACC_ACCOUNT_NUMBER]
        bank_name = self._bank_name(bank_code)
        title = ' '.join(
            [MENU_TEXT['Show'], bank_name, MENU_TEXT['Holding'] + '%', label])
        data_dict = {FN_FROM_DATE: date_days.convert(date.today() - timedelta(days=1)),
                     FN_TO_DATE: date_days.convert(date.today())}
        self.mariadb.selection_put(title, data_dict)    # start with current day
        self.mariadb.execute_delete(GEOMETRY, caller=title)
        while True:
            input_period = InputDateHolding(title=title, data_dict=data_dict,
                                            container_dict={DB_iban: iban})
            if input_period.button_state == WM_DELETE_WINDOW:
                return
            data_dict = input_period.field_dict
            data_from_date = self.mariadb.select_holding_data(
                iban=iban, price_date=data_dict[FN_FROM_DATE])
            to_date = input_period.field_dict[FN_TO_DATE]
            data_to_date = self.mariadb.select_holding_data(
                iban=iban, price_date=to_date)
            title_period = ' '.join(
                [title, MESSAGE_TEXT['PERIOD'].format(data_dict[FN_FROM_DATE], data_dict[FN_TO_DATE])])
            while True:
                table = PandasBoxHoldingPercent(title=title_period, dataframe=(
                    data_to_date, data_from_date), mode=CURRENCY_SIGN,
                    cellwidth_resizeable=False)
                if table.button_state == WM_DELETE_WINDOW:
                    break

    def _transactions_pieces(self, bank_name, iban):

        self._delete_footer()
        title = ' '.join([bank_name, MENU_TEXT['Check Transactions Pieces']])
        data_dict = {FN_FROM_DATE: START_DATE_TRANSACTIONS,
                     FN_TO_DATE: date.today()}
        while True:
            input_period = InputPeriod(title=title, data_dict=data_dict)
            if input_period.button_state == WM_DELETE_WINDOW:
                return
            data_dict = input_period.field_dict
            result = self.mariadb.transaction_portfolio(
                iban=iban, period=(data_dict[FN_FROM_DATE], data_dict[FN_TO_DATE]))
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
        title = ' '.join(
            [bank_name, MENU_TEXT['Profit of closed Transactions']])
        data_dict = {FN_FROM_DATE: START_DATE_TRANSACTIONS,
                     FN_TO_DATE: date.today()}
        while True:
            input_period = InputPeriod(title=title, data_dict=data_dict)
            if input_period.button_state == WM_DELETE_WINDOW:
                return
            data_dict = input_period.field_dict
            self._transactions_profit_closed(
                title, iban, data_dict[FN_FROM_DATE], data_dict[FN_TO_DATE])

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
        title = ' '.join(
            [bank_name, MENU_TEXT['Profit Transactions incl. current Depot Positions']])
        data_dict = {FN_FROM_DATE: START_DATE_TRANSACTIONS,
                     FN_TO_DATE: date.today()}
        while True:
            input_period = InputPeriod(title=title, data_dict=data_dict)
            if input_period.button_state == WM_DELETE_WINDOW:
                return
            data_dict = input_period.field_dict
            result = self.mariadb.transaction_profit_all(
                iban=iban, period=(data_dict[FN_FROM_DATE], data_dict[FN_TO_DATE]))
            if result:
                title_period = ' '.join(
                    [title, MESSAGE_TEXT['PERIOD'].format(data_dict[FN_FROM_DATE], data_dict[FN_TO_DATE])])
                while True:
                    table = PandasBoxTransactionProfit(
                        title=title_period, dataframe=list(result), mode=NO_CURRENCY_SIGN,
                        cellwidth_resizeable=False)
                    if table.button_state == WM_DELETE_WINDOW:
                        break
            else:
                MessageBoxInfo(title=title,
                               message=MESSAGE_TEXT['TRANSACTION_NO'].format(data_dict[FN_FROM_DATE], data_dict[FN_TO_DATE]))
                self._transactions_profit_closed(
                    bank_name, iban, data_dict[FN_FROM_DATE], data_dict[FN_TO_DATE])

    def _update_holding_total_amount_portfolio(self, bank_name, iban):
        """
        Update Table holding total_amount_portfolio
        """
        title = ' '.join(
            [bank_name, iban, MENU_TEXT['Update Portfolio Total Amount']])
        data_dict = {}
        data_dict[FN_FROM_DATE] = date.today()
        data_dict[FN_TO_DATE] = date.today()
        while True:
            input_period = InputPeriod(title=title, data_dict=data_dict)
            if input_period.button_state == WM_DELETE_WINDOW:
                return
            data_dict = input_period.feld_dict
            period = (data_dict[FN_FROM_DATE], data_dict[FN_TO_DATE])
            self.mariadb.update_total_holding_amount(iban=iban, period=period)
            self.footer.set(' '.join(
                [MESSAGE_TEXT['TASK_DONE'],  "\n", MENU_TEXT['Update Portfolio Total Amount'],
                 "\n", bank_name, iban,   MESSAGE_TEXT['PERIOD'].format(data_dict[FN_FROM_DATE], data_dict[FN_TO_DATE])])
            )

    def _websites(self, site):

        webbrowser.open(site)

    """
    Ledger Methods
    """

    def _ledger_balances(self):
        """
        Show ledger balances
            date referred to entry_date field in Ledger
        """
        self._delete_footer()
        title = ' '.join([MENU_TEXT['Ledger'],
                         MENU_TEXT['Balances']])
        data_dict = {FN_FROM_DATE: date(
            date.today().year, 1, 1), FN_TO_DATE: date(date.today().year, 12, 31)}
        input_period = InputPeriod(title=title, data_dict=data_dict)
        if input_period.button_state == WM_DELETE_WINDOW:
            return
        data_dict = input_period.field_dict
        ledger_coa = self.mariadb.select_table(
            LEDGER_COA, [DB_account, DB_name, DB_iban, DB_portfolio], order=DB_account, result_dict=True)
        data = self._ledger_balance_table(
            data_dict[FN_FROM_DATE], data_dict[FN_TO_DATE], ledger_coa)
        if data:
            title = ' '.join(
                [title, MESSAGE_TEXT['PERIOD'].format(data_dict[FN_FROM_DATE], data_dict[FN_TO_DATE])])
            BuiltPandasBox(title=title, dataframe=DataFrame(
                data), mode=NO_CURRENCY_SIGN, cellwidth_resizeable=False)
        else:
            self.footer.set(MESSAGE_TEXT['DATA_NO'].format(title, ''))

    def _ledger_assets(self):
        """
        Show ledger assets
            date referred to entry_date field in Ledger
        """
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
        max_price_date_all_iban = self.mariadb.select_max_column_value(
            HOLDING, DB_price_date, period=(from_date, to_date))
        for ledger_coa_dict in ledger_coa:
            account = ledger_coa_dict[DB_account]
            _name = ledger_coa_dict[DB_name]
            iban = ledger_coa_dict[DB_iban]
            portfolio = ledger_coa_dict[DB_portfolio]
            credit = 0
            debit = 0
            if portfolio:
                balance, price_date = self._ledger_balance_holding(
                    ledger_coa_dict, iban)
                if price_date != max_price_date_all_iban:
                    # this holding is empty:
                    balance = 0
                credit = ''
                debit = ''
            else:
                if iban != NOT_ASSIGNED:
                    # get opening balance of asset current year
                    order = [DB_entry_date, DB_counter]
                    field_list = [DB_opening_balance, DB_opening_status]
                    period = (from_date, to_date)
                    balance_dict = self.mariadb.select_table_first(
                        STATEMENT, field_list, date_name=DB_entry_date, order=order, result_dict=True, iban=iban, period=period)
                    if balance_dict and balance_dict[DB_opening_status] == CREDIT:
                        credit = balance_dict[DB_opening_balance]
                    elif balance_dict and balance_dict[DB_opening_status] == DEBIT:
                        debit = balance_dict[DB_opening_balance]
                    else:
                        # get closing balance of asset last year
                        # necessary if there is no account turnover in the current year
                        order = [DB_entry_date, DB_counter]
                        field_list = [DB_closing_balance, DB_closing_status]
                        period = (date_years.subtract(from_date, 1),
                                  date_years.subtract(to_date, 1))
                        balance_dict = self.mariadb.select_table_last(
                            STATEMENT, field_list, date_name=DB_entry_date, order=order, result_dict=True, iban=iban, period=period)
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
            if credit or debit or balance or portfolio:
                data.append(account_dict)
        return data

    def _ledger_balance_holding(self, ledger_coa_dict, iban):
        """
        Return latest total_amount_portfolio, otherwise return 0
        """
        max_price_date = self.mariadb.select_max_column_value(
            HOLDING, DB_price_date, iban=iban)
        if max_price_date:
            result = self.mariadb.select_table(
                HOLDING, [DB_total_amount_portfolio, DB_price_date], iban=iban, price_date=max_price_date)
            if result:
                # HOLDING Account contains only 1 record per day (total_amount_portfolio, price_date)
                return result[0]
        return 0

    def _ledger_upload_check(self):
        """
        Check (last upload ledger)
        """
        self._delete_footer()
        title = ' '.join([MENU_TEXT['Ledger'],
                         MENU_TEXT['Check Upload']])

        field_list = TABLE_FIELDS[LEDGER_VIEW]
        from_date = date(datetime.now().year - 1, 1, 1)
        to_date = date(datetime.now().year, 12, 31)
        period = (from_date, to_date)
        message = MESSAGE_TEXT['HELP_CHECK_UPLOAD']
        while True:
            data = self.mariadb.select_table(
                LEDGER_VIEW, field_list, result_dict=True,
                date_name=DB_entry_date, period=period, upload_check=False, origin=ORIGIN)
            if data:
                table = PandasBoxLedgerTable(
                    title, data, message, period=period)
                message = table.message
                if table.button_state == WM_DELETE_WINDOW:
                    break
            else:
                period = MESSAGE_TEXT['PERIOD'].format(
                    date_days.convert(from_date), date_days.convert(to_date))
                self.footer.set(MESSAGE_TEXT['DATA_NO'].format(title, period))
                break

    def _ledger_bank_statement_check(self):
        """
        Check (Bank Statement of an account)
        """
        title = ' '.join([MENU_TEXT['Ledger'],
                         MENU_TEXT['Check Bank Statement']])
        self._ledger_account(title=title, iban_clause=True)

    def _ledger_account_category(self):
        """
        Account grouped by category with sum Rows
        """
        self._delete_footer()
        title = ' '.join([MENU_TEXT['Ledger'],
                         MENU_TEXT['Account Category']])
        data_dict = self.mariadb.selection_get(title)
        if not data_dict:
            data_dict = {FN_FROM_DATE: date(datetime.now().year, 1, 1), FN_TO_DATE: date(
                datetime.now().year, 12, 31)}
        while True:
            select_ledger_account = SelectLedgerAccountCategory(
                title=title, data_dict=data_dict)
            if select_ledger_account.button_state == WM_DELETE_WINDOW:
                return
            data_dict = select_ledger_account.field_dict
            period = (data_dict[FN_FROM_DATE], data_dict[FN_TO_DATE])
            account_name = data_dict[DB_account][5:]
            account = data_dict[DB_account][:4]
            field_list = [DB_id_no, DB_entry_date, DB_date, DB_purpose_wo_identifier, DB_amount,
                          DB_currency, DB_category, DB_credit_account, DB_debit_account, DB_applicant_name]
            while True:
                title_period = '  '.join(
                    [title, account, account_name, MESSAGE_TEXT['PERIOD'].format(data_dict[FN_FROM_DATE], data_dict[FN_TO_DATE])])
                data = self.mariadb.select_ledger_account(
                    field_list, account, result_dict=True, date_name=DB_entry_date, period=period)
                if data:
                    table = PandasBoxLedgerAccountCategory(
                        title=title_period, dataframe=data, mode=NUMERIC)
                    if table.button_state == WM_DELETE_WINDOW:
                        break
                else:
                    self.footer.set(
                        MESSAGE_TEXT['DATA_NO'].format(' ', title_period))
                    break

    def _ledger_account(self, title=None, iban_clause=False):

        self._delete_footer()
        if title is None:
            title = ' '.join([MENU_TEXT['Ledger'],
                             MENU_TEXT['Account']])
        data_dict = self.mariadb.selection_get(title)
        if not data_dict:
            data_dict = {FN_FROM_DATE: date(datetime.now().year, 1, 1),
                         FN_TO_DATE: date(datetime.now().year, 12, 31)}
        while True:
            select_ledger_account = SelectLedgerAccount(
                title=title, data_dict=data_dict)
            if select_ledger_account.button_state == WM_DELETE_WINDOW:
                return
            data_dict = select_ledger_account.field_dict
            period = (data_dict[FN_FROM_DATE], data_dict[FN_TO_DATE])
            account_name = data_dict[DB_account][5:]
            account = data_dict[DB_account][:4]
            data_dict[DB_id_no] = 1
            field_list = list(filter(lambda x: data_dict[x] == 1, list(
                data_dict.keys())))  # filter selected check_buttons
            selected_row = 0
            message = MESSAGE_TEXT['HELP_PANDASTABLE']
            while True:
                title_period = '  '.join(
                    [title, account, account_name, MESSAGE_TEXT['PERIOD'].format(data_dict[FN_FROM_DATE], data_dict[FN_TO_DATE])])
                if title.startswith(' '.join([MENU_TEXT['Ledger'], MENU_TEXT['Check Bank Statement']])):
                    # caller is _ledger_statement_check
                    data = self.mariadb.select_ledger_account(
                        field_list, account, result_dict=True, date_name=DB_entry_date, period=period, bank_statement_checked=False)
                else:
                    data = self.mariadb.select_ledger_account(
                        field_list, account, result_dict=True, date_name=DB_entry_date, period=period)

                if data:
                    table = PandasBoxLedgerTable(
                        title_period, data, message, mode=EDIT_ROW, selected_row=selected_row, period=period)
                    message = table.message
                    selected_row = table.selected_row
                    if table.button_state == WM_DELETE_WINDOW:
                        break
                else:
                    self.footer.set(
                        MESSAGE_TEXT['DATA_NO'].format(' ', title_period))
                    break

    def _ledger_journal(self):

        self._delete_footer()
        title = ' '.join([MENU_TEXT['Ledger'],
                         MENU_TEXT['Journal']])
        field_list = TABLE_FIELDS[LEDGER_VIEW]
        data_dict = self.mariadb.selection_get(title)
        if not data_dict:
            data_dict = {FN_FROM_DATE: date(datetime.now().year, 1, 1), FN_TO_DATE: date(
                datetime.now().year, 12, 31)}
        message = MESSAGE_TEXT['HELP_PANDASTABLE']
        while True:
            input_period = InputPeriod(title=title, data_dict=data_dict)
            if input_period.button_state == WM_DELETE_WINDOW:
                return
            data_dict = input_period.field_dict
            title_period = ' '.join(
                [title, data_dict[FN_FROM_DATE], '-', data_dict[FN_TO_DATE]])
            selected_row = 0
            while True:
                period = (data_dict[FN_FROM_DATE], data_dict[FN_TO_DATE])
                data = self.mariadb.select_table(
                    LEDGER_VIEW, field_list, result_dict=True,
                    date_name=DB_entry_date, period=period)
                if data:
                    table = PandasBoxLedgerTable(
                        title_period, data, message, mode=EDIT_ROW, selected_row=selected_row, period=period)
                    message = table.message
                    selected_row = table.selected_row
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
        message = MESSAGE_TEXT['HELP_PANDASTABLE']
        selected_row = 0
        while True:
            data = self.mariadb.select_table(
                LEDGER_COA, field_list, result_dict=True)
            ledger_coa_table = PandasBoxLedgerCoaTable(
                title, data, message, mode=EDIT_ROW, selected_row=selected_row)
            message = ledger_coa_table.message
            selected_row = ledger_coa_table.selected_row
            if ledger_coa_table.button_state == WM_DELETE_WINDOW:
                return
