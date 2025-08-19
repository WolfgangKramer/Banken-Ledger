"""
Created on 18.11.2019
__updated__ = "2025-05-31"
@author: Wolfgang Kramer
"""

import inspect
import logging

from fints.client import FinTS3Serializer

from banking.mariadb import MariaDB
from banking.declarations import (
    CUSTOMER_ID_ANONYMOUS, KEY_TAN_REQUIRED
)
from banking.declarations_mariadb import DB_logging
from banking.segment import Segments
from banking.utils import application_store


def _serialize(message):

    if application_store.get(DB_logging):
        fints3serializer = FinTS3Serializer()
        byte_message = fints3serializer.serialize_message(message).split(b"'")
        logging.getLogger(__name__).debug('\n\n>>>>> START' + 80 * '>' + '\n')
        logging.getLogger(__name__).debug(inspect.stack()[1])
        for item in byte_message:
            logging.getLogger(__name__).debug(item)


def _get_tan_required(bank, segment_type, mariadb):

    tan_required = True
    transactions_tan_required = mariadb.shelve_get_key(
        bank.bank_code, KEY_TAN_REQUIRED)
    for item in transactions_tan_required:
        transaction, tan_required = item
        if transaction == segment_type:
            break
    return tan_required


class Messages():
    """
    FinTS Message Structures

    Documentation:
    https://www.hbci-zka.de/dokumente/spezifikation_deutsch/fintsv3/FinTS_3.0_Formals_2017-10-06_final_version.pdf
    """

    def __init__(self):

        self.mariadb = MariaDB()
        self.segments = Segments()

    def msg_dialog_init(self, bank):
        """
        (For more Information Chapter  C.3 Page 41)
        """
        message = self.segments.segHNHBK(bank)
        message = self.segments.segHNSHK(bank, message)
        message = self.segments.segHKIND(bank, message)
        message = self.segments.segHKVVB(bank, message)
        message = self.segments.segHKTAN(bank, message)
        message = self.segments.segHNSHA(bank, message)
        message = self.segments.segHNHBS(bank, message)
        _serialize(message)
        return message

    def msg_dialog_anonymous(self, bank):
        """
        (For more Information Chapter  C.5 Page 55)
        """
        message = self.segments.segHNHBK(bank)
        message = self.segments.segHKIND(
            bank, message, user_id=CUSTOMER_ID_ANONYMOUS)
        message = self.segments.segHKVVB(bank, message)
        message = self.segments.segHKTAN(bank, message)
        message = self.segments.segHNHBSnoencrypt(bank, message)
        _serialize(message)
        return message

    def msg_dialog_syn(self, bank):
        """
        (For more Information Chapter  C.8 Page 66)
        """
        message = self.segments.segHNHBK(bank)
        message = self.segments.segHNSHK(bank, message)
        message = self.segments.segHKIND(bank, message)
        message = self.segments.segHKVVB(bank, message)
        message = self.segments.segHKTAN(bank, message)
        message = self.segments.segHKSYN(bank, message)
        message = self.segments.segHNSHA(bank, message)
        message = self.segments.segHNHBS(bank, message)
        _serialize(message)
        return message

    def msg_tan_decoupled(self, bank):
        """
        FinTS Message TAN challenge decoupled
        """
        message = self.segments.segHNHBK(bank)
        message = self.segments.segHNSHK(bank, message)
        message = self.segments.segHKTAN_decoupled(bank, message)
        message = self.segments.segHNSHA_TAN(bank, message)
        if message:
            message = self.segments.segHNHBS(bank, message)
            _serialize(message)
            return message
        return None  # input of tan canceled

    def msg_tan(self, bank):
        """
        FinTS Message TAN challenge
        """
        message = self.segments.segHNHBK(bank)
        message = self.segments.segHNSHK(bank, message)
        message = self.segments.segHKTAN(bank, message)
        message = self.segments.segHNSHA_TAN(bank, message)
        if message:
            message = self.segments.segHNHBS(bank, message)
            _serialize(message)
            return message
        return None  # input of tan canceled

    def msg_statements(self, bank):
        """
        FinTS Message Request of account turnovers
        """
        message = self.segments.segHNHBK(bank)
        message = self.segments.segHNSHK(bank, message)
        message = self.segments.segHKKAZ(bank, message)
        if _get_tan_required(bank, 'HKKAZ', self.mariadb):
            message = self.segments.segHKTAN(
                bank, message, segment_name='HKKAZ')
        message = self.segments.segHNSHA(bank, message)
        message = self.segments.segHNHBS(bank, message)
        _serialize(message)
        return message

    def msg_holdings(self, bank):
        """
        FinTS Message Request of Portfolio
        """
        message = self.segments.segHNHBK(bank)
        message = self.segments.segHNSHK(bank, message)
        message = self.segments.segHKWPD(bank, message)
        if _get_tan_required(bank, 'HKWPD', self.mariadb):
            message = self.segments.segHKTAN(
                bank, message, segment_name='HKWPD')
        message = self.segments.segHNSHA(bank, message)
        message = self.segments.segHNHBS(bank, message)
        _serialize(message)
        return message

    def msg_trading(self, bank):
        """
        FinTS Message Request of movements in portfolio (untested!!)
        """
        message = self.segments.segHNHBK(bank)
        message = self.segments.segHNSHK(bank, message)
        message = self.segments.segHKWDU(bank, message)
        if _get_tan_required(bank, 'HKWDU', self.mariadb):
            message = self.segments.segHKTAN(
                bank, message, segment_name='HKWDU')
        message = self.segments.segHNSHA(bank, message)
        message = self.segments.segHNHBS(bank, message)
        _serialize(message)
        return message

    def msg_transfer(self, bank):
        """
        FinTS Message Execution of a SEPA credit transfer
        """
        message = self.segments.segHNHBK(bank)
        message = self.segments.segHNSHK(bank, message)
        message = self.segments.segHKCCS1(bank, message)
        if _get_tan_required(bank, 'HKCCS', self.mariadb):
            message = self.segments.segHKTAN(
                bank, message, segment_name='HKCCS')
        message = self.segments.segHNSHA(bank, message)
        message = self.segments.segHNHBS(bank, message)
        _serialize(message)
        return message

    def msg_date_transfer(self, bank):
        """
        FinTS Message Execution of a SEPA date credit transfer
        """
        message = self.segments.segHNHBK(bank)
        message = self.segments.segHNSHK(bank, message)
        message = self.segments.segHKCSE1(bank, message)
        if _get_tan_required(bank, 'HKCSE', self.mariadb):
            message = self.segments.segHKTAN(
                bank, message, segment_name='HKCSE')
        message = self.segments.segHNSHA(bank, message)
        message = self.segments.segHNHBS(bank, message)
        _serialize(message)
        return message

    def msg_dialog_end(self, bank):
        """
        (For more Information Chapter  C.4 Page 53)
        """
        message = self.segments.segHNHBK(bank)
        message = self.segments.segHNSHK(bank, message)
        message = self.segments.segHKEND(bank, message)
        message = self.segments.segHNSHA(bank, message)
        message = self.segments.segHNHBS(bank, message)
        _serialize(message)
        return message
