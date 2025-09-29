#!/usr/bin/env python
# -*- coding: latin-1 -*-
"""
Created on 09.12.2019
__updated__ = "2025-07-17"
@author: Wolfgang Kramer
"""

from _datetime import date
from collections import namedtuple
from dataclasses import dataclass, field
from decimal import Decimal
from banking.declarations_mariadb import (
    DB_entry_date, DB_closing_status, DB_closing_balance, DB_closing_currency,
    DB_opening_status, DB_opening_balance, DB_opening_currency,
)


PNS = {}
"""
-------------------------- Date Constants -----------------------------------------------
"""
# Start Currency EUR
START_CURRENCY_EUR = '2002-01-01'
# Start date  download in MariaDB database
# e.g. start www download of prices e.g. from https://www.alphavantage.co
START_DATE_PRICES = '2000-01-01'
# start download of statements from bank; attention check storage_period of your bank
START_DATE_STATEMENTS = date(2010, 1, 1)
# start date transaction date
START_DATE_TRANSACTIONS = date(2000, 1, 1)
# start date holding_data
START_DATE_HOLDING = date(2010, 1, 1)
# start date transfer statements to ledger
START_DATE_LEDGER = date(1990, 1, 1)
# Submission of scheduled SEPA transfers (HKCSE)
TRANSFER_DATA_SEPA_EXECUTION_DATE = '1999-01-01'
# Maria DB initialzing date fields
MARIADB_STANDARD_DATE = '2000-01-01'

"""
-------------------------- Alpha Vantage Prices Constants -----------------------------------------------

"""
OUTPUTSIZE_COMPACT = 'compact'
OUTPUTSIZE_FULL = 'full'
"""
-------------------------- Constants -----------------------------------------------
"""
NOT_ASSIGNED = 'NA'
VALIDITY_DEFAULT = '9999-01-01'
"""
--------------------------- WebSites --------------------------------------------------
"""
BUNDESBANK_BLZ_MERKBLATT = b"https://www.bundesbank.de/resource/blob/602848/50cba8afda2b0b1442016101cfd7e084/mL/merkblatt-bankleitzahlendatei-data.pdf"
BUNDEBANK_BLZ_DOWNLOAD = b"https://www.bundesbank.de/de/aufgaben/unbarer-zahlungsverkehr/serviceangebot/bankleitzahlen/download-bankleitzahlen-602592"
MSEDGE_DRIVER_DOWNLOAD = b"https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver"
FINTS_SERVER_ADDRESS = b"https://www.fints.org/de/hersteller/produktregistrierung"

FRANKFURTER_BOERSE = b"https://www.boerse-frankfurt.de/aktien/suche"
BNPPARIBAS = b"https://www.derivate.bnpparibas.com/realtime"
ONVISTA = b"https://www.onvista.de/"
WWW_YAHOO = b"https://de.finance.yahoo.com/lookup"
ALPHA_VANTAGE_DOCUMENTATION = 'https://www.alphavantage.co/documentation/'
WEBSITES = {'Frankfurter Boerse': FRANKFURTER_BOERSE,
            'BNP Paribas': BNPPARIBAS,
            'onvista': ONVISTA,
            'YAHOO!': WWW_YAHOO,
            'AlphaVantage': ALPHA_VANTAGE_DOCUMENTATION}

FINTS_SERVER = " \n\nContains German Bank FINTS Server Address \nRegistrate to get CSV Files  with PIN/TAN-Bank Access URL from FINTS\n\nCSV File contains 28 Columns\nColumn B: CODE\nColumn Y: PIN/TAN URL in CSV-File "
"""
--------------------------- Messages --------------------------------------------------
"""
MESSAGE_TITLE = 'BANK ARCHIVE'
MENU_TEXT = {
    'Connect DB': 'Connect DB',
    'Ledger': 'Ledger',
    'Show': 'Show',
    'Download': 'Download',
    'Transfer': 'Transfer',
    'Database': 'Database',
    'Customize': 'Customize',

    'Account': 'Account',
    'Account Category': 'Account Category',
    'All_Banks': 'All_Banks',
    'Alpha Vantage': 'Alpha Vantage Query',
    'Alpha Vantage Symbol Search': 'Alpha Vantage Symbol Search',
    'Application INI File': 'Application INI File',
    'Assets': 'Assets',
    'Balances': 'Balances',
    'Change FinTS Transaction Version': 'Change FinTS Transaction Version',
    'Change Security Function': 'Change Security Function',
    'Change Login Data': 'Change Login Data',
    'Chart of Accounts': 'Chart of Accounts',
    'Check Transactions Pieces': 'Check Transactions Pieces',
    'Check Upload': 'Check Upload',
    'Check Bank Statement': 'Check Bank Statement',
    'Delete Bank': 'Delete Bank',
    'Holding': 'Holding',
    'Holding Performance': 'Holding Performance',
    'Holding ISIN Comparision': 'Holding ISIN Comparision',
    'Holding ISIN Comparision %': 'Holding ISIN Comparision %',
    'Holding Table': 'Holding Table',
    'Import Bankidentifier CSV-File': 'Bankidentifier CSV-File',
    'Import Server CSV-File': 'Server CSV-File',
    'Import Ticker Symbols': 'Ticker CSV-File',
    'Import Transactions': 'Import Transactions',
    'ISIN Table': 'ISIN Table',
    'Journal': 'Journal',
    'New Bank': 'New Bank',
    'Prices': 'Prices',
    'Prices ISINs': 'Prices',
    'Profit Transactions incl. current Depot Positions': 'Profit Transactions incl. current Depot Positions',
    'Profit of closed Transactions': 'Profit of closed Transactions',
    'Refresh Alpha Vantage': 'Create Alpha Vantage Query Selection',
    'Refresh BankParameterData': 'Refresh BankParameterData',
    'Reset Screen Positions': 'Reset Screen Positions',
    'Show Data': 'Show Data',
    'Statement': 'Statement',
    'Synchronize': 'Synchronize',
    'Synchronize Transactions': 'Synchronize Transactions',
    'Technical Indicators': 'Technical Indicators',
    'Transactions': 'Transactions',
    'Transaction Detail': 'Transaction Detail',
    'Transactions Table': 'Transactions Table',
    'Update': 'Update',
    'Update Holding Market Price by Closing Price': 'Update Holding Market Price by Closing Price',
    'Update Portfolio Total Amount': 'Update Portfolio Total Amount',
    'WebSites': 'WebSites',
    'Frankfurter Boerse': 'Frankfurter Boerse',
    'Onvista': 'Onvista',
    'Boerse.de': 'Boerse.de',
}

