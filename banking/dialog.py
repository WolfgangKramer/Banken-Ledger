"""
Created on 18.11.2019
__updated__ = "2025-06-14"
@author: Wolfgang Kramer
"""

import base64
import io
import json
import logging
import re
import requests
import xmltodict
import xml.dom.minidom as minidom

from decimal import Decimal
from typing import Any, List, Union
from datetime import date
from operator import itemgetter
from fints.message import FinTSInstituteMessage
from fints.segments.accounts import HISPAS1
from fints.segments.auth import (
    HITAN6, HITAN7, HITANS1, HITANS2, HITANS3, HITANS4, HITANS5, HITANS6, HITANS7, HIPINS1
)
from fints.segments.bank import HIBPA3, HIUPA4, HIUPD6
from fints.segments.depot import HIWPD5, HIWPD6
from fints.segments.dialog import HISYN4, HIRMG2, HIRMS2
from fints.segments.message import HNHBK3
from fints.segments.statement import HIKAZ6, HIKAZ7, HICAZ1
from fints.utils import Password
from mt940.models import Transactions

from banking.mariadb import MariaDB
from banking.declarations_mariadb import (
    STATEMENT, TABLE_FIELDS,
    DB_amount, DB_currency, DB_entry_date, DB_date,
    DB_camt,
    DB_show_messages, DB_logging,
    DB_status, DB_bank_reference, DB_posting_text,
    DB_end_to_end_reference, DB_mandate_id, DB_purpose_code, DB_applicant_name,
    DB_applicant_iban, DB_applicant_bic,
    DB_id, DB_transaction_code, DB_prima_nota, DB_remittance_information, DB_purpose,
    DB_opening_balance, DB_opening_status, DB_opening_currency, DB_opening_entry_date,
    DB_closing_balance, DB_closing_status, DB_closing_currency, DB_closing_entry_date,
    )
from banking.declarations import (
    CODE_0030, CODE_3010, CODE_3040, CODE_3955, CREDIT,
    DIALOG_ID_UNASSIGNED,
    ERROR, EURO,
    Informations, INFORMATION, IDENTIFIER,
    PERCENT,
    MESSAGE_TEXT,
    KEY_IDENTIFIER_DELIMITER, KEY_SYSTEM_ID,
    KEY_BPD, KEY_UPD, KEY_BANK_NAME, KEY_STORAGE_PERIOD, KEY_TWOSTEP, KEY_ACCOUNTS, KEY_SUPPORTED_CAMT_MESSAGE,
    KEY_MIN_PIN_LENGTH, KEY_MAX_PIN_LENGTH, KEY_MAX_TAN_LENGTH,
    KEY_VERSION_TRANSACTION, KEY_VERSION_TRANSACTION_ALLOWED,
    KEY_SEPA_FORMATS, KEY_TAN_REQUIRED,
    KEY_ACC_IBAN, KEY_ACC_ACCOUNT_NUMBER, KEY_ACC_ALLOWED_TRANSACTIONS,
    KEY_ACC_BANK_CODE, KEY_ACC_CURRENCY, KEY_ACC_CUSTOMER_ID, KEY_ACC_OWNER_NAME,
    KEY_ACC_PRODUCT_NAME, KEY_ACC_SUBACCOUNT_NUMBER, KEY_ACC_TYPE,
    PNS,
    WARNING,
    # form declaratives
    WM_DELETE_WINDOW, DEBIT)
from banking.fints_extension import HIKAZS6, HIKAZS7,  HIWPDS5, HIWPDS6
from banking.messagebox import (MessageBoxTermination, MessageBoxInfo, MessageBoxAsk)
from banking.forms import PrintMessageCode, InputPIN
from banking.message import Messages
from banking.utils import (
    Amount, application_store,
    bankdata_informations_append,
    check_main_thread,
    dict_get_nested_value, dec2, dec6,
    create_iban,
    date_yymmdd,
    exception_error,
    )


re_identification = re.compile(r'^:35B:ISIN\s(.*)\|(.*)\|(.*)$')
re_marketprice = re.compile(
    r'^:90B::MRKT\/\/ACTU\/([A-Z]{3})(\d*),{1}(\d*)$')
re_marketprice01 = re.compile(r'^:90A::MRKT\/\/PRCT\/(\d*),{1}(\d*)$')
re_pricedate01 = re.compile(r'^:98A::PRIC\/\/(\d{8})')
re_pricedate02 = re.compile(r'^:98C::PRIC\/\/(\d{8})')
re_pricedate03 = re.compile(r'^:98A::STAT\/\/(\d{8})')
re_pricedate04 = re.compile(r'^:98C::STAT\/\/(\d{8})')
re_exchange_rate = re.compile(
    r'^:92B::EXCH\/\/([A-Z]{3})\/([A-Z]{3})\/(\d*),{1}(\d*)$')
re_pieces = re.compile(r'^:93B::AGGR\/\/UNIT\/(\d*),(\d*)$')
re_pieces01 = re.compile(r'^:93B::AGGR\/\/FAMT\/(\d*),(\d*)$')
re_total_amount = re.compile(r'^:19A::HOLD\/\/([A-Z]{3})(\d*),{1}(\d*)$')
re_acquisitionprice = re.compile(
    r'^:70E::HOLD\/\/\d*[A-Z]{3}\|2(\d*?),{1}(\d*?)\+([A-Z]{3})$')
re_total_amountportfolio = re.compile(
    r'^:19A::HOLP\/\/([A-Z]{3})(\d*),{1}(\d*)$')
logger = logging.getLogger(__name__)
log_target = logger.info



