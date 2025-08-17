"""
Created on 11.08.2024
__updated__ = "2025-05-25"
@author: Wolfgang Kramer
"""
from datetime import date, timedelta

from banking.declarations import (
    NOT_ASSIGNED,
    WARNING,
    CREDIT, DEBIT,
)
from banking.declarations import (
    MESSAGE_TEXT, START_DATE_LEDGER
)
from banking.declarations_mariadb import (
    LEDGER, LEDGER_COA, STATEMENT, LEDGER_STATEMENT,

    DB_account,
    DB_amount,
    DB_applicant_iban,
    DB_applicant_name,
    DB_counter,
    DB_credit_account,
    DB_closing_balance,
    DB_closing_status,
    DB_contra_account,
    DB_creditor_id,
    DB_currency,
    DB_date,
    DB_debit_account,
    DB_debitor_id,
    DB_entry_date,
    DB_iban,
    DB_id_no,
    DB_mandate_id,
    DB_name,
    DB_opening_balance,
    DB_opening_status,
    DB_posting_text,
    DB_purpose_wo_identifier,
    DB_status,
)
from banking.messagebox import MessageBoxInfo
from banking.utils import dec2,  date_days


def _recommend_account(mariadb, account, statement_dict, posting_text_dict):
    """
    recommendation contra account, otherwise return 'NA'
    hierarchy of contra_account selection
    """
    # 1. table LEDGER_COA
    ledger_coa = mariadb.select_table(
        LEDGER_COA, [DB_contra_account, DB_iban], result_dict=True, account=account)
    if ledger_coa and ledger_coa[0][DB_contra_account] != NOT_ASSIGNED:
        if ledger_coa[0][DB_contra_account] != account:
            return ledger_coa[0][DB_contra_account]
    # 2. find contra_account used last 370 days, statement fields checked in this order
    check_field_list = [DB_creditor_id, DB_debitor_id, DB_mandate_id,
                        DB_applicant_iban, DB_applicant_name, DB_purpose_wo_identifier]
    period = (statement_dict[DB_entry_date] -
              timedelta(days=370), date_days.subtract(statement_dict[DB_entry_date], 1))
    for field_name in check_field_list:
        if statement_dict[field_name]:
            if field_name == DB_creditor_id:
                account = mariadb.select_sepa_fields_in_statement(
                    statement_dict[DB_iban], period=period, creditor_id=statement_dict[DB_creditor_id])
            elif field_name == DB_debitor_id:
                account = mariadb.select_sepa_fields_in_statement(
                    statement_dict[DB_iban], period=period, debitor_id=statement_dict[DB_debitor_id])
            elif field_name == DB_mandate_id:
                account = mariadb.select_sepa_fields_in_statement(
                    statement_dict[DB_iban], period=period, mandate_id=statement_dict[DB_mandate_id])
            elif field_name == DB_applicant_iban:
                account = mariadb.select_sepa_fields_in_statement(
                    statement_dict[DB_iban], period=period, applicant_iban=statement_dict[DB_applicant_iban])
            elif field_name == DB_applicant_name:
                account = mariadb.select_sepa_fields_in_statement(
                    statement_dict[DB_iban], period=period, applicant_name=statement_dict[DB_applicant_name])
            elif field_name == DB_purpose_wo_identifier:
                account = mariadb.select_sepa_fields_in_statement(
                    statement_dict[DB_iban], period=period, purpose_wo_identifier=statement_dict[DB_purpose_wo_identifier][:20] + '%')
            if account != NOT_ASSIGNED:
                return account
    # 3. dictionary  used posting_text_dict of last 365 days
    if statement_dict[DB_posting_text] in posting_text_dict.keys():
        # contra_account matched posting_text
        if posting_text_dict[statement_dict[DB_posting_text]] != account:
            return posting_text_dict[statement_dict[DB_posting_text]]
    return NOT_ASSIGNED