POPUP_MENU_TEXT = {
    'Show selected Row': 'Show selected Row',
    'Show credit data': 'Show selected Row credit data',
    'Show debit data': 'Show selected Row debit data',
    'New Row': 'New Row',
    'Update selected Row': 'Update selected Row',
    'Delete selected Row': 'Delete selected Row',
    'Export to Excel': 'Export to Excel',
}

CODE_3010 = '3010'  # Download bank data,    no entries exist'
CODE_3040 = '3040'  # Download partially executed
CODE_0030 = '0030'  # Download not executed
CODE_3955 = '3955'  # Security clearance is provided via another channel 

MESSAGE_TEXT = {
    CODE_0030: 'Bank: {} \n Bank Account: {}  {}       \n     Download not executed,    use single downloading bank data',
    CODE_3040: 'Bank: {} \n Bank Account: {}  {}       \n     Download partially executed',
    'ACCOUNT_IBAN_MISSED': 'Check TABLE LEDGER_COA: {}, \n Assign valid IBAN to ledger account: {}, {}',
    'ACQUISITION_HEADER': '{}  ACQUISITION AMOUNT CHANGE {} in Period {} - {}',
    'ACQUISITION_AMOUNT': 'Bank: {} \n Bank Account: {}  {}  {}      \n     Acquisition Amount must be adjusted manually',
    'ALPHA_VANTAGE': 'DOWNLOAD Prices from ALPHA_VANTAGE ({}/{}) failed (see ERROR Message before)',
    'ALPHA_VANTAGE_REFRESH_RUN': 'AlphaVantage Functions Creation started',
    'ALPHA_VANTAGE_REFRESH': 'AlphaVantage Functions successfully created\ntest\ntest\ntest\ntest\ntest\ntest\ntest\ntest\ntest\ntest',
    'ALPHA_VANTAGE_ERROR': 'API Parameter Information not created',
    'ALPHA_VANTAGE_ERROR_MSG': 'AlphaVantage Error Message: \n{} \n\n Generated URl: \n{}',
    'ALPHA_VANTAGE_NO_DATA': 'AlphaVantage API returns no Data \n {}',
    'APP': 'APPLICATION and MARIDB Customizing Installation',
    'ASSINGNABLE_STATEMENTS': 'Assignable Statements for ledger in period {} to {}',
    'BALANCE_DIFFERENCE':   'Bank Account {} {}:  {}  \n Ledger Account {} {}:  {}  \n Balance Difference: {}',
    'BANK_CODE_EXIST': 'Bank Code exists',
    'BANK_DATA_ACCOUNTS_MISSED': 'BankCode {}: Accounts missed, Run Customizing',
    'BANK_DATA_NEW': 'Created {} ({}. Next Step: SYNCHRONIZE Bank \n\n Then restart application',
    'BANK_DATA_NEW_SCRAPER': 'Created {} ({})',
    'BANK_DELETED': 'DELETE BANK LOGIN DATA \nBankcode: {}',
    'BANK_DELETE_failed': 'DELETE BANK {} failed!! \n IBAN of bank exists in table {}',
    'BANK_LOGIN': 'Bank Scraper Login failed \nException: {} \nURL: {}\nPassword: {}\nUserName: {}',
    'BANK_PERIOD': '{} ({}) \n Bank Account: {} {}      \n Account Postings only available from {} onwards',
    'BMW_ZFA2': 'Please confirm the login process with your BMW Bank 2FA app',
    'BMW_ZFA2_REJECTED': 'login process not confirmed with your BMW Bank 2FA app; Login rejected',
    'CONNECT_IMAGE_ERROR': 'Image error, Could not load background image:\n {}',
    'CONNECT_MARIADB_ERROR': 'MariaDB connection error: {}',
    'CONNECT_MARIADB': 'MariaDb connected: {}',
    'CONNECT_SELECT_DB': 'Please select or specify a database.',
    'CONNECT_CREATE_DB': 'New database? \n The database {} does not exist.\n  Do you want to create it?',
    'CONNECT_DB_CREATED': 'Database {} created.',
    'CONNECT_CREATE_DB_ABORTED': 'Database creation aborted.',
    'CONNECT_DB_CONNECTED': 'Connected to database {}',
    'CREDENTIALS': '{} Login failed',
    'CREDENTIALS_CHECK': '{} Checking Credentials',
    'CHECKBOX': 'Select at least one of the Check Box Icons',
    'CONN': 'Database Connection failed  \nMariaDBuser: {} \nMariaDBname: {}',
    'DATA_INSERTED': '{}       Data inserted',
    'DATA_CHANGED': '{}       Data changed',
    'DATA_DELETED': '{}       Data deleted',
    'DATA_ROW_EXIST': '{}       Data Row exists',
    'DATA_NO': '{} \n{} \nData not available',
    'DATABASE': 'D A T A B A S E:  {}',
    'DATABASE_REFRESH': 'Database Credentials changed \n You must restart Banking',
    'DATE': '{} invalid or missing (Format e.g. 2020-12-12)',
    'DATE_ADJUSTED': 'Price_Date not in Table Holding \n Adjusted by existing previous Date',
    'DATE_TODAY': '{} Less todays date',
    'DATE_NO_WORKDAY': '{} is no  working day',
    'DBLOGIN': 'Database Connection failed! \n Check Database LOGIN Parameter in CUSTOMIZINDG Application/MariaDB',
    'DECIMAL': 'Invalid Decimal Format Field {} e.g. 12345.00',
    'DOWNLOAD_BANK':  'BANK: {}    Download Bank Data started',
    'DOWNLOAD_ACCOUNT': 'Bank: {} {}\n Bank Account: {}  {}       \n     Download Bank Data of Iban {}',
    'DOWNLOAD_ACCOUNT_NOT_ACTIVATED': 'Bank: {} {}\n Bank Account: {}  {}       \n     Download Bank Data of Iban {} not activated in LEDGER_COA',
    'DOWNLOAD_DONE': 'BANK: {}   Data downloading finished',
    'DOWNLOAD_NOT_DONE': 'BANK: {}   Data downloading finished with E R R O R ',
    'DOWNLOAD_REPEAT': 'Download {} canceled by User! \n\nStart Download once more!',
    'DOWNLOAD_RUNNING': '{} Data Download running',
    'EXCEL': 'Excel File {} created, sheet added',
    'ENTRY': 'Enter Data',
    'ENTRY_DATE': 'Entry_date missed',
    'FIELDLIST_MIN': 'Select at least {} positions in fieldlist',
    'FIXED': '{} MUST HAVE {} Characters ',
    'HELP_PANDASTABLE': 'Show Row Menu: \n          Select row\n          Click on row number with the right mouse button',
    'HELP_CHECK_UPLOAD': 'Start with FIRST row to be checked\n\n Show Row Menu: \n          Select row\n          Click on row number with the right mouse button\n          Then select Update Selected Row and UPDATE if the row and all previous rows are OK',
    'HITAN6': 'Bank: {} \n Bank Account: {}  {}       \n     Could not find HITAN6/7 task_reference',
    'HIKAZ':  'Response HIKAZ missing: bank_name {}, account_number {}, account_product_name {}',
    'HITAN': 'Security clearance is provided via another channel\n{}',
    'HITAN_MISSED': 'Response HITAN missing: bank_name {}, account_number {}, account_product_name {}',
    'HIUPD_EXTENSION': 'Bank: {} \n Bank Account: {}  {}       \n     IBAN {} received Bank Information: \n     {}',
    'HOLDING_INSERT': 'Holding data for date {} does not exist. Insert?',
    'HTTP': 'Server not connected! HTTP Status Code: {}\nBank: {}  Server: {}',
    'HTTP_INPUT': 'Server not valid or not available! HTTP Status Code: {}',
    'IBAN': 'IBAN invalid',
    'IBAN_USED': 'IBAN is already assigned to account {}',
    'IMPORT_CSV': 'Import CSV_File into Table {}',
    'ISIN_ALPHABETIC': 'Isin_code must start with an alphabetic character',
    'ISIN_DATA': 'Enter ISIN Data',
    'ISIN_IN_HOLDING': 'No deletion allowed \n {} ({}) \n Used in holding or transaction table',
    'ISDIGIT': 'Invalid Integer Field {}',
    'LEDGER_ACTIVATE': 'Ledger activated',
    'LEDGER_ROW': 'No additional statement data available for table row ',
    'LEDGER_STATEMENT_ASSIGMENT_EMPTY': 'There are no assignment statements for ledger IdNo {} and Ledger Account {}',
    'LEDGER_STATEMENT_ASSIGMENT_MISSED': 'Update and select new assignment (statement) of credit/debit accounts marked in red !',
    'LENGTH': '{} Exceeds Length OF {} Characters',
    'LOAD_DATA': 'Data imported if no message was displayed previously \nfrom File {}',
    'LOGGING_ACTIVE': 'Logging activated',
    'LOGGING_FILE': 'OS Error Logging_file',
    'LOGIN': 'LOGIN Data incomplete.   \nCustomizing e.g. synchronization LOGIN Data must be done \nBank_Code: {} (Key Error: {})',
    'LOGIN_SCRAPER': 'LOGIN Data incomplete.   \nCustomizing LOGIN Data/Scraping must be done \nBank: {} ({})',
    'MANDATORY': '{} is mandatory',
    'MARIADB_DUPLICATE': 'Duplicate Entry ignored\nSQL Statement: \n{} \n Error: \n{} \n Vars: \n{}',
    'MARIADB_ERROR_SQL': 'SQL_Statement\n {} \n\nVars\n {}',
    'MARIADB_ERROR': 'MariaDB Error\n{} \n {}',
    'MIN_LENGTH': '{} Must have a Length OF {} Characters',
    'NAME_INPUT': 'Enter Query Name (Name of Stored Procedure, allowed Chars [alphanumeric and _): ',
    'NAMING': 'Fix Naming. Allowed Characters: A-Z, a-z, 0-9, _',
    'NO_TURNOVER': 'Bank: {} \n Bank Account: {}  {}       \n     No new turnover',
    'NOTALLOWED': '{} Value not allowed, select from list \n {}',
    'SHELVE_NAME_MISSED': 'Shelve name  {} not found',
    'PAIN': 'SEPA Format pain.001.001.03 not found/allowed\nBank: {}',
    'PERIOD':               'Period ({}, {})',
    'PIN': 'PIN missing! \nBank: {} ({})',
    'PIN_INPUT': 'Enter PIN   {} ({}) ',
    'PRICES_DELETED': '{}:  Prices deleted\n\n Used Ticker Symbol {} \n ISIN: {}',
    'PRICES_LOADED': '{}:  Price loaded for Period {}\n\n Used Ticker Symbol {} \n ISIN: {}',
    'PRICES_ALREADY': '{}:  No new Prices found\n\n Used Ticker Symbol {} {}\n ISIN: {}  {} \n Prices already available until {}',
    'PRICES_NO': '{}:  No new Prices found\n\n Used Ticker Symbol {} {}\n ISIN: {}  {}',
    'PRODUCT_ID': 'Product_ID missing, No Bank Access possible\n Get your Product_Id: https://www.hbci-zka.de/register/prod_register.htm',
    'RADIOBUTTON': 'Select one of SELECT the RadioButtons',
    'RESPONSE': 'Got unvalid response from bank',
    'SCRAPER_BALANCE': 'Last closing balance from database: {} \n Opening balance from the transaction overview: {}',
    'SCRAPER_NO_TRANSACTION_TO_STORE': '{} {} All transactions already saved in database',
    'SCRAPER_PAGE_ERROR': 'Connection interrupted!',
    'SCRAPER_SELENIUM_EXCEPTION': 'An error occurred:\n  Error type: {}\n  Error message: {}',
    'SCRAPER_TIMEOUT': 'Connection TimeOut',
    'SCROLL': 'Scroll forward: CTRL+RIGHT   Scroll backwards: CTRL+LEFT',
    'SEGMENT_VERSION': 'Segment {}{} Version {} not implemented',
    'SELECT': 'Enter your Selection',
    'SELECT_ROW': 'Select row, then right clicking on row number',
    'SEPA_CRDT_TRANSFER': 'SEPA Credit Transfer \nBank:    {}  \nAccount:    {} ({})',
    'SQLALCHEMY_ERROR': "Error Calling SQLAlchemy {}:    {}",
    'SHELVE': '\n LOGON Data, Synchronization Data >>>>> BANK: {}\n\n',
    'STACK': '\n\n LINE\n {} \n        MODULE  {}\n        METHOD {}',
    'SYMBOL_MISSING_ALL': '{} \n \n No ticker/symbol found in Table ISIN. \n You must add ticker symbols in Table ISIN',
    'SYMBOL_MISSING': 'No ticker/symbol (symbol_origin) found. \n ISIN: {}  /  {} \n\n You must add ticker symbol in Table ISIN',
    'SYMBOL_USED': 'Symbol already used in {}',
    'SYNC': 'Synchronization Data incomplete    \nSynchronization must be done \nBank: {} ',
    'SYNC_START': 'Next Stepp: You must start Synchronization Bank: {} ',
    'TA_OTHER_PARAMETER': 'function contains additional parameters: \n  {}',
    'TA_NO_RESULT': 'Technical Analysis no result!\n Category: {}  Indicator: {}',
    'TA_METHOD_ERROR': 'Indicator {}: Name creation of the calling method not successful',
    'TA_CLASS_NO_METHOD': 'Category: {} \nMethods in class {} not found',
    'TA_NO_OHLC': 'Category: {} \n No OHCL Series parameter of Class {}',
    'TASK_DONE': 'Task finished.',
    'TASK_WARNING': 'Finished with Warnings',
    'TASK_STARTED': '{}: Task started.',
    'TAN_INPUT': 'Enter TAN  {} ({}): ',
    'TAN_CANCEL': 'Input TAN canceled, request aborted',
    'TERMINATION': 'FinTS MariaDB Banking Termination',
    'THREAD': 'Task {} aborted. No Dialogue. Its no mainthread',
    'THREADING_ACTIVE': 'Threading activated',
    'TRANSACTION_CHECK': '{} Difference Pieces of Transactions / Pieces of Portfolio',
    'TRANSACTION_CLOSED_EMPTY': ' No Closed Transactions in Period {} - {}',
    'TRANSACTION_HEADER_SYNC_TABLE': 'SYNCHRONIZE TRANSACTIONS',
    'TRANSACTION_NO': ' No Transactions in Period {} - {}',
    'TRANSACTION_PIECES_NEGATIVE': 'Transactions faulty! On {} cumulated Pieces negative!',
    'TRANSACTION_PIECES_PORTFOLIO': ' Difference Pieces of Transactions / Pieces of Portfolio',
    'TRANSACTION_TITLE': '{}  TRANSACTIONS  {} ',
    'TWOSTEP': 'Select one of the Security Functions \n Only Two-Step TAN Procedure \n SCA Strong Customer Authentication',
    'UNEXCEPTED_ERROR': 'E X C E P T I O N    E R R O R  !\n\nMODULE: {}\n\nLINE  of EXCEPTION ERROR Call: {}\n\nMETHOD: {}\n\nTYPE:\n {} \n\nVALUE:  {} \n\nTRACEBACK:\n {}',
    'VERSION_TRANSACTION': 'TRANSACTION HK{}{} not available',
    'WEBDRIVER': 'Installing {} WEB Driver failed\n\n{}',
    'WEBDRIVER_INSTALL': '{} WEB Driver installed to project.root/.wdm'
}