class Dialogs(object):
    """
    Dialogues: Customer - Bank
    """
    bpd_updated = False
    upd_updated = False

    def __init__(self):

        self.mariadb = MariaDB()
        self.messages = Messages()
        result = application_store.get([DB_logging, DB_show_messages])
        if result:
            self._show_message = result[DB_show_messages]
            self._logging = result[DB_logging]
        if not self._show_message:
            self._show_message = ERROR

    def _start_dialog(self, bank):

        if bank.opened_bank_code != bank.bank_code:
            bank.opened_bank_code = None
            bank.dialog_id = DIALOG_ID_UNASSIGNED
            bank.tan_process = 4
            bank.sca = True
            response = None
            while not response:
                bank.message_number = 1
                if bank.bank_code not in PNS.keys():
                    input_pin = InputPIN(
                        bank.bank_code, bank_name=bank.bank_name)
                    if input_pin.button_state == WM_DELETE_WINDOW:
                        return None
                    PNS[bank.bank_code] = input_pin.pin
                response, _ = self._send_msg(
                    bank, self.messages.msg_dialog_init(bank), dialog_init=True)
                if response is not None:
                    self._store_bpd_shelve(bank, response)
                    self._store_upd_shelve(bank, response)
                    for seg in response.find_segments(HIUPD6):
                        if bank.iban == seg.iban and seg.extension:
                            formatted_string = json.dumps(
                                seg.extension, indent=4)
                            MessageBoxInfo(message=MESSAGE_TEXT['HIUPD_EXTENSION'].format(
                                bank.bank_name, bank.account_number, bank.account_product_name, bank.iban, formatted_string),
                                bank=bank, information_storage=Informations.BANKDATA_INFORMATIONS)
                    seg = response.find_segment_first(HNHBK3)
                    if seg:
                        break
                Informations.bankdata_informations = ''
                PNS.pop(bank.bank_code, None)
                response = None
            bank.dialog_id = seg.dialog_id
            seg = response.find_segment_first(HITAN7)
            if not seg:
                seg = response.find_segment_first(HITAN6)
                if not seg:
                    MessageBoxInfo(message=MESSAGE_TEXT['HITAN_MISSED'].format(
                        bank.bank_name, bank.account_number, bank.account_product_name), bank=bank)
            bank.task_reference = seg.task_reference
            response, _ = self._get_tan(bank, response)
            if response:
                bank.opened_bank_code = bank.bank_code
                return response
            else:
                return None  # input of Tan canceled
        else:
            return True  # thread checking

    def _end_dialog(self, bank):

        self._send_msg(bank, self.messages.msg_dialog_end(bank))
        bank.message_number = 1
        bank.opened_bank_code = None

    def _get_tan(self, bank, response):

        hirms_codes = []
        for seg in response.find_segments(HIRMS2):
            for hirms in seg.responses:
                if hirms.code == CODE_0030:
                    bank.tan_process = 2
                    message = self.messages.msg_tan(bank)
                    if message:
                        response, hirms_codes = self._send_msg(bank, message)
                    else:
                        MessageBoxInfo(message=MESSAGE_TEXT['TAN_CANCEL'].format(
                            bank.bank_name, bank.account_number), bank=bank, information=ERROR)
                        return None, []  # input of tan canceled
        return response, hirms_codes

    def _get_segment(self, bank, segment_type):

        for seg in [HIKAZ6, HIKAZ7, HIWPD5, HIWPD6]:
            if (seg.__name__[2:5] == segment_type and
                    seg.__name__[5:6] == str(bank.transaction_versions[segment_type])):
                return seg
        MessageBoxTermination(info=MESSAGE_TEXT['SEGMENT_VERSION'].format(
            'HI', segment_type, bank.transaction_versions[segment_type]), bank=bank)

    def _store_bpd_shelve(self, bank, response):

        seg = response.find_segment_first(HIBPA3)
        if seg is not None:
            # update bpd if version changed
            if Dialogs.bpd_updated:
                return
            elif seg.bpd_version <= 1:  # e.g. Consors; if version number not updated by the bank
                pass            
            elif bank.bpd_version == seg.bpd_version:
                return
            bank.bpd_version = seg.bpd_version
            bank.bank_name = seg.bank_name
            self.mariadb.shelve_put_key(bank.bank_code, [
                (KEY_BPD, bank.bpd_version), (KEY_BANK_NAME, bank.bank_name)])
            Dialogs.bpd_updated =True
        else:
            return
        seg = response.find_segment_first("HICAZS")
        if seg is not None:
            try:
                bank.supported_camt_messages = seg._additional_data[3][3]  # camt_message_name
                self.mariadb.shelve_put_key(
                    bank.bank_code, (KEY_SUPPORTED_CAMT_MESSAGE, bank.supported_camt_messages))
            except KeyError:
                self.mariadb.shelve_put_key(
                    bank.bank_code, (KEY_SUPPORTED_CAMT_MESSAGE, None))
        for hitans in [HITANS7, HITANS6, HITANS5, HITANS4, HITANS3, HITANS2, HITANS1]:
            seg = response.find_segment_first(hitans)
            if seg is not None:
                bank.twostep_parameters = []
                for par in seg.parameter.twostep_parameters:
                    if par.tan_process == '2':
                        bank.twostep_parameters.append(
                            (par.security_function, par.name))
                self.mariadb.shelve_put_key(
                    bank.bank_code, (KEY_TWOSTEP, bank.twostep_parameters))
                break
        transaction_versions_allowed = {}
        transaction_versions_allowed['TAN'] = []

        seg = response.find_segment_first(HITANS7)
        if seg is not None:
            transaction_versions_allowed['TAN'].append(seg.header.version)
        seg = response.find_segment_first(HITANS6)
        if seg is not None:
            transaction_versions_allowed['TAN'].append(seg.header.version)

        transaction_versions_allowed['KAZ'] = []
        seg = response.find_segment_first(HIKAZS7)
        if seg is not None:
            transaction_versions_allowed['KAZ'].append(seg.header.version)
        seg = response.find_segment_first(HIKAZS6)
        if seg is not None:
            transaction_versions_allowed['KAZ'].append(seg.header.version)

        transaction_versions_allowed['WPD'] = []
        seg = response.find_segment_first(HIWPDS6)
        if seg is not None:
            transaction_versions_allowed['WPD'].append(seg.header.version)
        seg = response.find_segment_first(HIWPDS5)
        if seg is not None:
            transaction_versions_allowed['WPD'].append(seg.header.version)

        self.mariadb.shelve_put_key(bank.bank_code, (KEY_VERSION_TRANSACTION_ALLOWED,
                                                     transaction_versions_allowed))
        if self.mariadb.shelve_get_key(bank.bank_code, KEY_VERSION_TRANSACTION):
            bank.transaction_versions = self.mariadb.shelve_get_key(
                bank.bank_code, KEY_VERSION_TRANSACTION)
        else:
            # use highest version
            bank.transaction_versions = {}
            bank.transaction_versions['TAN'] = 7
            seg = response.find_segment_first(HITANS7)
            if seg is None:
                seg = response.find_segment_first(HITANS6)
            if seg is not None:
                bank.transaction_versions['TAN'] = seg.header.version
            bank.transaction_versions['KAZ'] = 7
            seg = response.find_segment_first(HIKAZS7)
            if seg is None:
                seg = response.find_segment_first(HIKAZS6)
            if seg is not None:
                bank.transaction_versions['KAZ'] = seg.header.version
            bank.transaction_versions['WPD'] = 6
            seg = response.find_segment_first(HIWPDS6)
            if seg is None:
                seg = response.find_segment_first(HITANS5)
            if seg is not None:
                bank.transaction_versions['WPD'] = seg.header.version
            self.mariadb.shelve_put_key(
                bank.bank_code, (KEY_VERSION_TRANSACTION, bank.transaction_versions))
        seg = response.find_segment_first(HISPAS1)
        bank.sepa_formats = []
        if seg is not None:
            bank.sepa_formats = seg.parameter.supported_sepa_formats
        self.mariadb.shelve_put_key(
            bank.bank_code, (KEY_SEPA_FORMATS, bank.sepa_formats))
        seg = response.find_segment_first(HIPINS1)
        if seg is not None:
            tans_required = []
            for item in seg.parameter.transaction_tans_required:
                tans_required.append((item.transaction, item.tan_required))
            self.mariadb.shelve_put_key(bank.bank_code, [(KEY_MIN_PIN_LENGTH, seg.parameter.min_pin_length),
                                                         (KEY_MAX_PIN_LENGTH,
                                                          seg.parameter.max_pin_length),
                                                         (KEY_MAX_TAN_LENGTH,
                                                          seg.parameter.max_tan_length),
                                                         (KEY_TAN_REQUIRED, tans_required)])
        else:
            MessageBoxInfo(message=MESSAGE_TEXT['HIPINS1'], bank=bank)
            self.mariadb.shelve_put_key(bank.bank_code, [(KEY_MIN_PIN_LENGTH, 3),
                                                         (KEY_MAX_PIN_LENGTH, 20),
                                                         (KEY_MAX_TAN_LENGTH, 10)])
        seg = response.find_segment_first(HIKAZS7)
        if seg is not None:
            bank.storage_period = seg.parameter.storage_period
        else:
            seg = response.find_segment_first(HIKAZS6)
            if seg is not None:
                bank.storage_period = seg.parameter.storage_period
            else:
                bank.storage_period = 90
        self.mariadb.shelve_put_key(
            bank.bank_code, (KEY_STORAGE_PERIOD, bank.storage_period))
        MessageBoxInfo(message=MESSAGE_TEXT["FINTS_UPDATE_BPD_VERSION"].format(
            bank.bank_name, bank.bpd_version), bank=bank, information=INFORMATION)
        

    def _store_sync_shelve(self, bank, response):

        seg = response.find_segment_first(HNHBK3)
        if seg is not None:
            bank.dialog_id = seg.dialog_id
        else:
            MessageBoxTermination(info=MESSAGE_TEXT['HNHBK3'], bank=bank)
        seg = response.find_segment_first(HISYN4)
        if seg is not None:
            bank.system_id = seg.system_id
            bank.security_identifier = seg.system_id
            self.mariadb.shelve_put_key(
                bank.bank_code, (KEY_SYSTEM_ID, seg.system_id))
        else:
            MessageBoxTermination(info=MESSAGE_TEXT['HISYN4'], bank=bank)
        seg = response.find_segment_first(HISPAS1)
        if seg is not None:
            bank.sepa_formats = seg.parameter.supported_sepa_formats
            self.mariadb.shelve_put_key(
                bank.bank_code, (KEY_SEPA_FORMATS, bank.sepa_formats))
        self._store_upd_shelve(bank, response)
        print("")

    def _store_upd_shelve(self, bank, response):

        seg = response.find_segment_first(HIUPA4)
        if seg is not None:
            # update upd if version changed
            if Dialogs.upd_updated:
                return            
            if seg.upd_version <= 1: # e.g. Consors; if version number not updated by the bank
                pass
            elif bank.upd_version == seg.upd_version:
                return            
            bank.upd_version = seg.upd_version
            self.mariadb.shelve_put_key(
                bank.bank_code, (KEY_UPD, bank.upd_version))
            Dialogs.upd_updated =True
        else:
            return
        seg = response.find_segment_first(HIUPD6)
        if seg is not None:
            bank.accounts = []
            for upd in response.find_segments(HIUPD6):
                if upd.account_information.account_number:
                    acc = {}
                    if upd.iban:
                        acc[KEY_ACC_IBAN] = upd.iban
                    else:
                        acc[KEY_ACC_IBAN] = create_iban(
                            bank_code=upd.account_information.bank_identifier.bank_code,
                            account_number=upd.account_information.account_number)
                    acc[KEY_ACC_ACCOUNT_NUMBER] = upd.account_information.account_number
                    acc[KEY_ACC_SUBACCOUNT_NUMBER] = upd.account_information.subaccount_number
                    acc[KEY_ACC_BANK_CODE] = upd.account_information.bank_identifier.bank_code
                    acc[KEY_ACC_CUSTOMER_ID] = upd.customer_id
                    acc[KEY_ACC_TYPE] = upd.account_type
                    acc[KEY_ACC_CURRENCY] = upd.account_currency
                    if upd.name_account_owner_1:
                        acc[KEY_ACC_OWNER_NAME] = upd.name_account_owner_1
                    if upd.name_account_owner_2:
                        acc[KEY_ACC_OWNER_NAME] = (acc[KEY_ACC_OWNER_NAME]
                                                   + upd.name_account_owner_2)
                    acc[KEY_ACC_PRODUCT_NAME] = upd.account_product_name
                    acc[KEY_ACC_ALLOWED_TRANSACTIONS] = []
                    for allowed_transaction in upd.allowed_transactions:
                        if allowed_transaction.transaction is not None:
                            acc[KEY_ACC_ALLOWED_TRANSACTIONS].append(
                                allowed_transaction.transaction)
                    bank.accounts.append(acc)
            self.mariadb.shelve_put_key(
                bank.bank_code, (KEY_ACCOUNTS, bank.accounts))
        MessageBoxInfo(message=MESSAGE_TEXT["FINTS_UPDATE_UPD_VERSION"].format(
            bank.bank_name, bank.upd_version), bank=bank, information=INFORMATION)            

    def _receive_msg(self, bank, response, hirms_codes):

        if CODE_0030 in hirms_codes:
            seg = response.find_segment_first(HITAN7)
            if not seg:
                seg = response.find_segment_first(HITAN6)
                if not seg:
                    MessageBoxInfo(message=MESSAGE_TEXT[CODE_0030].format(
                        bank.bank_name, bank.account_number, bank.account_product_name), bank=bank, information=WARNING)
                    return [], hirms_codes
            if check_main_thread():
                bank.task_reference = seg.task_reference
                bank.challenge_hhduc = seg.challenge_hhduc  # e.g. Consors: QR_Code contains TAN
                response, hirms_codes = self._get_tan(bank, response)
            else:
                MessageBoxInfo(message=MESSAGE_TEXT[CODE_0030].format(
                    bank.bank_name, bank.account_number, bank.account_product_name), bank=bank, information=WARNING)
        return response, hirms_codes

    def _decoupled_process(self, bank, response, hirms_codes):

        if CODE_0030 in hirms_codes and bank.bank_code == '76030080':  # Consors  Show QR_Code
            # store QR_code with tan in bank
            bank.challenge_hhduc = None
            bank.challenge = ''
            for seg in response.find_segments(HITAN6):
                bank.challenge_hhduc = seg.challenge_hhduc
                bank.challenge = seg.challenge
                break
        if CODE_3955 in hirms_codes:
            # Security clearance is provided via another channel
            for seg in response.find_segments(HITAN7):
                bank.task_reference = seg.task_reference
                message_box_ask = MessageBoxAsk(message=MESSAGE_TEXT['HITAN'].format(seg.challenge))
                if message_box_ask.result:
                    bank.tan_process = 'S'
                    return True
        return False

    def _send_msg(self, bank, message, dialog_init=False):

        def fints_code(bank, segment):

            codes = []
            error = False
            for response in segment.responses:
                codes.append(response.code)
                message = ' ' .join(['Code', str(response.code), str(response.text)])
                if response.code == '3076':      # SCA not required
                    bank.sca = False
                if response.code[0] in ['0', '1']:
                    if self._show_message == INFORMATION:
                        bankdata_informations_append(INFORMATION, message)
                elif response.code[0] == '3':
                    if response.code == '3010':    # no entries found
                        MessageBoxInfo(message=MESSAGE_TEXT['NO_TURNOVER'].format(
                            bank.bank_name, bank.account_number, bank.account_product_name), bank=bank)
                    if self._show_message in [INFORMATION, WARNING]:
                        bankdata_informations_append(WARNING, message)
                        bank.warning_message = True
                else:
                    error = True
                    bankdata_informations_append(WARNING, message)
                    if response.reference_element:
                        bankdata_informations_append(WARNING, ' ' .join(
                            ['- Bezugssegment', str(response.reference_element)]))
                    if response.parameters:
                        bankdata_informations_append(ERROR, ' ' .join(
                            ['- Parameters', str(response.parameters)]))
            return error, codes
        if self._logging:
            log_out = io.StringIO()
            with Password.protect():
                message.print_nested(stream=log_out, prefix="\t")
                logger.debug(('Sending ' + 30 * '>' + '\n{}\n' + 40 * '>' + '\n').format
                             (log_out.getvalue()))
                log_out.truncate(0)
        r = requests.post(bank.server,
                          headers={b'Content-Type': 'text/plain;charset=UTF-8'},
                          data=base64.b64encode(message.render_bytes()))
        if r.status_code < 200 or r.status_code > 299:
            MessageBoxTermination(
                info=MESSAGE_TEXT['SEND_ERROR'].format(r.status_code), bank=bank)
        try:
            response = FinTSInstituteMessage(
                segments=base64.b64decode(r.content.decode('latin1')))
        except Exception:
            exception_error(
                message=MESSAGE_TEXT['RESPONSE'])
            PrintMessageCode(text=Informations.bankdata_informations)
            if dialog_init:
                return None,  []
            else:
                MessageBoxTermination(bank=bank)
        bank.response = response
        if self._logging:
            with Password.protect():
                response.print_nested(stream=log_out, prefix="\t")
                logger.debug(('Received ' + 30 * '>' + '\n{}\n' + 40 * '>' + '\n').format
                             (log_out.getvalue()))
        # bank feedback message
        seg = response.find_segment_first(HIRMG2)
        hirmg_error, fints_codes = fints_code(bank, seg)
        hirms_error = None
        for seg in response.find_segments(HIRMS2):
            hirms_error, hirms_codes = fints_code(bank, seg)
            fints_codes = fints_codes + hirms_codes
        if hirmg_error or hirms_error:
            PrintMessageCode(text=Informations.bankdata_informations)
            if dialog_init:
                return None,  fints_codes
            else:
                MessageBoxTermination(bank=bank)
        return response, fints_codes

    def _mt535_listdict(self, data):
        """
        documentation:
         https://www.hbci-zka.de/dokumente/spezifikation_deutsch/fintsv3/FinTS_3.0_Messages_Finanzdatenformate_2010-08-06_final_version.pdf
        (For more Information Chapter  B.4 page 150)

        Modified Coding copied from
            Pure-python FinTS (formerly known as HBCI) implementation https://pypi.python.org/pypi/fints
        """
        def collapse_multilines(lines):

            clauses = []
            prevline = ""
            for line in lines:
                if line.startswith(":"):
                    if prevline != "":
                        clauses.append(prevline)
                    prevline = line
                elif line.startswith("-"):
                    # last line
                    clauses.append(prevline)
                    clauses.append(line)
                else:
                    prevline += "|{}".format(line)
            return clauses

        def grab_financial_instrument_segments(clauses):
            retval = []
            stack = []
            within_financial_instrument = False
            for clause in clauses:
                if clause.startswith(":16R:FIN"):
                    # start of financial instrument
                    within_financial_instrument = True
                elif clause.startswith(":16S:FIN"):
                    # end of financial instrument - move stack over to
                    # return value
                    retval.append(stack)
                    stack = []
                    within_financial_instrument = False
                else:
                    if within_financial_instrument:
                        stack.append(clause)
            return retval

        mt535_lines = str.splitlines(data)
        # The first line is empty.
        del mt535_lines[0]
        # First: Collapse multiline clauses into one clause
        clauses = collapse_multilines(mt535_lines)
        # Check price_date header information
        for clause in clauses:
            m = re_pricedate04.match(clause)
            if m:
                _price_date = m.group(1)
            m = re_pricedate03.match(clause)
            if m:
                _price_date = m.group(1)
            m = re_total_amountportfolio.match(clause)
            if m:
                _total_amount_portfolio = dec2.convert(
                    float(m.group(2) + '.' + m.group(3)))
        # Second: Scan sequence of clauses for financial instrument
        finsegs = grab_financial_instrument_segments(clauses)
        # Third: Extract financial instrument data
        mt535 = []
        for idx, finseg in enumerate(finsegs):
            mt535.append({})
            mt535[idx]['price_date'] = _price_date
            for clause in finseg:
                # identification of instrument
                # e.g. ':35B:ISIN LU0635178014|/DE/ETF127|COMS.-MSCI
                # EM.M.T.U.ETF I'
                m = re_identification.match(clause)
                if m:
                    mt535[idx]['isin_code'] = m.group(1)
                    mt535[idx]['name'] = m.group(3)
                # current market price
                # e.g. ':90B::MRKT//ACTU/EUR38,82'
                m = re_marketprice.match(clause)
                if m:
                    mt535[idx]['price_currency'] = m.group(1)
                    mt535[idx]['market_price'] = dec6.convert(
                        float(m.group(2) + '.' + m.group(3)))
                else:
                    m = re_marketprice01.match(clause)
                    if m:
                        mt535[idx]['price_currency'] = PERCENT
                        mt535[idx]['market_price'] = dec6.convert(
                            float(m.group(1) + '.' + m.group(2)))
                # date of market price
                # e.g. ':98A::PRIC//20170428'
                m = re_pricedate02.match(clause)
                if m:
                    mt535[idx]['price_date'] = m.group(1)
                elif not m:
                    m = re_pricedate01.match(clause)
                    if m:
                        mt535[idx]['price_date'] = m.group(1)
                # number of pieces
                # e.g. ':93B::AGGR//UNIT/16,8211'
                m = re_pieces.match(clause)
                if m:
                    mt535[idx]['pieces'] = dec2.convert(
                        float(m.group(1) + '.' + m.group(2)))
                else:
                    m = re_pieces01.match(clause)
                    if m:
                        mt535[idx]['pieces'] = dec2.convert(
                            float(m.group(1) + '.' + m.group(2)))
                # total value of holding
                # e.g. ':19A::HOLD//EUR970,17'
                m = re_total_amount.match(clause)
                if m:
                    mt535[idx]['amount_currency'] = m.group(1)
                    mt535[idx]['total_amount'] = dec2.convert(
                        float(m.group(2) + '.' + m.group(3)))
                # Acquisition price
                # e.g ':70E::HOLD//1STK23,968293+EUR'
                m = re_acquisitionprice.match(clause)
                if m:
                    mt535[idx]['acquisition_price'] = dec6.convert(
                        float(m.group(1) + '.' + m.group(2)))
                # Exchange_rate
                # e.g ':92B::EXCH//EUR/TRY/6,3926'
                m = re_exchange_rate.match(clause)
                if m:
                    mt535[idx]['exchange_currency_1'] = m.group(1)
                    mt535[idx]['exchange_currency_2'] = m.group(2)
                    mt535[idx]['exchange_rate'] = float(
                        m.group(3) + '.' + m.group(4))
                    if mt535[idx]['exchange_rate'] != 0:
                        if mt535[idx]['exchange_currency_2'] == mt535[idx]['amount_currency']:
                            mt535[idx]['amount_currency'] = mt535[idx]['exchange_currency_1']
                            mt535[idx]['total_amount'] = dec2.divide(
                                mt535[idx]['total_amount'], mt535[idx]['exchange_rate'])
                        if mt535[idx]['exchange_currency_2'] == mt535[idx]['price_currency']:
                            mt535[idx]['price_currency'] = mt535[idx]['exchange_currency_1']
                            mt535[idx]['market_price'] = dec6.divide(
                                mt535[idx]['market_price'], mt535[idx]['exchange_rate'])
            mt535[idx]['total_amount_portfolio'] = _total_amount_portfolio
        return mt535

    def _mt940_listdict(self, data, bank_code):
        """
        documentation:
        https://www.hbci-zka.de/dokumente/spezifikation_deutsch/fintsv3/FinTS_3.0_Messages_Finanzdatenformate_2010-08-06_final_version.pdf
        (For more Information Chapter  B.8 page 174)
        """

        transactions = Transactions()
        mt940 = []
        identifier_delimiter = self.mariadb.shelve_get_key(
            bank_code, KEY_IDENTIFIER_DELIMITER)
        # bank: CONSORS
        # transactions.parse returns duplicate customer_reference value separated
        # by <LF>
        keys_not_used = []
        mt940_statements = transactions.parse(data)

        for mt940_statement in mt940_statements:
            for key_ in mt940_statement.data.keys():
                if key_ not in TABLE_FIELDS[STATEMENT] or mt940_statement.data[key_] is None:
                    keys_not_used.append(key_)
                else:
                    value = mt940_statement.data[key_]
                    if value is not None and isinstance(value, str):
                        mt940_statement.data[key_] = value.replace('\n', ' ')
                    if isinstance(value, date):
                        mt940_statement.data[key_] = str(value)
            for key_ in keys_not_used:
                del mt940_statement.data[key_]
            keys_not_used = []
            mt940.append(mt940_statement.data)
        idx_mt940 = 0
        clauses = data.splitlines()
        tags = Transactions.defaultTags().copy()
        for clause in clauses:
            m = tags['60F'].re.match(clause[5:])  # opening balance data
            if clause[0:5] == ':60F:' and m:
                _opening_status = m.group('status')
                _entry_date = date_yymmdd.convert(
                    m.group('year') + m.group('month') + m.group('day'))
                _opening_entry_date = _entry_date
                _opening_currency = m.group('currency')
                _opening_balance = dec2.convert(abs(Amount(m.group('amount'),
                                                           m.group('status')).amount))
                _closing_status = m.group('status')
                _closing_entry_date = _entry_date
                _closing_currency = m.group('currency')
                _closing_balance = dec2.convert(abs(Amount(m.group('amount'),
                                                           m.group('status')).amount))
            m = tags['60M'].re.match(clause[5:])  # opening balance data
            if clause[0:5] == ':60M:' and m:
                _opening_status = m.group('status')
                _entry_date = date_yymmdd.convert(
                    m.group('year') + m.group('month') + m.group('day'))
                _opening_entry_date = _entry_date
                _opening_currency = m.group('currency')
                _opening_balance = dec2.convert(abs(Amount(m.group('amount'),
                                                           m.group('status')).amount))
                _closing_status = m.group('status')
                _closing_entry_date = _entry_date
                _closing_currency = m.group('currency')
                _closing_balance = dec2.convert(abs(Amount(m.group('amount'),
                                                           m.group('status')).amount))
            m = tags[61].re.match(clause[4:])  # transaction data
            if clause[0:4] == ':61:' and m:
                _amount = dec2.convert(abs(Amount(m.group('amount'),
                                                  m.group('status')).amount))
                _status = m.group('status')
                try:
                    _entry_date = date_yymmdd.convert(m.group('entry_date'))
                except IndexError:
                    pass
                mt940[idx_mt940]['entry_date'] = _entry_date
                mt940[idx_mt940]['amount'] = _amount
                mt940[idx_mt940]['currency'] = _opening_currency
                mt940[idx_mt940].update({'opening_status': _opening_status})
                mt940[idx_mt940].update(
                    {'opening_entry_date': _opening_entry_date})
                mt940[idx_mt940].update(
                    {'opening_currency': _opening_currency})
                mt940[idx_mt940].update({'opening_balance': _opening_balance})
                x = _opening_balance
                if _opening_status == 'D':
                    x = -x
                y = _amount
                if _status == 'D':
                    y = -y
                _closing_balance = dec2.add(x, y)
                _closing_status = 'C' if (_closing_balance > 0) else 'D'
                mt940[idx_mt940].update({'closing_status': _closing_status})
                mt940[idx_mt940].update(
                    {'closing_entry_date': _closing_entry_date})
                mt940[idx_mt940].update(
                    {'closing_currency': _closing_currency})
                mt940[idx_mt940].update(
                    {'closing_balance': abs(_closing_balance)})
                _opening_balance = abs(_closing_balance)
                _opening_status = _closing_status
                mt940[idx_mt940] = self._create_identifiers(
                    mt940[idx_mt940], identifier_delimiter)
                idx_mt940 += 1
        return mt940

    def _create_identifiers(self, mt940, identifier_delimiter):

        if 'purpose' in mt940:
            identifiers = []
            if isinstance(mt940['purpose'], list):
                mt940['purpose'] = " ".join(mt940['purpose'])
            purpose = mt940['purpose'].replace(' ', '')
            # select existing SEPA indentifiers in purpose
            for identifier in IDENTIFIER.keys():
                identifier = identifier + identifier_delimiter
                m = re.compile(identifier).search(purpose)
                if m is not None:
                    identifiers.append((m.group(), m.start(), m.end()))
            identifiers = sorted(identifiers, key=itemgetter(1))
            purpose_all = purpose
            # insert sepa items in mt940
            for idx, identifier in enumerate(identifiers):
                name, _, end = identifier
                name = name[:-1]
                try:
                    _, next_start, _ = identifiers[idx + 1]
                    value = purpose_all[end:next_start]
                except IndexError:
                    value = purpose_all[end:]
                if len(value) > 65:
                    value = value[0:65]
                mt940.update({IDENTIFIER[name]: value})
            # mt940: save purpose content cleaned of sepa items in purpose_wo_identifier
            if 'purpose_wo_identifier' not in mt940:
                if identifiers:
                    start_sepa_identifiers = identifiers[0][2] + 1
                    mt940['purpose_wo_identifier'] = mt940['purpose'][:start_sepa_identifiers]
                else:
                    mt940['purpose_wo_identifier'] = mt940['purpose']

        return mt940

    def _parse_camt052(self, xml_string, bank):
        """
        Document:
            www.ebics.de > Datenformate > Gueltige version
            Die Deutsche Kreditwirtschaft
            Version 3.9 vom 12.03.2025 (Final Version)
            DFÜ – Abkommen
            Anlage 3: Spezifikation der Datenformate
            7.2 Bank to Customer Account Report (camt.052)
        """
        def ensure_list(x: Union[None, list, dict]) -> List:
            if x is None:
                return []
            if isinstance(x, list):
                return x
            return [x]

        def convert_amount(amount, status):
            if isinstance(amount, Decimal):
                amount = amount if status == CREDIT else -amount
            else:
                amount = dec2.convert(amount)
                amount = amount if status == CREDIT else -amount
            return amount

        def normalize_amount(a: Any):
            # a can be dict like {"#text":"123.45", "@Ccy":"EUR"}
            if isinstance(a, dict):
                # xmltodict typically gives text under None or '#text' or directly string
                if "#text" in a:
                    amount = dec2.convert(a["#text"])
                    if "@Ccy" in a:
                        currency = a["@Ccy"]
                    return amount, currency
            return None, EURO

        identifier_delimiter = self.mariadb.shelve_get_key(bank.bank_code, KEY_IDENTIFIER_DELIMITER)
        doc = xmltodict.parse(xml_string)
        doc = doc.get("Document", {})
        root = doc.get("BkToCstmrAcctRpt", {})
        rpt = root.get("Rpt", {})
        # Get opening balance
        opening_balance = None
        closing_balance = None
        rpt_bal = rpt.get("Bal", [])
        for bal in ensure_list(rpt_bal):
            # bal could be dict with keys Tp->{Cd}, Amt, CdtDbtInd, Dt or Bal.Dt
            tp = bal.get("Tp", {})
            cd = None
            # cd might be under Tp.Cd or Tp.Cd.CdOrPrtry
            if isinstance(tp, dict):
                cd = tp.get("Cd") or tp.get("CdOrPrtry", None)
                # sometimes nested: Tp.Cd.Prtry...
                if isinstance(cd, dict):
                    # try nested representation
                    cd = cd.get("#text") or cd.get("Cd")
            if cd and cd == "OPBD":
                opening_balance, opening_currency = normalize_amount(bal.get("Amt"))
                if opening_balance:
                    cdt_db = bal.get("CdtDbtInd")
                    if cdt_db == "DBIT":
                        opening_status = DEBIT
                    else:
                        opening_status = CREDIT
                    opening_balance = convert_amount(opening_balance, opening_status)
                    # date can be in bal.Dt or bal.Dt.Dt or in SubTp? prefer Dt.Dt
                    dt = None
                    dt_node = bal.get("Dt") or bal.get("DtTm")
                    if isinstance(dt_node, dict):
                        dt = dt_node.get("Dt") or dt_node.get("#text")
                    else:
                        dt = dt_node
                    opening_date = dt
            if cd and cd == "CLBD":
                closing_balance, _ = normalize_amount(bal.get("Amt"))
                if closing_balance:
                    cdt_db = bal.get("CdtDbtInd")
                    if cdt_db == "DBIT":
                        closing_status = DEBIT
                    else:
                        closing_status = CREDIT
                    closing_balance = convert_amount(closing_balance, closing_status)
        # Get statements
        entries_out = []
        entry_obj = {}        
        ntry = rpt.get("Ntry")
        for entry in ensure_list(ntry):
            if opening_balance:
                entry_obj = {
                    DB_opening_balance: abs(opening_balance),
                    DB_opening_status: opening_status,
                    DB_opening_currency: opening_currency,
                    DB_opening_entry_date: opening_date,
                    }
            entry_obj[DB_amount], entry_obj[DB_currency] = normalize_amount(entry.get("Amt"))
            entry_obj[DB_status] = DEBIT if entry.get("CdtDbtInd") == "DBIT" else CREDIT
            entry_obj[DB_entry_date] = (entry.get("BookgDt") or {}).get("Dt") if isinstance(entry.get("BookgDt"), dict) else entry.get("BookgDt")
            entry_obj[DB_date] = (entry.get("ValDt") or {}).get("Dt") if isinstance(entry.get("ValDt"), dict) else entry.get("ValDt")
            entry_obj[DB_posting_text] = entry.get("AddtlNtryInf")
            # "EntryReference": entry.get("NtryRef"),
            entry_obj[DB_bank_reference] = entry.get("AcctSvcrRef")
            if opening_balance:
                opening_balance = dec2.add(
                    convert_amount(entry_obj[DB_opening_balance], entry_obj[DB_opening_status]),
                    convert_amount(entry_obj[DB_amount], entry_obj[DB_status])
                    )
                opening_status = CREDIT if (opening_balance > 0) else DEBIT
                opening_date = entry_obj[DB_entry_date]
                entry_obj[DB_closing_balance] = abs(opening_balance)
                entry_obj[DB_closing_status] = opening_status
                entry_obj[DB_closing_entry_date] = opening_date
                entry_obj[DB_closing_currency] = opening_currency
            """
             Bank Transaction Code mapping (BkTxCd)
            7.1.8.5.2
            Belegung von <Prtry>
            Bei Nutzung der Elementgruppe <Prtry> ist unter <Cd> folgender zusammengesetzter Code,
            bestehend aus folgenden Teilen, die zusammen als String, verbunden mit jeweils “+”
            eingestellt werden, spezifiziert:
                    1. Vierstelliger SWIFT-Transaction-Code
                    2. Geschäftsvorfallcode (GVC)
                    3. Optional: Primanota-Nr. (maximal 10-stellig)
                    4. Textschlüsselergänzung, falls darstellbar
            Beispiel:
            <Cd>NTRF+116+9002/405</Cd>
            """
            bk = entry.get("BkTxCd")
            if isinstance(bk, dict):
                # Proprietary Bank TransactionCodeStructure1
                prtry = bk.get("Prtry", {})
                if isinstance(prtry, dict):
                    _prtry = prtry.get("Cd", None)
                    if _prtry:
                        _prtry = _prtry.split("+")
                        entry_obj[DB_id] = _prtry[0]
                        entry_obj[DB_transaction_code] = _prtry[1]
                        entry_obj[DB_prima_nota] = _prtry[2]

            # Entry details: one or many TxDtls under NtryDtls.TxDtls
            ntrydtls = entry.get("NtryDtls", {})
            txdtls = ntrydtls.get("TxDtls") or ntrydtls.get("TxDtls")
            for tx in ensure_list(txdtls):
                # "TransactionId": (tx.get("Refs") or {}).get("TxId"),
                entry_obj[DB_remittance_information] = (tx.get("Refs") or {}).get("InstrId")
                entry_obj[DB_end_to_end_reference] = (tx.get("Refs") or {}).get("EndToEndId")
                # "ClearingSystemRef": (tx.get("Refs") or {}).get("ClrSysRef"),
                entry_obj[DB_mandate_id] = (tx.get("DrctDbtTx", {}).get("MndtRltdInf") or {}).get("MndtId")
                # "CreditorSchemeId": (tx.get("DrctDbtTx", {}).get("MndtRltdInf") or {}).get("CdtrSchmeId", {}),
                entry_obj[DB_purpose_code] = (tx.get("Purp") or {}).get("Cd")
                # "AdditionalTransactionInfo": tx.get("AddtlTxInf"),
                # "ChargeAmount": self._normalize_amount(tx.get("ChrgsInf")),
                # Remittance info
                rmt = tx.get("RmtInf")
                if rmt:
                    entry_obj[DB_purpose] = rmt.get("Ustrd", {})
                # Parties & Accounts (RltdAgts, RltdPties commonly used)
                rltd = tx.get("RltdAgts") or {}
                # Debtor Agent BICs
                dbtragt = rltd.get("DbtrAgt") or {}
                if isinstance(dbtragt, dict):
                    entry_obj[DB_applicant_bic] = dict_get_nested_value(dbtragt, ["FinInstnId", "BICFI"])
                rltd = tx.get("RltdPties") or {}
                if entry_obj[DB_status] == CREDIT:
                    # Debtor
                    dbtr = rltd.get("Dbtr")
                    if dbtr:
                        entry_obj[DB_applicant_name] = dict_get_nested_value(dbtr, ["Pty", "Nm"])
                    dbtracct = rltd.get("DbtrAcct")
                    if dbtracct:
                        # IBAN under Id.IBAN or Id.Othr.Id
                        iban = dict_get_nested_value(dbtracct, ["Id", "IBAN"])
                        if iban is None:
                            iban = dict_get_nested_value(dbtracct, ["Id", "Othr", "Id"])
                        entry_obj[DB_applicant_iban] = iban
                else:
                    # Creditor
                    cdtr = rltd.get("Cdtr")
                    if cdtr:
                        entry_obj[DB_applicant_name] = dict_get_nested_value(cdtr, ["Pty", "Nm"])
                    cdtract = rltd.get("CdtrAcct")
                    if cdtract:
                        iban = dict_get_nested_value(cdtract, ["Id", "IBAN"])
                        if iban is None:
                            iban = dict_get_nested_value(cdtract, ["Id", "Othr", "Id"])
                        entry_obj[DB_applicant_iban] = iban
                    entry_obj = self._create_identifiers(entry_obj, identifier_delimiter)
                entry_obj[DB_camt] = "052"  # source format camt.052
                entries_out.append(entry_obj)
        if entry_obj and closing_balance:  # entries exist and closing_balance reported by bank
            statements_closing_balance = convert_amount(entry_obj[DB_closing_balance], entry_obj[DB_closing_status])  # calculated closing_balance
            if closing_balance != statements_closing_balance:
                MessageBoxInfo(
                    message=MESSAGE_TEXT['BANK_BALANCE_DIFFERENCE'].format(
                        bank.account_product_name, bank.account_number, closing_balance,
                        entry_obj[DB_closing_balance], statements_closing_balance,
                        str(dec2.subtract(closing_balance, statements_closing_balance))
                        ),
                    bank=bank, information=WARNING
                    )
        return entries_out

    def anonymous(self, bank):
        ' HITANS >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>'
        bank.message_number = 1
        bank.dialog_id = DIALOG_ID_UNASSIGNED
        response, _ = self._send_msg(
            bank, self.messages.msg_dialog_anonymous(bank))
        self._store_bpd_shelve(bank, response)

    def sync(self, bank):
        ' HISYN >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>'
        bank.message_number = 1
        bank.dialog_id = DIALOG_ID_UNASSIGNED
        response, _ = self._send_msg(bank, self.messages.msg_dialog_syn(bank))
        self._store_sync_shelve(bank, response)
        self._end_dialog(bank)

        ' HIUPD 2nd search >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>'
        seg = response.find_segment_first(HIUPD6)
        if not seg:
            response = self._start_dialog(bank)
            if response:
                self._store_upd_shelve(bank, response)
                self._end_dialog(bank)

    def holdings(self, bank):

        holdings = []
        if self._start_dialog(bank):
            bank.tan_process = 4
            response, hirms_codes = self._send_msg(
                bank, self.messages.msg_holdings(bank))
            response, hirms_codes = self._receive_msg(
                bank, response, hirms_codes)
            if not response:
                return holdings
            hiwpd = self._get_segment(bank, 'WPD')
            seg = response.find_segment_first(hiwpd)
            if not seg:
                MessageBoxTermination(
                    info=MESSAGE_TEXT['HIWPD'].format(hiwpd.__name__), bank=bank)
                return holdings  # threading continues
            if type(seg.holdings) is bytes:
                try:
                    holding_str = seg.holdings.decode('utf-8')
                except UnicodeDecodeError:
                    holding_str = seg.holdings.decode('latin1')
            else:
                holding_str = seg.holdings
            if self._logging:
                logger.debug('\n\n>>>>> START MT535 DATA ' + 40 * '>' + '\n')
                log_target(holding_str)
                logger.debug('\n\n>>>>> START MT535 DATA PARSING ' +
                             30 * '>' + '\n')
            self._end_dialog(bank)
            holdings = self._mt535_listdict(holding_str)
        return holdings

    def statements(self, bank):

        statements = []
        if self._start_dialog(bank):
            bank.tan_process = 4
            response, hirms_codes = self._send_msg(
                bank, self.messages.msg_statements(bank))
            if self._decoupled_process(bank, response, hirms_codes):
                response, hirms_codes = self._send_msg(
                    bank, self.messages.msg_tan_decoupled(bank))
            response, hirms_codes = self._receive_msg(
                bank, response, hirms_codes)
            if not response:
                return statements  # no statements found or SCA in threading mode
            if CODE_3010 in hirms_codes:
                return statements
            if CODE_0030 not in hirms_codes:
                if CODE_3040 in hirms_codes:  # further turnovers exist
                    MessageBoxInfo(message=MESSAGE_TEXT[CODE_3040].format(
                        bank.bank_name, bank.account_number, bank.account_product_name),
                        bank=bank, information=WARNING)
                if bank.statement_mt940:
                    hikaz = self._get_segment(bank, 'KAZ')
                    seg = response.find_segment_first(hikaz)
                    if not seg:
                        MessageBoxInfo(message=MESSAGE_TEXT['HIKAZ'].format(
                            'HKKAZ', bank.bank_name, bank.account_number, bank.account_product_name
                            ),
                             bank=bank, information=ERROR
                             )
                        return statements  # threading continues
                    try:
                        statement_booked_str = seg.statement_booked.decode('utf-8')
                    except UnicodeDecodeError:
                        statement_booked_str = seg.statement_booked.decode(
                            'latin1')
                    if self._logging:
                        logger.debug('\n\n>>>>> START MT940 DATA ' +
                                     40 * '>' + '\n')
                        log_target(statement_booked_str)
                        logging.getLogger(__name__).debug(
                            '\n\n>>>>> START MT940 DATA PARSING ' + 30 * '>' + '\n')
                    statements = self._mt940_listdict(
                        statement_booked_str, bank.bank_code)
                elif bank.statement_camt:
                    seg = response.find_segment_first(HICAZ1)
                    if not seg:
                        MessageBoxInfo(
                            message=MESSAGE_TEXT['HIKAZ'].format(
                                'HKCAZ', bank.bank_name, bank.account_number, bank.account_product_name
                                ),
                            bank=bank, information=ERROR
                            )
                        return statements  # threading continues
                    statements = seg.statement_booked.camt_statements._data[0]
                    if self._logging:
                        dom = minidom.parseString(statements)
                        pretty_xml = dom.toprettyxml(indent="  ")
                        logger.debug('\n\n>>>>> START CAMT_052 DATA ' +
                                     40 * '>' + '\n')
                        log_target(pretty_xml)
                        logging.getLogger(__name__).debug(
                            '\n\n>>>>> START CAMT_052 DATA PARSING ' + 30 * '>' + '\n')
                    statements = self._parse_camt052(statements, bank)
            self._end_dialog(bank)
        return statements

    def transfer(self, bank):

        if self._start_dialog(bank):
            bank.tan_process = 4
            response, hirms_codes = self._send_msg(
                bank, self.messages.msg_transfer(bank))
            if self._decoupled_process(bank, response, hirms_codes):
                self._send_msg(bank, self.messages.msg_tan_decoupled(bank))
            else:
                seg = response.find_segment_first(HITAN7)
                if not seg:
                    seg = response.find_segment_first(HITAN6)
                    if not seg:
                        MessageBoxTermination(info=MESSAGE_TEXT['HITAN6'], bank=bank)
                bank.task_reference = seg.task_reference
                self._get_tan(bank, response)
            self._end_dialog(bank)

    def date_transfer(self, bank):

        if self._start_dialog(bank):
            bank.tan_process = 4
            response, hirms_codes = self._send_msg(
                bank, self.messages.msg_date_transfer(bank))
            if self._decoupled_process(bank, response, hirms_codes):
                self._send_msg(bank, self.messages.msg_tan_decoupled(bank))
            else:
                seg = response.find_segment_first(HITAN7)
                if not seg:
                    seg = response.find_segment_first(HITAN6)
                    if not seg:
                        MessageBoxTermination(info=MESSAGE_TEXT['HITAN6'], bank=bank)
                bank.task_reference = seg.task_reference
                self._get_tan(bank, response)
            self._end_dialog(bank)
