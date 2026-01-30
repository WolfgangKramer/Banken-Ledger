"""
Created on 18.11.2019
__updated__ = "2026-01-30"
@author: Wolfgang Kramer
"""


import re
import webbrowser
from datetime import date
from random import randint
from banking.mariadb import MariaDB
from banking.declarations import (
    CUSTOMER_ID_ANONYMOUS,
    DIALOG_ID_UNASSIGNED,
    HTTP_CODE_OK,
    KEY_USER_ID, KEY_PIN, KEY_BIC, KEY_BANK_NAME, KEY_VERSION_TRANSACTION,
    KEY_SERVER, KEY_SECURITY_FUNCTION, KEY_SEPA_FORMATS, KEY_SYSTEM_ID,
    KEY_BPD, KEY_UPD, KEY_STORAGE_PERIOD, KEY_TWOSTEP, KEY_ACCOUNTS, KEY_SUPPORTED_CAMT_MESSAGE,
    PRODUCT_ID, PNS,
    SCRAPER_BANKDATA,
    SHELVE_KEYS, SYSTEM_ID_UNASSIGNED,
)
from banking.declarations_mariadb import DB_product_id
from banking.dialog import Dialogs
from banking.message_handler import (
    get_message,
    MESSAGE_TEXT,
    MessageBoxError, MessageBoxInfo
    )
from banking.forms import InputPIN

from banking.utils import application_store, http_error_code


class InitBank(object):
    """
    Data Bank Dialogue
    """

    def __init__(self, bank_code):

        mariadb = MariaDB()
        self.scraper = False
        self.bank_code = bank_code
        shelve_file = mariadb.shelve_get_key(
            bank_code, SHELVE_KEYS, none=False)
        try:
            self.user_id = shelve_file[KEY_USER_ID]
            if KEY_PIN in shelve_file.keys() and shelve_file[KEY_PIN] not in ['', None]:
                PNS[bank_code] = shelve_file[KEY_PIN]
            self.bic = shelve_file[KEY_BIC]
            self.server = shelve_file[KEY_SERVER]
            self.bank_name = shelve_file[KEY_BANK_NAME]
            self.accounts = shelve_file[KEY_ACCOUNTS]
        except KeyError as key_error:
            MessageBoxError(
                message=get_message(MESSAGE_TEXT, 'LOGIN', self.bank_code, key_error))
            return None  # thread checking
        http_code = http_error_code(self.server)
        if http_code not in HTTP_CODE_OK:
            MessageBoxError(message=get_message(MESSAGE_TEXT, 'HTTP', http_code,
                                                self.bank_code, self.server))
            webbrowser.open(self.server)
            return None  # thread checking
        if bank_code in list(SCRAPER_BANKDATA.keys()):
            MessageBoxError(
                message=get_message(MESSAGE_TEXT, 'LOGIN_SCRAPER', '', self.bank_code))
            return None  # thread checking
        else:
            self.dialogs = Dialogs()
            try:
                self.security_function = shelve_file[KEY_SECURITY_FUNCTION]
            except KeyError as key_error:
                MessageBoxError(
                    message=get_message(MESSAGE_TEXT, 'LOGIN', self.bank_code, key_error))
                return None  # thread checking
            # Checking / Installing FINTS server connection
            # register product:
            # https://www.hbci-zka.de/register/prod_register.htm
            self.product_id = application_store.get(DB_product_id)
            if self.product_id == '':
                MessageBoxInfo(message=get_message(MESSAGE_TEXT, 'PRODUCT_ID'))
                self.product_id = PRODUCT_ID
            # Getting Sychronisation Data
            try:
                #    Bank Parameter Data BPD
                self.system_id = shelve_file[KEY_SYSTEM_ID]
                try:
                    self.supported_camt_messages = shelve_file[KEY_SUPPORTED_CAMT_MESSAGE]
                except KeyError:
                    self.supported_camt_messages = None
                for sepa_format in shelve_file[KEY_SEPA_FORMATS]:
                    if re.search('pain.001.001.03', sepa_format):
                        self.sepa_descriptor = sepa_format
                        break
                if not self.sepa_descriptor:
                    MessageBoxError(
                        message=get_message(MESSAGE_TEXT, 'PAIN', self.bank_code))
                    return None  # thread checking
                self.security_identifier = shelve_file[KEY_SYSTEM_ID]
                self.bpd_version = shelve_file[KEY_BPD]
                self.transaction_versions = shelve_file[KEY_VERSION_TRANSACTION]
                self.storage_period = shelve_file[KEY_STORAGE_PERIOD]
                self.twostep_parameters = shelve_file[KEY_TWOSTEP]
                #    User Parameter Data UPD
                self.upd_version = shelve_file[KEY_UPD]
            except KeyError:
                MessageBoxError(
                    message=get_message(MESSAGE_TEXT, 'SYNC', self.bank_code))
                return None  # thread checking
            # Setting Dialog Variables
            self.message_number = 1
            self.task_reference = None
            self.tan_process = 4
            self.security_reference = randint(10000, 99999)
            self.dialog_id = DIALOG_ID_UNASSIGNED
            self.opened_bank_code = None

        self.sepa_credit_transfer_data = None
        self.sca = True
        self.challenge_hhduc = None
        self.challenge = ''
        self.warning_message = False
        self.iban = None
        self.account_number = None
        self.account_product_name = ''
        self.subaccount_number = None
        self.statement_mt940 = False  # Download Format of Statements  MT940 (Segment HKKAZ allowed)
        self.statement_camt = False  # Download Format of Statements   CAMT (Segment HKCAZ allowed)
        self.owner_name = ''
        self.period_message = False  # true if period message was displayed (segment.py)
        self.from_date = date.today()
        self.to_date = date.today()