"""
--------------------------- FinTS --------------------------------------------------
"""
SYSTEM_ID_UNASSIGNED = '0'
CUSTOMER_ID_ANONYMOUS = '9999999999'
DIALOG_ID_UNASSIGNED = '0'
PRODUCT_ID = 'Not Valid'
VERSION_TRANSACTION = ['HKAKZ6', 'HKAKZ7',
                       'HKSAL6', 'HKSAL7', 'HKWPD5', 'HKWPD6']
"""
 ------------------Shelve_Files------------------------------------------------
"""
KEY_DIRECTORY = 'DIRECTORY'
KEY_DRIVER = 'DRIVER'
MARIADB_NAME = 'MARIADB_NAME'
MARIADB_USER = 'MARIADB_USER'
MARIADB_PASSWORD = 'MARIADB_PASSWORD'
MARIADB_HOST = 'MARIADB_HOST'
KEY_ALPHA_VANTAGE_PRICE_PERIOD = 'ALPHA_VANTAGE_PRICE_PERIOD'
KEY_SHOW_MESSAGE = 'SHOW_MESSAGE'
KEY_LOGGING = 'LOGGING'
KEY_THREADING = 'THREADING'

KEY_ALPHA_VANTAGE_FUNCTION = 'ALPHA_VANTAGE_FUNCTION'
KEY_ALPHA_VANTAGE_PARAMETER = 'ALPHA_VANTAGE_PARAMETER'
KEY_LEDGER = 'LEDGER'
KEY_RESET_SCREENSIZE = 'KEY_RESET_SCREENSIZE'