def transfer_statement_to_ledger(mariadb, bank):
    """
    Upload ledger rows from table statement
    """
    posting_text_credit_dict = mariadb.select_ledger_posting_text_account(
        bank.iban)
    posting_text_debit_dict = mariadb.select_ledger_posting_text_account(
        bank.iban, credit=False)
    ledger_max_entry_date = mariadb.select_max_column_value(
        LEDGER_STATEMENT, DB_entry_date, iban=bank.iban)
    if ledger_max_entry_date is None:
        ledger_max_entry_date = START_DATE_LEDGER
    clause_amount_0 = ' '.join([DB_amount, '!=', str(0)])
    statements = mariadb.select_table(
        STATEMENT, '*', result_dict=True,
        date_name=DB_entry_date,
        period=(ledger_max_entry_date, date.today()),
        iban=bank.iban,
        clause=clause_amount_0
    )
    if statements:
        # get ledger account_number assigned to iban of bank-account
        result = mariadb.select_table(
            LEDGER_COA, [DB_account, DB_name], result_dict=True, portfolio=False, iban=bank.iban)
        if result:
            account_dict = result[0]
        else:
            MessageBoxInfo(message=MESSAGE_TEXT['ACCOUNT_IBAN_MISSED'].format(
                bank.bank_name, bank.account_product_name, bank.account_number))
            return

        if account_dict == NOT_ASSIGNED:  # cancel download of this bank account
            MessageBoxInfo(message=MESSAGE_TEXT['ACCOUNT_IBAN_MISSED'].format(
                bank.bank_name, bank.account_product_name, bank.account_number))
            return
        # initialize credit/debit
        opening_balance = statements[0][DB_opening_balance]
        if statements[0][DB_opening_status] == DEBIT:
            opening_balance = -opening_balance
        # check and store statement records in ledger table

        for statement_dict in statements:
            iban = statement_dict[DB_iban]
            entry_date = statement_dict[DB_entry_date]
            counter = statement_dict[DB_counter]
            status = statement_dict[DB_status]
            if mariadb.row_exists(LEDGER_STATEMENT, iban=iban, entry_date=entry_date,  counter=counter, status=status):
                pass  # statement already aasigned in ledger
            else:
                # create ledger
                from_id_no = entry_date.year * 1000000
                to_id_no = (entry_date.year + 1) * 1000000
                clause = ' '.join(
                    [DB_id_no, ">", str(from_id_no), 'AND', DB_id_no, "<", str(to_id_no)])
                max_id_no = mariadb.select_max_column_value(
                    LEDGER, DB_id_no, clause=clause)
                if max_id_no:
                    id_no = max_id_no + 1
                else:
                    id_no = from_id_no + 1
                ledger_dict = {DB_id_no: id_no}
                statement_to_ledger_fields = [
                    DB_entry_date,
                    DB_date,
                    DB_purpose_wo_identifier,
                    DB_amount,
                    DB_currency,
                    DB_applicant_name
                ]
                for ledger_field_name in statement_to_ledger_fields:
                    ledger_value = statement_dict[ledger_field_name]
                    if ledger_value:
                        ledger_dict[ledger_field_name] = ledger_value
                if statement_dict[DB_status] == CREDIT:
                    ledger_dict[DB_credit_account] = account_dict[DB_account]
                    ledger_dict[DB_debit_account] = _recommend_account(
                        mariadb, account_dict[DB_account], statement_dict, posting_text_credit_dict)
                else:
                    ledger_dict[DB_debit_account] = account_dict[DB_account]
                    ledger_dict[DB_credit_account] = _recommend_account(
                        mariadb, account_dict[DB_account], statement_dict, posting_text_debit_dict)
                mariadb.execute_insert(LEDGER,  ledger_dict)
                # connect to ledger_statemnt
                ledger_statement_dict = {}
                ledger_statement_dict[DB_iban] = statement_dict[DB_iban]
                ledger_statement_dict[DB_entry_date] = statement_dict[DB_entry_date]
                ledger_statement_dict[DB_counter] = statement_dict[DB_counter]
                ledger_statement_dict[DB_status] = statement_dict[DB_status]
                ledger_statement_dict[DB_id_no] = id_no
                mariadb.execute_insert(LEDGER_STATEMENT, ledger_statement_dict)
        # check balances of LEDGER and STATEMENT table
        period = (ledger_max_entry_date, date(date.today().year, 12, 31))
        # compare balances
        credit = mariadb.select_table_sum(
            LEDGER, DB_amount, date_name=DB_entry_date, period=period, credit_account=account_dict[DB_account])
        if credit is None:
            credit = 0
        debit = mariadb.select_table_sum(
            LEDGER, DB_amount, date_name=DB_entry_date, period=period, debit_account=account_dict[DB_account])
        if debit is None:
            debit = 0
        ledger_balance = opening_balance + credit - debit
        closing_balance = statement_dict[DB_closing_balance]
        if statement_dict[DB_closing_status] == DEBIT:
            closing_balance = -closing_balance
        if closing_balance != ledger_balance:
            MessageBoxInfo(
                message=MESSAGE_TEXT['BALANCE_DIFFERENCE'].format(
                    bank.account_product_name, bank.account_number, closing_balance,
                    account_dict[DB_name], account_dict[DB_account], ledger_balance,
                    str(dec2.subtract(closing_balance, ledger_balance))
                ),
                bank=bank, information=WARNING
            )