class InitBankSync(object):
    """
    Data Bank Synchronization
    """

    def __init__(self, bank_code):

        mariadb = MariaDB()
        self.bank_code = bank_code
        self.scraper = False
        shelve_keys = [KEY_USER_ID, KEY_PIN, KEY_BIC, KEY_BPD, KEY_SERVER,
                       KEY_SECURITY_FUNCTION]
        shelve_file = mariadb.shelve_get_key(
            bank_code, shelve_keys, none=False)
        try:
            self.user_id = shelve_file[KEY_USER_ID]
            if KEY_PIN in shelve_file.keys() and shelve_file[KEY_PIN] not in ['', None]:
                PNS[bank_code] = shelve_file[KEY_PIN]
            self.bic = shelve_file[KEY_BIC]
            self.server = shelve_file[KEY_SERVER]
            self.security_function = shelve_file[KEY_SECURITY_FUNCTION]
            self.bpd_version = shelve_file[KEY_BPD]
        except KeyError as key_error:
            MessageBoxError(
                message=get_message(MESSAGE_TEXT, 'LOGIN', self.bank_code, key_error))
            return None  # thread checking
        if bank_code not in PNS.keys():
            try:
                inputpin = InputPIN(bank_code)
                PNS[bank_code] = inputpin.pin
            except TypeError:
                MessageBoxError(
                    message=get_message(MESSAGE_TEXT, 'PIN', '', self.bank_code))
                return None  # thread checking
        # register product: https://www.hbci-zka.de/register/prod_register.htm
        self.product_id = application_store.get(DB_product_id)
        if self.product_id == '':
            MessageBoxInfo(message=get_message(MESSAGE_TEXT, 'PRODUCT_ID'))
            self.product_id = PRODUCT_ID
        # Checking / Installing FINTS server connection
        http_code = http_error_code(self.server)
        if http_code not in HTTP_CODE_OK:
            MessageBoxError(message=get_message(MESSAGE_TEXT, 'HTTP', http_code,
                                                self.bank_code, self.server))
            webbrowser.open(self.server)
            return None  # thread checking
        # Init Sychronization Data
        self.system_id = SYSTEM_ID_UNASSIGNED
        self.security_identifier = '0'
        self.bank_name = None
        self.transaction_versions = shelve_file[KEY_VERSION_TRANSACTION]
        self.storage_period = 90
        self.twostep_parameters = []
        self.upd_version = mariadb.shelve_get_key(bank_code, KEY_UPD)
        if not self.upd_version:
            self.upd_version = 0
            self.accounts = []
        else:
            self.accounts = mariadb.shelve_get_key(bank_code, KEY_ACCOUNTS)
        # Setting Dialog Variables
        self.message_number = 1
        self.task_reference = None
        self.tan_process = 4
        self.security_reference = randint(10000, 99999)
        self.iban = None
        self.account_number = None
        self.account_product_name = ''
        self.subaccount_number = None
        self.from_date = date.today()
        self.dialog_id = DIALOG_ID_UNASSIGNED
        self.warning_message = False
        self.dialogs = Dialogs()


class InitBankAnonymous(object):
    """
    Data Bank Anonymous Dialogue
    """

    def __init__(self, bank_code):

        mariadb = MariaDB()
        # Dialog Identification
        self.bank_code = bank_code
        self.scraper = False
        self.user_id = CUSTOMER_ID_ANONYMOUS
        self.server = mariadb.shelve_get_key(bank_code, KEY_SERVER)
        if self.server in [None, '']:
            MessageBoxError(
                message=get_message(MESSAGE_TEXT, 'LOGIN', self.bank_code, KEY_SERVER))
            return None  # thread checking
        # register product: https://www.hbci-zka.de/register/prod_register.htm
        self.product_id = application_store.get(DB_product_id)
        if self.product_id in [None, '']:
            MessageBoxInfo(message=get_message(MESSAGE_TEXT, 'PRODUCT_ID'))
            self.product_id = PRODUCT_ID
        # Checking / Installing FINTS server connection
        http_code = http_error_code(self.server)
        if http_code not in HTTP_CODE_OK:
            MessageBoxError(message=get_message(MESSAGE_TEXT, 'HTTP', http_code,
                                                self.bank_code, self.server))
            webbrowser.open(self.server)
            return None  # thread checking
        # Init Sychronization Data
        self.system_id = SYSTEM_ID_UNASSIGNED
        self.security_identifier = '0'
        self.security_function = None
        self.bpd_version = 0
        self.bank_name = None
        self.twostep_parameters = []
        self.upd_version = mariadb.shelve_get_key(bank_code, KEY_UPD)
        if not self.upd_version:
            self.upd_version = 0
            self.accounts = []
        else:
            self.accounts = mariadb.shelve_get_key(bank_code, KEY_ACCOUNTS)
        # Setting Dialog Variables
        self.message_number = 1
        self.task_reference = None
        self.tan_process = 4
        self.security_reference = randint(10000, 99999)
        self.warning_message = False
        self.dialogs = Dialogs()