TRUE = 1
FALSE = 0
"""
SWITCH = [TRUE, FALSE]
"""
KEY_ACCOUNTS = 'ACCOUNTS'
KEY_BANK_CODE = 'BANK_CODE'
KEY_BANK_NAME = 'BANK_NAME'
KEY_BPD = 'BPD_VERSION'
KEY_PIN = 'PIN'
KEY_BIC = 'BIC'
KEY_SECURITY_FUNCTION = 'SECURITY_FUNCTION'
KEY_VERSION_TRANSACTION = 'VERSION_TRANSACTION'
KEY_VERSION_TRANSACTION_ALLOWED = 'VERSION_TRANSACTION_ALLOWED'
KEY_SEPA_FORMATS = 'SUPPORTED_SEPA_FORMATS'
KEY_SERVER = 'SERVER'
KEY_IDENTIFIER_DELIMITER = 'KEY_IDENTIFIER_DELIMITER'
KEY_DOWNLOAD_ACTIVATED = 'DOWNLOAD_ACTIVATED'
KEY_STORAGE_PERIOD = 'STORAGE_PERIOD'
KEY_SYSTEM_ID = 'SYSTEM_ID'
KEY_TAN = 'TAN'
KEY_TWOSTEP = 'TWOSTEP_PARAMETERS'
KEY_UPD = 'UPD_VERSION'
KEY_USER_ID = 'USER_ID'
KEY_MIN_PIN_LENGTH = 'MIN_PIN_LENGTH'
KEY_MAX_PIN_LENGTH = 'MAX_PIN_LENGTH'
KEY_MAX_TAN_LENGTH = 'MAX_TAN_LENGTH'
KEY_TAN_REQUIRED = 'TRANSACTION_TANS_REQUIRED'
SHELVE_KEYS = [
    KEY_BANK_CODE, KEY_BANK_NAME, KEY_USER_ID, KEY_PIN, KEY_BIC,
    KEY_SERVER, KEY_IDENTIFIER_DELIMITER, KEY_DOWNLOAD_ACTIVATED, KEY_SECURITY_FUNCTION, KEY_VERSION_TRANSACTION,
    KEY_VERSION_TRANSACTION_ALLOWED,
    KEY_SEPA_FORMATS, KEY_SYSTEM_ID,
    KEY_TWOSTEP, KEY_ACCOUNTS, KEY_UPD, KEY_BPD, KEY_STORAGE_PERIOD,
    KEY_MIN_PIN_LENGTH, KEY_MAX_PIN_LENGTH, KEY_MAX_TAN_LENGTH, KEY_TAN_REQUIRED,

]
MIN_PIN_LENGTH = 3
MAX_PIN_LENGTH = 20
MAX_TAN_LENGTH = 20
MIN_TAN_LENGTH = 1
"""
 ------------------ACCOUNTS Field Keys in Shelve_Files------------------------------------------------
"""
KEY_ACC_IBAN = 'IBAN'
KEY_ACC_ACCOUNT_NUMBER = 'ACCOUNT_NUMBER'
KEY_ACC_SUBACCOUNT_NUMBER = 'SUBACCOUNT_NUMBER'
KEY_ACC_BANK_CODE = 'BANK_CODE'
KEY_ACC_CUSTOMER_ID = 'CUSTOMER_ID'
KEY_ACC_TYPE = 'TYPE'
KEY_ACC_CURRENCY = 'CURRENCY'
KEY_ACC_OWNER_NAME = 'OWNER_NAME'
KEY_ACC_PRODUCT_NAME = 'PRODUCT_NAME'
KEY_ACC_ALLOWED_TRANSACTIONS = 'ALLOWED_TRANSACTIONS'
KEY_ACC_KEYS = [
    KEY_ACC_IBAN, KEY_ACC_ACCOUNT_NUMBER, KEY_ACC_ALLOWED_TRANSACTIONS,
    KEY_ACC_BANK_CODE, KEY_ACC_CURRENCY, KEY_ACC_CUSTOMER_ID, KEY_ACC_OWNER_NAME,
    KEY_ACC_PRODUCT_NAME, KEY_ACC_SUBACCOUNT_NUMBER, KEY_ACC_TYPE
]
"""
-------------------HBCI Server ---------------------------------------------------
"""
HTTP_CODE_OK = [200, 405]
"""
---------------------------- S.W.I.F.T. Formats MT940, MT535, MT536 -------------
"""
ORIGIN = '_BANKDATA_'
ORIGIN_LEDGER = '_LEDGER_'  # data source: ledger database
# data source: update market_price, total_amount and total_amount_portfolio in table holding  from table prices
ORIGIN_PRICES = '_PRICES_'
# data source: inserted if holding position is missing during update from prices
ORIGIN_INSERTED = '_INSERTED_'
ORIGIN_BANKDATA_CHANGED = '_BANKDATA_CHANGED_'
ORIGINS = [ORIGIN, ORIGIN_LEDGER]
DEBIT = 'D'
CREDIT = 'C'
PERCENT = 'PCT'
EURO = 'EUR'
CURRENCY = [EURO]  # table statement and holding (prices see below)
CURRENCY_EXTENDED = CURRENCY
# table statement and holding (prices see below) exteneded by PCT (bonds)
CURRENCY_EXTENDED.append(PERCENT)
CURRENCIES = [EURO, PERCENT, 'USD', 'CHF']
FAMT = 'FAMT'
UNIT = 'UNIT'
TYPES = [FAMT, UNIT]
TRANSACTION_RECEIPT = 'RECE'
TRANSACTION_DELIVERY = 'DELI'
TRANSACTION_TYPES = [TRANSACTION_RECEIPT, TRANSACTION_DELIVERY]
SEPA_TRANSFER_APPLCANT_NAMES = ['ÜBERWEISUNG', 'überweisung', 'EURO-ÜBERWEISUNG',
                                'EURO-Überweisung', 'EU-ÜBERWEISUNG', 'Online-Überweisung', ]
"""
--------------- ISIN field values -------------
"""
YAHOO = 'Yahoo!'
ALPHA_VANTAGE = 'AlphaVantage'
ONVISTA = 'Onvista'
ORIGIN_SYMBOLS = [NOT_ASSIGNED, ALPHA_VANTAGE, YAHOO]
CURRENCIES = [EURO, 'USD', 'AUD', 'CAD', 'CHF',
              'GBP', 'JPY']  # ISIN currency of prices
"""
--------------- Alpha Vantage field values -------------
"""
JSON_KEY_ERROR_MESSAGE = 'Error Message'
JSON_KEY_META_DATA = 'Meta Data'
TIME_SERIES_DAILY = 'TIME_SERIES_DAILY'
TIME_SERIES_DAILY_ADJUSTED = 'TIME_SERIES_DAILY_ADJUSTED'
TIME_SERIES_INTRADAY = 'TIME_SERIES_INTRADAY'
TIME_SERIES_WEEKLY = 'TIME_SERIES_WEEKLY'
TIME_SERIES_WEEKLY_ADJUSTED = 'TIME_SERIES_WEEKLY_ADJUSTED'
TIME_SERIES_MONTHLY = 'TIME_SERIES_MONTHLY'
TIME_SERIES_WEEKLY_ADJUSTED = 'TIME_SERIES_WEEKLY_ADJUSTED'
ALPHA_VANTAGE_PRICE_PERIOD = [TIME_SERIES_INTRADAY,
                              TIME_SERIES_DAILY, TIME_SERIES_DAILY_ADJUSTED,
                              TIME_SERIES_WEEKLY, TIME_SERIES_WEEKLY_ADJUSTED,
                              TIME_SERIES_MONTHLY, TIME_SERIES_WEEKLY_ADJUSTED]
ALPHA_VANTAGE_REQUIRED = ['symbol', 'interval', 'keywords', 'from_currency', 'to_currency', 'from_symbol',
                          'to_symbol', 'market', 'time_period', 'series_type']
ALPHA_VANTAGE_REQUIRED_COMBO = {'interval': ['1min', '5min', '15min', '30min', '60min', 'daily', 'weekly', 'monthly'],
                                'time_period': [60, 200],
                                'series_type': ['close', 'open', 'high', 'low']
                                }
ALPHA_VANTAGE_OPTIONAL_COMBO = {'outputsize': ['compact', 'full']}

"""
-------------------------- Formbuilts -----------------------------------------------
"""
ENTRY = 'Entry'
COMBO = 'ComboBox'
CHECK = 'CheckButton'
TEXT = 'Text'

BUTTON_ALPHA_VANTAGE = 'ALPHA_VANTAGE'
BUTTON_APPEND = 'APPEND'
BUTTON_CREDIT = 'SHOW CREDIT'
BUTTON_CREATE = 'CREATE'
BUTTON_COPY = 'COPY'
BUTTON_DEBIT = 'SHOW DEBIT'
BUTTON_DELETE = 'DELETE'
BUTTON_DELETE_ALL = 'DELETE ALL'
BUTTON_DATA = 'DATA'
BUTTON_INIT = 'INIT'
BUTTON_PRICES_IMPORT = 'IMPORT PRICES'
BUTTON_NEXT = 'NEXT'
BUTTON_NEW = 'NEW'
BUTTON_OK = 'OK'
BUTTON_PRINT = 'PRINT'
BUTTON_PREVIOUS = 'PREVIOUS'
BUTTON_QUIT = 'QUIT'
BUTTON_QUIT_ALL = 'QUIT ALL'
BUTTON_REPLACE = 'REPLACE'
BUTTON_RESTORE = 'RESTORE'
BUTTON_SAVE = 'SAVE'
BUTTON_SAVE_STANDARD = 'SAVE as Standard'
BUTTON_SELECT_ALL = 'SELECT All'
BUTTON_SELECT = 'SELECT'
BUTTON_STANDARD = 'STANDARD'
BUTTON_STORE = 'STORE'
BUTTON_UPDATE = 'UPDATE'

COLOR_ERROR = 'red'
COLOR_NOT_ASSIGNED = 'cyan'
COLOR_NEGATIVE = 'darkorange'
COLOR_HOLDING = 'yellow'
COLUMN_FORMATS_LEFT = 'LEFT'
COLUMN_FORMATS_RIGHT = 'RIGHT'
COLUMN_FORMATS_CURRENCY = 'CURRENCY'
COLUMN_FORMATS_COLOR_NEGATIVE = 'COLOR_NEGATIVE'
STANDARD = 'STANDARD'
FORMAT_FIXED = 'F'
FORMAT_VARIABLE = 'V'
TYP_ALPHANUMERIC = 'X'
TYP_DECIMAL = 'D'

TYP_DATE = 'DAT'

# package pandastable: standard values  (see class table self.font and self.fontsize
ROOT_WINDOW_POSITION = '+100+100'
BUILTBOX_WINDOW_POSITION = '+200+200'
BUILTPANDASBOX_WINDOW_POSITION = '+1+1'
BUILTEXT_WINDOW_POSITION = '+400+0'
WIDTH_WIDGET = 70
WIDTH_CANVAS = 700
HEIGHT_CANVAS = 800
PANDAS_NAME_SHOW = 'SHOW'
PANDAS_NAME_ROW = 'ROW'

WM_DELETE_WINDOW = 'WM_DELETE_WINDOW'
LIGHTBLUE = 'LIGHTBLUE'
UNDEFINED = 'UNDEFINED'
FONTSIZE = 8
MAX_FIELD_LENGTH = 65

"""
-------------------------- Forms -----------------------------------------------
"""
WIDTH_TEXT = 170
HEIGHT_TEXT = 60
HEADER = 'HEADER'
INFORMATION = 'INFORMATION '
WARNING = 'WARNING     '
ERROR = 'ERROR       '
LIGHTBLUE = 'LIGHTBLUE'
SHOW_MESSAGE = [INFORMATION, WARNING, ERROR]
FN_ACCOUNT_NAME = 'ACCOUNT_NAME'
FN_COMPARATIVE = 'COMPARATIVE_VALUE'
FN_DATE = 'DATE'
FN_TO_DATE = 'TO_DATE'
FN_FROM_DATE = 'FROM_DATE'
FN_BANK_NAME = 'BANK_NAME'
FN_FIELD_NAME = 'Field_Name'
FN_PROCUDURE_NAME = 'Procedure_Name'
FN_PERCENTAGE = 'Percentage'
FN_Y_AXE = 'Y_AXE'
FN_DATA_MODE = 'DATA_MODE'
FN_SHARE = 'SHARE'
FN_INDEX = 'INDEX'
FN_PROPORTIONAL = 'PROPORTIONAL'
FN_ABSOLUTE = 'ABSOLUTE'
FN_TOTAL = 'TOTAL'
FN_TOTAL_PERCENT = '% TOTAL'
FN_PERIOD_PERCENT = 'PERIOD'
FN_DAILY_PERCENT = 'Day'
FN_PROFIT = 'Profit'
FN_PROFIT_LOSS = 'PROFIT_LOSS'
FN_PROFIT_CUM = 'PERFORMANCE'
FN_PIECES_CUM = 'CUM_PIECES'
FN_SOLD_PIECES = 'sold_pieces'
FN_ALL_BANKS = 'ALL BANKS '
FN_CREDIT = 'CREDIT'
FN_DEBIT = 'DEBIT'
FN_BALANCE = 'BALANCE'
FN_COLUMNS_EURO = [FN_TOTAL, FN_PROFIT,
                   FN_PROFIT_LOSS, FN_PROFIT_CUM,
                   FN_BALANCE, FN_CREDIT, FN_DEBIT]
FN_COLUMNS_PERCENT = [FN_TOTAL_PERCENT,
                      FN_PERIOD_PERCENT, FN_DAILY_PERCENT]
Y_AXE_PROFIT = 'profit'
Y_AXE = ['market_price', 'acquisition_price', 'pieces',
         'total_amount', 'acquisition_amount', Y_AXE_PROFIT]
SEPA_CREDITOR_NAME = 'Creditor_Name'
SEPA_CREDITOR_IBAN = 'Creditor_IBAN'
SEPA_CREDITOR_BIC = 'Creditor_BIC'
SEPA_CREDITOR_BANK_NAME = 'Creditor_Bank_Name'
SEPA_CREDITOR_BANK_LOCATION = 'CREDITOR_Bank_Location'
SEPA_AMOUNT = 'Amount'
SEPA_PURPOSE = 'Purpose'
SEPA_PURPOSE_1 = 'Purpose_1'
SEPA_PURPOSE_2 = 'Purpose_2'
SEPA_REFERENCE = 'Reference'
SEPA_EXECUTION_DATE = 'Execution_Date'
NOTPROVIDED = 'NOTPROVIDED'
"""
-------------------------- BuilPandasBox param mode
"""
EDIT_ROW = 'EDIT_ROW'
CURRENCY_SIGN = 'CURRENCY_SIGN'
NUMERIC = 'NUMERIC'
NO_CURRENCY_SIGN = 'NO_CURRENCY_SIGN'
"""
---------------  MT940 Field 86 identifiers in element PURPOSE (>identifier sub-field< :  >MARIADB column name<)-----------------------------------------------------
"""
IDENTIFIER = {
    'EREF': 'end_to_end_reference',
    'BREF': 'bank_reference',
    'KREF': 'customer_reference',
    'CREF': 'customer_reference',
    'MREF': 'mandate_id',
    'PREF': 'payment_reference',
    'CRED': 'creditor_id',
    'DEBT': 'debitor_id',
    'ORDP': 'ordering_party',
    'BENM': 'beneficiary',
    'ULTC': 'ultimate_creditor',
    'ULTD': 'ultimate_debtor',
    'REMI': 'remittance_information',
    'PURP': 'purpose_code',
    'RTRN': 'return_reason',
    'RREF': 'return_reference',
    'ACCW': 'counterparty_account',
    'IBK': 'intermediary_bank',
    'OCMT': 'original_amount',
    'OAMT': 'original_amount',
    'COAM': 'compensation_amount',
    'CHGS': 'charges',
    'EXCH': 'exchange_rate',
    'IBAN': 'applicant_iban',
    'BIC': 'applicant_bic',
    'ABWA': 'different_client',
    'ABWE': 'different_receiver',
    'ANAM': 'applicant_name',
    'SVWZ': 'sepa_purpose'
}
"""
----------------------------- Scraper ------------

    Adding new bank scraper routines or changing login Link -->  reload server table:

            CUSTOMIZINGG
                Import Server CSV-File
"""
BMW_BANK_CODE = '70220300'
# value: [>login Link<, >identifier_delimiter<, >storage_period<]
SCRAPER_BANKDATA = {BMW_BANK_CODE: [
    'https://ebanking.bmwbank.de/eBankingClient', '+', 360]}
"""
----------------------------- Named Tuples ------------
"""
Balance = namedtuple(
    'Balance', ' '.join([KEY_ACC_BANK_CODE, KEY_ACC_ACCOUNT_NUMBER, KEY_ACC_PRODUCT_NAME, DB_entry_date.upper(),
                         DB_closing_status, DB_closing_balance, DB_closing_currency,
                         DB_opening_status, DB_opening_balance, DB_opening_currency]))
"""
----------------------------- DataClasses ------------
"""


@dataclass
class Caller:
    """
    Used to remember window position
    (see formbuilt.py  methods geometry_get, geometry_put)
    Contains class name of calling Class)
    """
    caller: str


@dataclass
class ToolbarSwitch:
    """
    Switch Toolbar True/False

    See class ToolBarBanking

    True: Show Banking Toolbar
        Used to suppress formatting amounts with currency sign
        (see formbuilt.py  Class BuiltPandasBox)

    False: Hidden Banking Toolbar
    """
    toolbar_switch = True


@dataclass
class HoldingAcquisition:
    price_date: date
    price_currency: str = field(default=EURO)
    market_price: Decimal = field(default=0)
    acquisition_price: Decimal = field(default=0)
    pieces: Decimal = field(default=0)
    amount_currency: str = field(default=EURO)
    total_amount: Decimal = field(default=0)
    acquisition_amount: Decimal = field(default=0)
    origin: str = field(default=0)


class Informations(object):
    """
    Threading
    Downloading Bankdata using FinTS
    Container of messages, responses of banks, errors
    """
    bankdata_informations = ''
    BANKDATA_INFORMATIONS = 'BANKDATA INFORMATIONS'

    """
    Threading
    Download prices from Yahoo! or Alpha Vantage
    Container öf messages, errors
    """
    prices_informations = ' '
    PRICES_INFORMATIONS = 'PRICES_INFORMATIONS'

    """
    Update prices in holding from Yahoo! or Alpha Vantage
    Container öf messages, errors
    """
    holding_informations = ' '
    HOLDING_INFORMATIONS = 'HOLDING_INFORMATIONS'
