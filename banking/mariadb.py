'''
Created on 26.11.2019
__updated__ = "2025-02-06"
@author: Wolfgang Kramer
'''

import sqlalchemy

from mariadb import connect, Error
from re import compile
from itertools import chain
from datetime import date
from inspect import stack
from json import dumps, loads
from collections import namedtuple

from banking.declarations_mariadb import (
    TABLE_NAMES,
    TABLE_FIELDS,
    TABLE_FIELDS_PROPERTIES,
    DATABASE_FIELDS_PROPERTIES,
    FieldsProperty,

    DATABASES,
    DB_id_no, DB_iban,
    DB_entry_date,
    DB_name, DB_counter, DB_price_date, DB_ISIN,
    DB_purpose_wo_identifier,
    DB_status, DB_symbol,
    BANKIDENTIFIER,
    CREATE_TABLES,
    HOLDING, HOLDING_VIEW,
    ISIN, PRICES, LEDGER, LEDGER_VIEW, LEDGER_COA, LEDGER_STATEMENT,
    SERVER, STATEMENT,
    TRANSACTION, TRANSACTION_VIEW,
    DB_credit_account, DB_debit_account,
)
from banking.declarations import (
    BANK_MARIADB_INI,
    CREDIT, DEBIT,
    TRUE, FALSE,
    HoldingAcquisition,
    Informations,
    ERROR,
    INFORMATION,
    KEY_ACC_IBAN, KEY_ACC_ACCOUNT_NUMBER, KEY_ACC_ALLOWED_TRANSACTIONS, KEY_ACC_PRODUCT_NAME, KEY_ACC_OWNER_NAME,
    KEY_LEDGER,
    MESSAGE_TEXT,
    NOT_ASSIGNED,
    ORIGIN,
    PERCENT,
    SCRAPER_BANKDATA, START_DATE_STATEMENTS,
    TRANSACTION_RECEIPT, TRANSACTION_DELIVERY,
    WARNING,
)
from banking.formbuilts import (
    MessageBoxError, MessageBoxInfo,
    TYP_ALPHANUMERIC, TYP_DECIMAL, TYP_DATE,
    WM_DELETE_WINDOW
)
from banking.ledger import transfer_statement_to_ledger
from banking.utils import dec2, date_days, date_yyyymmdd, shelve_get_key, remove_obsolete_iban_rows, bankdata_informations_append

# statement begins with SELECT or is a Selection via CTE and begins with WITH
select_statement = compile(r'^SELECT|^WITH')
rowcount_statement = compile(r'^UPDATE|^DELETE|^INSERT|^REPLACE')

'''
Cursor attributes
.description
This read-only attribute is a sequence of 7-item sequences.

Each of these sequences contains information describing one result column:

name
type_code
display_size
internal_size
precision
scale
null_ok
'''

# used type_codes
TYPE_CODE_VARCHAR = 253
TYPE_CODE_CHAR = 254,
TYPE_CODE_DECIMAL = 246
TYPE_CODE_DATE = 10
TYPE_CODE_INT = 3
TYPE_CODE_SMALLINT = 2


def _sqlalchemy_exception(title, storage, info):
    '''
    SQLAlchemy Error Handling
    '''

    MessageBoxInfo(title=title, information_storage=storage, information=ERROR,
                   message=MESSAGE_TEXT['SQLALCHEMY_ERROR'].format('MESSAGE', info.args[0]))
    MessageBoxInfo(title=title, information_storage=storage, information=ERROR,
                   message=MESSAGE_TEXT['SQLALCHEMY_ERROR'].format('STATEMENT', info.statement))
    MessageBoxInfo(title=title, information_storage=storage, information=ERROR,
                   message=MESSAGE_TEXT['SQLALCHEMY_ERROR'].format('PARAMS', info.params))


class MariaDB(object):
    '''
    Create Connection MARIADB
    Create MARIADB Tables
    Retrieve Records from MARIADB Tables
    Insert and Modify Records of MARIADB Tables
    '''

    def __init__(self, user, password, database):

        self.user = user
        self.password = password
        self.database = database.lower()
        self.table_names = []
        self.host = "localhost"
        try:
            conn = connect(
                host="localhost", user=self.user, password=self.password)
            cur = conn.cursor()
            sql_statement = "CREATE DATABASE IF NOT EXISTS " + self.database.upper()
            cur.execute(sql_statement)
            sql_statement = "show databases"
            cur.execute(sql_statement)
            for databases in cur:
                if databases[0] not in ['information_schema', 'mysql', 'performance_schema']:
                    DATABASES.append(databases[0])
            conn = connect(user=self.user, password=self.password, host=self.host,
                           database=self.database)
            self.cursor = conn.cursor()
            self.conn = conn
            self.conn.autocommit = True
            for sql_statement in CREATE_TABLES:
                self.cursor.execute(sql_statement)
                if sql_statement.startswith("CREATE ALGORITHM"):
                    sql_statement = sql_statement.replace(
                        "CREATE ALGORITHM", "ALTER ALGORITHM")
                    sql_statement = sql_statement.replace(
                        "IF NOT EXISTS", "")
                    # update view data if view already exists
                    self.cursor.execute(sql_statement)
            self._init_database_info()
        except Error as error:
            message = MESSAGE_TEXT['MARIADB_ERROR_SQL'].format(
                sql_statement, '')
            message = '\n\n'.join([
                message, MESSAGE_TEXT['MARIADB_ERROR'].format(error.errno, error.errmsg)])
            filename = stack()[1][1]
            line = stack()[1][2]
            method = stack()[1][3]
            message = '\n\n'.join(
                [message, MESSAGE_TEXT['STACK'].format(method, line, filename)])
            MessageBoxInfo(message=message)

    def _init_database_info(self):
        '''

             Dictionary: TABLE_FIELDS
                         values are fieldnames of a table
             Dictionary: FIELD_>table_name<
                         values are field_definition tuples


                            (column_name, character_maximum_length, numeric_scale, numeric_precision, data_type)
        '''
        # initialize list TABLE_NAMES
        sql_statement = "SELECT table_name FROM information_schema.tables WHERE table_schema = database();"
        '''
        Initialize list TABLE_NAMES (list of database table_names)
        Example TABLE_NAMES
        <class 'list'>: ['bankidentifier', 'holding',  ...]
        '''
        TABLE_NAMES.extend(list(chain(*self.execute(sql_statement))))
        self.table_names = TABLE_NAMES
        # initialize dict FIELDS->table< (properties of column fields)
        column_properties = ['column_name', 'character_maximum_length',
                             'numeric_scale', 'numeric_precision', 'data_type', 'column_comment']
        Property = namedtuple('Property', column_properties)
        for table in TABLE_NAMES:
            sql_statement = ("SELECT " + ','.join(column_properties) +
                             " FROM information_schema.columns " +
                             " WHERE table_schema = database() " +
                             " AND table_name = '" + table + "' ORDER BY ordinal_position;")
            result = self.execute(sql_statement)
            table_fields_properties = {}
            for _tuple in result:
                column_names = Property(*_tuple)
                if column_names.data_type == "decimal":
                    typ = TYP_DECIMAL
                elif column_names.data_type == "date":
                    typ = TYP_DATE
                else:
                    typ = TYP_ALPHANUMERIC
                if column_names.character_maximum_length:  # char fields, ...
                    properties = FieldsProperty(
                        column_names.character_maximum_length, 0, typ, column_names.column_comment, column_names.data_type)
                elif column_names.numeric_scale:  # int/decimal_fields, ....
                    properties = FieldsProperty(
                        column_names.numeric_precision, column_names.numeric_scale, typ, column_names.column_comment, column_names.data_type)
                # float / double fields, ....
                elif column_names.numeric_precision:
                    properties = FieldsProperty(
                        column_names.numeric_precision, 0, typ, column_names.column_comment, column_names.data_type)
                elif typ == 'date':
                    properties = FieldsProperty(
                        10, 0, typ, column_names.column_comment, column_names.data_type)
                else:
                    properties = FieldsProperty(
                        30, 0, typ, column_names.column_comment, column_names.data_type)
                table_fields_properties[column_names.column_name] = properties
            '''
             Initialize dict TABLE_FIELDS (column names of table)
              KEY: table_name
                  VALUE: list of table_fields
            '''
            TABLE_FIELDS[table] = list(
                map(lambda x: x[0], result))
            '''
            Initialize dict TABLE_FIELDS_PROPERTIES (field properties of each column_name of a table)
                KEY: table_name
                    KEY: field_name
                        VALUE: namedtuple('FieldsProperty', 'length, places, typ, comment, data_type')
            '''
            TABLE_FIELDS_PROPERTIES[table] = table_fields_properties
            '''
            Initialize dict of DATABASE_FIELDS_PROPERTIES (field properties of all column_names of database)
                KEY: field_name
                    VALUE: namedtuple('FieldsProperty', 'length, places, typ, comment, data_type')
            '''
            DATABASE_FIELDS_PROPERTIES.update(TABLE_FIELDS_PROPERTIES[table])

    def _holdings(self, bank):
        '''
        Storage of holdings on a daily basis of >bank.account_number<
        in MARIADB table HOLDING

        '''

        self.execute('START TRANSACTION;')
        holdings = bank.dialogs.holdings(bank)
        if holdings:
            price_date_holding = None
            for holding in holdings:  # find more frequent price_date
                if not price_date_holding or price_date_holding < holding[DB_price_date]:
                    price_date_holding = holding[DB_price_date]
            weekday = date_yyyymmdd.convert(price_date_holding).weekday()
            if weekday == 5:  # Saturday
                price_date_holding = date_yyyymmdd.subtract(
                    price_date_holding, 1)
            elif weekday == 6:  # Sunday
                price_date_holding = date_yyyymmdd.subtract(
                    price_date_holding, 2)
            if price_date_holding:  # delete last price_date in case of repeated download
                self.execute_delete(HOLDING, iban=bank.iban,
                                    price_date=price_date_holding)
            for holding in holdings:
                if not self.row_exists(ISIN, name=holding[DB_name]):
                    field_dict = {
                        DB_ISIN: holding[DB_ISIN], DB_name: holding[DB_name]}
                    self.execute_replace(ISIN, field_dict)
                name_ = holding[DB_name]
                del holding[DB_name]
                holding[DB_price_date] = price_date_holding
                holding['iban'] = bank.iban
                self.execute_replace(HOLDING, holding)
            # Update acquisition_amount (exists not in MT535 data)
                button_state = self._set_acquisition_amount(
                    bank, holding[DB_ISIN], name_)
                if button_state == WM_DELETE_WINDOW:
                    self.execute('ROLLBACK')
                    MessageBoxInfo(
                        message=MESSAGE_TEXT['DOWNLOAD_REPEAT'].format(bank.bank_name))
                    return
            self.execute('COMMIT;')
        return holdings

    def _set_acquisition_amount(self, bank, isin, name_):

        button_state = None
        sql_statement = ("SELECT price_date, price_currency, market_price, acquisition_price,"
                         " pieces, amount_currency, total_amount, acquisition_amount, origin"
                         " FROM " + HOLDING +
                         " WHERE iban=? AND isin_code=?"
                         " ORDER BY price_date DESC"
                         " LIMIT 2")
        vars_ = (bank.iban, isin, )
        result = self.execute(sql_statement, vars_=vars_)
        if not result:
            return
        data = []
        for row in result:
            data.insert(0, HoldingAcquisition(*row))
        pieces = data[0].pieces - data[-1].pieces
        if (len(data) > 1 and pieces == 0 and
                data[0].acquisition_price == data[-1].acquisition_price):
            # no change in position
            acquisition_amount = data[0].acquisition_amount
        else:
            if data[-1].price_currency == PERCENT:
                # ad just acquisition amount of percent price positions manually
                MessageBoxInfo(message=MESSAGE_TEXT['ACQUISITION_AMOUNT'].format(bank.bank_name, bank.iban, name_, isin),
                               bank=bank, information=WARNING)
                acquisition_amount = data[0].acquisition_amount
            else:
                acquisition_amount = dec2.multiply(
                    data[-1].pieces, data[-1].acquisition_price)
        data[-1].acquisition_amount = acquisition_amount
        self.update_holding_acquisition(bank.iban, isin, data[-1])
        return button_state

    def _statements(self, bank):
        '''
        Storage of statements of >bank.account_number< starting from the last stored entry_date
        in table STATEMENT.
        For the first time: all available statements will be stored.
        Use of touchdowns is not implemented
        '''
        sql_statement = (
            "select max(entry_date) from " + STATEMENT + " where iban=?"
        )
        vars_ = (bank.iban,)
        max_entry_date = self.execute(sql_statement, vars_=vars_)
        if max_entry_date[0][0]:
            bank.from_date = max_entry_date[0][0]
        else:
            bank.from_date = START_DATE_STATEMENTS
        bank.to_date = date.today()
        if bank.scraper:
            bank.to_date = ''.join(str(bank.to_date))
            bank.from_date = ''.join(str(bank.from_date))
            statements = bank.download_statements(bank)
        else:
            statements = bank.dialogs.statements(bank)
        if statements:
            entry_date = None
            for statement in statements:
                if statement[DB_entry_date] != entry_date:
                    entry_date = statement[DB_entry_date]
                    counter = 0
                statement[DB_iban] = bank.iban
                statement[DB_counter] = counter
                if self.row_exists(STATEMENT, iban=statement[DB_iban], entry_date=statement[DB_entry_date], counter=statement[DB_counter]):
                    pass
                else:
                    self.execute_insert(STATEMENT, statement)
                counter += 1
            self.execute('COMMIT;')
            if shelve_get_key(BANK_MARIADB_INI, KEY_LEDGER):
                transfer_statement_to_ledger(self, bank)

        return statements

    def _order_clause(self, sql_statement, order=None):

        if order is not None:
            if isinstance(order, list):
                order = ','.join(order)
            sql_statement = sql_statement + " ORDER BY " + order
        return sql_statement

    def _where_clause(self, clause=None, date_name=None, **kwargs):
        '''
        Generates WHERE Clause of kwargs items

        kwargs:      >database_fieldname<=>value< AND ....  >database_fieldname< IN >list<  ...
        clause:      additional >AND< >OR< condition parts
        date_name:   date field_name of period key

        result:  where    WHERE >database_fieldname<=? AND .... AND '
                 vars_    (>value<, ..>list<, .....)
        '''
        WHERE = ' WHERE '
        vars_ = ()
        where = WHERE
        if clause:
            where = where + ' ' + clause + '   AND '
        for key, value in kwargs.items():
            if key == 'period':
                from_date, to_date = value
                if isinstance(from_date, date):
                    from_date = date_days.convert(from_date)
                if isinstance(to_date, date):
                    to_date = date_days.convert(to_date)
                if where != WHERE:
                    vars_ = vars_ + (from_date, to_date)
                else:
                    vars_ = (from_date, to_date)
                where = where + " price_date>=? AND price_date<=? AND "
                if date_name:  # standard period field_name 'price_date' replaced by date_name
                    where = where.replace(DB_price_date, date_name)
            else:
                if isinstance(value, list):
                    where = where + ' ' + key + ' IN ('
                    for item in value:
                        where = where + "?,"
                        if isinstance(item, date):
                            item = date_days.convert(item)
                        vars_ = vars_ + (item,)
                    where = where[:-1] + ') AND '
                else:
                    where = where + ' ' + key + '=? AND '
                    vars_ = vars_ + (value,)
        if vars_ or clause:
            return where[0:-5], vars_
        else:
            return ' ', vars_

    def all_accounts(self, bank, holdings):
        '''
        Insert downloaded  Bank Data in Database

        holdings: ignores holdings if False
        '''
        message = ' '.join(
            [MESSAGE_TEXT['DOWNLOAD_BANK'].format(bank.bank_name), '\n\n'])
        bankdata_informations_append(INFORMATION, message)
        for account in bank.accounts:
            bank.account_number = account[KEY_ACC_ACCOUNT_NUMBER]
            bank.account_product_name = account[KEY_ACC_PRODUCT_NAME]
            bank.iban = account[KEY_ACC_IBAN]
            bank.owner_name = account[KEY_ACC_OWNER_NAME]
            information = MESSAGE_TEXT['DOWNLOAD_ACCOUNT'].format(
                bank.bank_name, bank.owner_name, bank.account_number, bank.account_product_name, bank.iban)
            if bank.scraper:
                if 'HKKAZ' in account[KEY_ACC_ALLOWED_TRANSACTIONS]:
                    bankdata_informations_append(INFORMATION, information)
                    if self._statements(bank) is None:
                        bankdata_informations_append(
                            WARNING, MESSAGE_TEXT['DOWNLOAD_NOT_DONE'].format(bank.bank_name))
                        return
            else:
                if 'HKWPD' in account[KEY_ACC_ALLOWED_TRANSACTIONS] and holdings:
                    bankdata_informations_append(INFORMATION, information)
                    if self._holdings(bank) is None:
                        bankdata_informations_append(
                            WARNING, MESSAGE_TEXT['DOWNLOAD_NOT_DONE'].format(bank.bank_name))
                        return
                if 'HKKAZ' in account[KEY_ACC_ALLOWED_TRANSACTIONS]:
                    bankdata_informations_append(INFORMATION, information)
                    if self._statements(bank) is None:
                        bankdata_informations_append(
                            WARNING, MESSAGE_TEXT['DOWNLOAD_NOT_DONE'].format(bank.bank_name))
                        return
        bankdata_informations_append(
            INFORMATION, MESSAGE_TEXT['DOWNLOAD_DONE'].format(bank.bank_name) + '\n\n')
        if bank.scraper:
            try:
                bank.driver.quit()
            except Exception:
                pass

    def all_holdings(self, bank):
        '''
        Insert downloaded  Holding Bank Data in Database
        '''
        bankdata_informations_append(
            INFORMATION, MESSAGE_TEXT['DOWNLOAD_BANK'].format(bank.bank_name))
        for account in bank.accounts:
            bank.account_number = account[KEY_ACC_ACCOUNT_NUMBER]
            bank.iban = account[KEY_ACC_IBAN]
            if 'HKWPD' in account[KEY_ACC_ALLOWED_TRANSACTIONS]:
                bankdata_informations_append(INFORMATION, MESSAGE_TEXT['DOWNLOAD_ACCOUNT'].format(
                    bank.bank_name, '', bank.account_number, bank.account_product_name, bank.iban))
                if self._holdings(bank) is None:
                    bankdata_informations_append(
                        WARNING, MESSAGE_TEXT['DOWNLOAD_NOT_DONE'].format(bank.bank_name))
                    return

    def all_statements(self, bank):
        '''
        Insert downloaded  Staement Bank Data in Database
        '''
        bankdata_informations_append(
            INFORMATION, MESSAGE_TEXT['DOWNLOAD_BANK'].format(bank.bank_name))
        for account in bank.accounts:
            bank.account_number = account[KEY_ACC_ACCOUNT_NUMBER]
            bank.account_product_name = account[KEY_ACC_PRODUCT_NAME]
            bank.iban = account[KEY_ACC_IBAN]
            if 'HKKAZ' in account[KEY_ACC_ALLOWED_TRANSACTIONS]:
                bankdata_informations_append(INFORMATION, MESSAGE_TEXT['DOWNLOAD_ACCOUNT'].format(
                    bank.bank_name, '', bank.account_number, bank.account_product_name, bank.iban))
                if self._statements(bank) is None:
                    bankdata_informations_append(
                        WARNING, MESSAGE_TEXT['DOWNLOAD_NOT_DONE'].format(bank.bank_name))
                    return
        bankdata_informations_append(
            INFORMATION, MESSAGE_TEXT['DOWNLOAD_DONE'].format(bank.bank_name))

    def destroy_connection(self):
        '''
        close connection >database<
        '''
        if self.conn.is_connected():
            self.conn.close()
            self.cursor.close()

    def execute(self, sql_statement, vars_=None, duplicate=False, result_dict=False):
        '''
        Parameter:  duplicate=True --> Ignore Error 1062 (Duplicate Entry)
                    result_dict -----> True: returns a list of dicts

        SQL SELECT:
        Method fetches all (or all remaining) rows of a query  result set
        and returns a list of tuples.
        If no rows are available, it returns an empty list.
        SQL REPLACE, UPDATE, ...
        Method executes SQL statement; no result set will be returned!
        rowcount = True   returns row_count of UPDATE, INSERT; DELETE
        '''
        try:
            if vars_:
                result = self.cursor.execute(sql_statement, vars_)
            else:
                self.cursor.execute(sql_statement)
            if select_statement.match(sql_statement.upper()):
                # returns result if sql_statement begins with SELECT
                result = []
                for item in self.cursor.fetchall():
                    result.append(item)
                if result_dict:
                    # contains fieldname in description tuple
                    fields = list(
                        map(lambda field: field[0], self.cursor.description))
                    # returns list of dictionaries
                    result = list(
                        map(lambda row: dict(zip(fields, row)), result))
                return result
            if rowcount_statement.match(sql_statement.upper()):
                # returns result if sql_statement begins with REPLACE, UPDATE,
                # DELETE, INSERT
                result = self.cursor.execute('SELECT row_count()')
                if result:
                    counted, = result[0]
                else:
                    counted = None
                return counted
            return None
        except Error as error:
            if duplicate and error.errno == 1062:
                MessageBoxInfo(message=MESSAGE_TEXT['MARIADB_DUPLICATE'].format(
                    sql_statement, error, vars_))
                return error.errno
            else:
                message = MESSAGE_TEXT['MARIADB_ERROR_SQL'].format(
                    sql_statement, vars_)
                try:
                    message = '\n\n'.join([
                        message, MESSAGE_TEXT['MARIADB_ERROR'].format(error.errno, error.errmsg)])
                except:
                    message = str(error)
                if sql_statement.upper().startswith('LOAD'):
                    MessageBoxInfo(message=message)
                    return False
                filename = stack()[1][1]
                line = stack()[1][2]
                method = stack()[1][3]
                message = '\n\n'.join(
                    [message, MESSAGE_TEXT['STACK'].format(line, filename, method)])
                MessageBoxError(message=message)
                return False  # thread checking

    def execute_insert(self, table, field_dict):
        '''
        Insert Record in MARIADB table

        '''
        set_fields = ' SET '
        vars_ = ()
        for key_ in field_dict.keys():
            set_fields = set_fields + ' ' + key_ + '=?, '
            if table == ISIN and key_ == DB_name:
                field_dict[key_] = field_dict[key_].upper()
            vars_ = vars_ + (field_dict[key_],)
        sql_statement = "INSERT INTO " + table + set_fields
        sql_statement = sql_statement[:-2]
        self.execute(sql_statement, vars_=vars_)

    def execute_replace(self, table, field_dict):
        '''
        Insert/Change Record in MARIADB table
        '''
        set_fields = ' SET '
        vars_ = ()
        for key_ in field_dict.keys():
            set_fields = set_fields + ' ' + key_ + '=?, '
            if table == ISIN and key_ == DB_name:
                field_dict[key_] = field_dict[key_].upper()
            vars_ = vars_ + (field_dict[key_],)
        sql_statement = "REPLACE INTO " + table + set_fields
        sql_statement = sql_statement[:-2]
        self.execute(sql_statement, vars_=vars_)

    def execute_update(self, table, field_dict, **kwargs):
        '''
        Updates columns of existing rows in the MARIADB table with new values
        '''
        where, vars_where = self._where_clause(**kwargs)
        set_fields = ' SET '
        vars_set = ()
        for key_ in field_dict.keys():
            set_fields = set_fields + ' ' + key_ + '=?, '
            vars_set = vars_set + (field_dict[key_],)
        sql_statement = "UPDATE " + table + set_fields
        sql_statement = sql_statement[:-2] + where
        self.execute(sql_statement, vars_=vars_set + vars_where)

    def execute_delete(self, table, **kwargs):
        '''
        Deletion of record in MARIADB table
        '''
        where, vars_ = self._where_clause(**kwargs)
        sql_statement = "DELETE FROM " + table + where
        self.execute(sql_statement, vars_=vars_)

    def import_bankidentifier(self, filename):
        '''
        Import CSV file into table bankidentifier
        Download CSV from https://www.bundesbank.de/de/aufgaben/
        unbarer-zahlungsverkehr/serviceangebot/bankleitzahlen/
        download-bankleitzahlen-602592
        '''
        sql_statement = "DELETE FROM " + BANKIDENTIFIER
        self.execute(sql_statement)
        sql_statement = ("LOAD DATA LOW_PRIORITY LOCAL INFILE '" + filename +
                         "' REPLACE INTO TABLE " + BANKIDENTIFIER +
                         " CHARACTER SET latin1 FIELDS TERMINATED BY ';'"
                         " OPTIONALLY ENCLOSED BY '\"' ESCAPED BY '\"'"
                         " LINES TERMINATED BY '\r\n' IGNORE 1 LINES"
                         " (`code`, `payment_provider`, `payment_provider_name`, `postal_code`,"
                         " `location`, `name`, `pan`, `bic`, `check_digit_calculation`, `record_number`, `change_indicator`, `code_deletion`, `follow_code`);"
                         )
        self.execute(sql_statement)
        sql_statement = "DELETE FROM " + BANKIDENTIFIER + " WHERE payment_provider='2'"
        self.execute(sql_statement)
        return

    def import_server(self, filename):
        '''
        Import CSV file into table server
                CSV_File contains 28 columns
        Registration see https://www.hbci-zka.de/register/prod_register.htm

        Imports only bank_code and server
        '''
        columns = 28
        csv_columns = ['@VAR' + str(x) for x in range(columns)]
        csv_columns[1] = 'code'
        csv_columns[24] = 'server'
        csv_columns = ', '.join([*csv_columns])
        sql_statement = "DELETE FROM " + SERVER
        self.execute(sql_statement)
        sql_statement = ("LOAD DATA LOW_PRIORITY LOCAL INFILE '" + filename +
                         "' REPLACE INTO TABLE " + SERVER +
                         " CHARACTER SET latin1 FIELDS TERMINATED BY ';'"
                         " OPTIONALLY ENCLOSED BY '\"' ESCAPED BY '\"'"
                         " LINES TERMINATED BY '\\r\\n'"
                         " IGNORE 1 LINES (" + csv_columns + ");")
        self.execute(sql_statement)
        sql_statement = "DELETE FROM " + SERVER + " WHERE server='\r'"
        for item in list(SCRAPER_BANKDATA.keys()):
            code = item
            server = SCRAPER_BANKDATA[code][0]
            sql_statement = ("INSERT INTO " + SERVER +
                             " SET code=?, server=?")
            vars_ = (code, server)  # bankdata[0] = >login Link<
            self.execute(sql_statement, vars_=vars_)
        return

    def import_transaction(self, iban, filename):
        '''
        Import CSV file into table transaction
        '''
        sql_statement = ("LOAD DATA LOW_PRIORITY LOCAL INFILE '" + filename +
                         "' REPLACE INTO TABLE " + TRANSACTION +
                         " CHARACTER SET latin1 FIELDS TERMINATED BY ';'"
                         " OPTIONALLY ENCLOSED BY '\"' ESCAPED BY '\"'"
                         " LINES TERMINATED BY '\r\n' IGNORE 1 LINES"
                         " (price_date, isin_code, counter, pieces, price)"
                         " SET iban='" + iban + "', transaction_type='"
                         + TRANSACTION_RECEIPT + "', "
                         " price_currency='EUR', amount_currency='EUR',"
                         " posted_amount=price*pieces, "
                         " origin='" + filename[-50:] + "'"
                         ";"
                         )
        self.execute(sql_statement)
        sql_statement = ("UPDATE " + TRANSACTION +
                         " SET transaction_type = ?, counter=Abs(counter), "
                         "pieces=Abs(pieces), posted_amount=Abs(posted_amount) WHERE pieces < 0")
        vars_ = (TRANSACTION_DELIVERY,)
        self.execute(sql_statement, vars_=vars_)

    def import_prices(self, title, dataframe):
        '''
        Insert/Replace prices
        '''

        # engine = sqlalchemy.create_engine(
        #    "mariadb+mariadbconnector://root:" + self.password + "@127.0.0.1:3306/" + self.database)
        credentials = ''.join(
            [self.user, ":", self.password, "@", self.host, "/", self.database])
        '''
        if_exists{>fail<, >replace<, >append<}, default >fail<
            How to behave if the table already exists.
            fail: Raise a ValueError.
            replace: Drop the table before inserting new values.
            append: Insert new values to the existing table.
        '''
        try:
            engine = sqlalchemy.create_engine(
                "mariadb+mariadbconnector://" + credentials)
            dataframe.to_sql(PRICES, con=engine, if_exists="append",
                             index_label=['symbol', 'price_date'])
            self.execute('COMMIT')
            return True
        except sqlalchemy.exc.SQLAlchemyError as info:
            _sqlalchemy_exception(
                title, Informations.PRICES_INFORMATIONS, info)
            return False

    def select_dict(self, table, key_name, value_name, order=DB_name, **kwargs):
        '''
        result: dictionary
        '''
        where, vars_ = self._where_clause(**kwargs)
        sql_statement = "SELECT " + key_name + ', ' + \
            value_name + " FROM " + table + where
        sql_statement = self._order_clause(sql_statement, order=order)
        result = self.execute(sql_statement, vars_=vars_)
        if result and len(result[0]) == 2:
            return dict(result)
        return {}

    def select_isin_adjustments(self):
        '''
        Return:  List of tuples (name, symbol, adjustments) of table ISIN with adjustments
        '''
        sql_statement = "SELECT name, symbol, adjustments FROM " + \
            ISIN + "  WHERE adjustments <> '{}'"
        result = self.execute(sql_statement)
        names_list = list(map(lambda x: x[0], result))
        names_symbol_dict = dict(list(map(lambda x: (x[0], x[1]), result)))
        names_adjustment_dict = dict(list(map(lambda x: (x[0], x[2]), result)))
        return names_list, names_symbol_dict, names_adjustment_dict

    def select_isin_with_ticker(self, field_list, order=None, **kwargs):

        where, vars_ = self._where_clause(**kwargs)
        if isinstance(field_list, list):
            field_list = ','.join(field_list)
        sql_statement = "SELECT " + field_list + \
            " FROM " + ISIN + " WHERE symbol != 'NA'"
        if vars_:
            sql_statement = ' '.join([sql_statement, 'AND', where])
        sql_statement = self._order_clause(sql_statement, order=order)
        return self.execute(sql_statement, vars_=vars_)

    def select_holding_all_total(self, **kwargs):

        where, vars_ = self._where_clause(**kwargs)
        sql_statement = ("SELECT price_date, SUM(total_amount), SUM(acquisition_amount) "
                         " FROM " + HOLDING + where)
        sql_statement = sql_statement + " GROUP BY price_date ORDER BY price_date ASC;"
        return self.execute(sql_statement, vars_=vars_)

    def select_holding_total(self, **kwargs):

        where, vars_ = self._where_clause(**kwargs)
        sql_statement = ("SELECT price_date, total_amount_portfolio, SUM(acquisition_amount)"
                         " FROM " + HOLDING + where +
                         " GROUP BY price_date ORDER BY price_date ASC;")
        return self.execute(sql_statement, vars_=vars_)

    def select_holding_data(self,
                            field_list='isin_code, name, total_amount, acquisition_amount, pieces, market_price, price_currency, amount_currency',
                            result_dict=True,
                            **kwargs):
        '''
        returns a list (of dictionaries)
        '''
        if field_list:
            where, vars_ = self._where_clause(**kwargs)
            if isinstance(field_list, list):
                field_list = ','.join(field_list)
            sql_statement = "SELECT " + field_list + " FROM " + HOLDING_VIEW + where
            result = self.execute(sql_statement, vars_=vars_,
                                  result_dict=result_dict)
            return result
        else:
            return []

    def select_holding_last(self, iban, isin, period,
                            field_list='price_date, market_price, pieces, total_amount, acquisition_amount'):
        '''
        returns tuple with last portfolio entries
        '''
        last_download = self.select_max_column_value(
            HOLDING, DB_price_date, iban=iban, isin_code=isin, period=period)
        if last_download is not None:
            if isinstance(field_list, list):
                field_list = ','.join(field_list)
            sql_statement = ("SELECT " + field_list + " FROM " + HOLDING_VIEW +
                             " WHERE iban=? AND isin_code=? AND price_date=?")
            vars_ = (iban, isin, str(last_download))
            result = self.execute(sql_statement, vars_=vars_)
            return result[0]
        else:
            return None

    def select_holding_fields(self, field_list='price_date', **kwargs):

        where, vars_ = self._where_clause(**kwargs)
        if isinstance(field_list, list):
            field_list = ','.join(field_list)
        sql_statement = "SELECT DISTINCT " + field_list + " FROM " + HOLDING + where
        result = []
        for item in self.execute(sql_statement, vars_=vars_):
            field_value, = item
            result.append(field_value)
        return result

    def select_ledger_account(self, field_list, account, order=None, result_dict=True, date_name=None, **kwargs):
        '''
        select ledger rows of account
        '''
        if field_list:
            where, vars_ = self._where_clause(date_name=date_name, **kwargs)
            if isinstance(field_list, list):
                field_list = ','.join(field_list)
            account_condition = " AND " + \
                ''.join(["(", DB_credit_account, "='", account,
                         "' OR ", DB_debit_account, "='", account, "')"])
            sql_statement = "SELECT " + field_list + " FROM " + \
                LEDGER_VIEW + where + account_condition
            sql_statement = self._order_clause(sql_statement, order=order)
            return self.execute(sql_statement, vars_=vars_, result_dict=result_dict)
        else:
            return []

    def select_ledger_posting_text_account(self, iban, credit=True):
        '''
        Recommended credit/debit accounts for used posting_texts
        Creates dict --> key: posting_text
                                value:  credit_account if credit=True or
                                        debit_account if credit=False
        of last 365 days
        '''
        from_date = date_days.convert(date_days.subtract(date.today(), 365))
        if credit:
            status = CREDIT
        else:
            status = DEBIT
        sql_statement = ("SELECT Distinct posting_text, t2.account FROM " + STATEMENT +
                         " AS t1 INNER JOIN (" + LEDGER_COA +
                         " AS t2) ON (t1.iban=t2.iban) WHERE t1.entry_date>'" + from_date +
                         "' AND t1.status='" + status + "';")
        result = self.execute(sql_statement)
        if result:
            return dict(result)
        else:
            return {}

    def select_sepa_fields_in_statement(self, iban, **kwargs):
        '''
        kwargs: sepa_fieldname (only 1!)
        Credit Statement: returns last debit_account of connected ledger_row
        Debit Statement: returns last creditit_account of connected ledger_row

        Not found: returns 'NA'
        '''
        where, vars_ = self._where_clause(
            date_name=DB_entry_date, **kwargs)
        field_list = ','.join(
            [DB_iban, DB_entry_date, DB_counter, DB_status])
        sql_statement = ("SELECT " + field_list + " FROM " +
                         STATEMENT + where + " ORDER by entry_date DESC LIMIT 1")
        sql_statement = sql_statement.replace(DB_purpose_wo_identifier +
                                              '=?', DB_purpose_wo_identifier + ' LIKE ?')
        result = self.execute(sql_statement, vars_=vars_, result_dict=True)
        if result:
            statement_row = result[0]
            id_no = self.select_table(LEDGER_STATEMENT, [DB_id_no],
                                      iban=statement_row[DB_iban], entry_date=statement_row[DB_entry_date],
                                      counter=statement_row[DB_counter], status=statement_row[DB_status])
            if id_no:
                if statement_row[DB_status] == CREDIT:
                    result = self.select_table(
                        LEDGER, DB_debit_account, id_no=id_no[0][0])
                else:
                    result = self.select_table(
                        LEDGER, DB_credit_account, id_no=id_no[0][0])
                if result:
                    return result[0][0]
        return NOT_ASSIGNED

    def select_sepa_transfer_creditor_data(self, **kwargs):

        where, vars_ = self._where_clause(**kwargs)
        sql_statement = ("SELECT applicant_iban, applicant_bic, purpose FROM " + STATEMENT +
                         where + " ORDER BY date DESC;")
        result = self.execute(sql_statement, vars_=vars_)

        if result:
            applicant_iban, applicant_bic, purpose = result[0]
            return applicant_iban, applicant_bic, purpose
        else:
            return None, None, None

    def select_sepa_transfer_creditor_names(self, **kwargs):

        where, vars_ = self._where_clause(**kwargs)
        sql_statement = ("SELECT DISTINCT applicant_name FROM " + STATEMENT +
                         where + " ORDER BY applicant_name ASC;")
        result = self.execute(sql_statement, vars_=vars_)
        creditor_names = []
        for item in result:
            creditor_name, = item
            if creditor_name:
                creditor_names.append(creditor_name)
        return creditor_names

    def select_server_code(self, **kwargs):

        where, vars_ = self._where_clause(**kwargs)
        sql_statement = "SELECT code FROM " + SERVER + where
        result = self.execute(sql_statement, vars_=vars_)
        bank_codes = []
        for item in result:
            bank_code, = item
            bank_codes.append(bank_code)
        return bank_codes

    def select_server(self, **kwargs):

        where, vars_ = self._where_clause(**kwargs)
        sql_statement = "SELECT server FROM " + SERVER + where
        result = self.execute(sql_statement, vars_=vars_)
        servers = []
        for item in result:
            server, = item
            servers.append(server)
        return servers

    def select_table(self, table, field_list, order=None, result_dict=False, date_name=None, **kwargs):

        if field_list:
            where, vars_ = self._where_clause(date_name=date_name, **kwargs)
            if isinstance(field_list, list):
                field_list = ','.join(field_list)
            sql_statement = "SELECT " + field_list + " FROM " + table + where
            sql_statement = self._order_clause(sql_statement, order=order)
            return self.execute(sql_statement, vars_=vars_, result_dict=result_dict)
        else:
            return []

    def select_table_sum(self, table, sum_field, date_name=None, **kwargs):
        '''
        returns sum of a column of the selected rows depending on **kwargs
        '''

        where, vars_ = self._where_clause(date_name=date_name, **kwargs)
        sql_statement = "SELECT SUM(" + sum_field + ") FROM " + table + where
        result = self.execute(sql_statement, vars_=vars_)
        return result[0][0]

    def select_table_distinct(self, table, field_list, order=None, result_dict=False, date_name=None, **kwargs):

        if field_list:
            where, vars_ = self._where_clause(date_name=date_name, **kwargs)
            if isinstance(field_list, list):
                field_list = ','.join(field_list)
            sql_statement = "SELECT DISTINCT " + field_list + " FROM " + table + where
            sql_statement = self._order_clause(sql_statement, order=order)
            return self.execute(sql_statement, vars_=vars_, result_dict=result_dict)
        else:
            return []

    def select_table_next(self, table, field_list, key_name, sign, key_value, result_dict=False, date_name=None, **kwargs):
        '''
        Returns row before (sign '<', '<=') or next row (sign '>', '>=')
        '''

        assert sign in [
            '>', '>=', '<', '<='], 'Comparison Operators {} not allowed'.format(sign)
        if field_list:
            where, vars_ = self._where_clause(date_name=date_name, **kwargs)
            if vars_:
                where = where + ' AND '
            else:
                where = ' WHERE '
            if isinstance(field_list, list):
                field_list = ','.join(field_list)
            sql_statement = "SELECT " + field_list + " FROM " + table + \
                where + key_name + sign + "? ORDER BY " + key_name
            if sign in ['>', '>=']:
                sql_statement = sql_statement + " LIMIT 1"
            else:
                sql_statement = sql_statement + " DESC LIMIT 1"
            vars_ = vars_ + (key_value,)
            return self.execute(sql_statement, vars_=vars_,  result_dict=result_dict)
        else:
            return []

    def select_table_first_or_last(self, table, field_list, order=None, result_dict=False, date_name=None, **kwargs):
        '''
        return one of selection depending on order value and **kwargs

        e.g.: order parameter to select last row of selection
            ' '.join([DB_entry_date, 'DESC,', DB_counter, 'DESC'] or
            ' entry_date DESC, counter DESC '

        e.g.: order parameter to select first row of selection
            ' '.join([DB_entry_date, ',', DB_counter] or
            ' entry_date, counter '
        '''
        where, vars_ = self._where_clause(date_name=date_name, **kwargs)
        if isinstance(field_list, list):
            field_list = ','.join(field_list)
        sql_statement = "SELECT " + field_list + " FROM " + table + where
        if order:
            if isinstance(order, list):
                field_list = ','.join(field_list)
            sql_statement = self._order_clause(sql_statement, order=order)
        sql_statement = sql_statement + " LIMIT 1"
        result = self.execute(sql_statement, vars_=vars_,
                              result_dict=result_dict)
        if result:
            return result[0]
        else:
            return None

    def select_total_amounts(self, **kwargs):

        where, vars_ = self._where_clause(**kwargs)
        where = where.replace(DB_price_date, 'date')
        from_date, to_date = vars_
        vars_ = (str(date_days.add(from_date, 1)), to_date)
        # search first row if no statements/holding in period., use it for as
        # from_date data
        sql_statement = ("WITH max_date_rows AS (SELECT iban AS max_iban, MAX(entry_date) AS max_date FROM " + STATEMENT + " WHERE entry_date <= '" + from_date + "' GROUP BY iban) "
                         "SELECT iban, date('" + from_date + "'), closing_status AS status, closing_balance AS saldo FROM " + STATEMENT + ", max_date_rows WHERE iban = max_iban AND entry_date = max_date GROUP BY iban;")
        first_row_statement = self.execute(sql_statement)
        sql_statement = ("WITH max_date_rows AS (SELECT iban AS max_iban, MAX(price_date) AS max_date FROM " + HOLDING + " WHERE price_date <= '" + from_date + "' GROUP BY iban) "
                         "SELECT iban, date('" + from_date + "'), '" + CREDIT + "' AS status, total_amount_portfolio AS saldo FROM " + HOLDING + ", max_date_rows WHERE iban = max_iban AND price_date = max_date GROUP BY iban;")
        first_row_holding = self.execute(sql_statement)
        sql_statement = ("WITH total_amounts AS ("
                         "SELECT iban, price_date AS date, '" + CREDIT +
                         "' AS status, total_amount_portfolio AS saldo  FROM "
                         + HOLDING + " GROUP BY iban, price_date "
                         " UNION "
                         "SELECT iban, entry_date AS date, closing_status AS status, closing_balance AS saldo FROM "
                         + STATEMENT + " GROUP BY iban, entry_date) "
                         "SELECT iban, date, status, saldo FROM total_amounts " + where)
        result = self.execute(sql_statement, vars_=vars_)
        # remove IBANs of old ledger applications or deleted banks.
        result = remove_obsolete_iban_rows(result)
        first_row_statement = remove_obsolete_iban_rows(first_row_statement)
        return first_row_statement + first_row_holding + result

    def select_max_column_value(self, table, column_name, **kwargs):

        where, vars_ = self._where_clause(**kwargs)
        sql_statement = "SELECT max(" + column_name + \
            ") FROM " + table + where
        result = self.execute(sql_statement, vars_=vars_)
        if result:
            return result[0][0]  # returns max_price_date
        else:
            return None

    def select_first_price_date_of_prices(self, symbol_list, **kwargs):
        '''
        Selects first price_date of symbols in symbol_list in table PRICES
        for which row exists for all symbols
        skips symbols with no row
        '''
        where, vars_ = self._where_clause(**kwargs)
        if vars_:
            where = where + ' AND '
        else:
            where = ' WHERE '
        price_dates = []
        for symbol in symbol_list:
            symbol = "'" + symbol + "'"
            sql_statement = ' '.join(
                ["SELECT MIN(", DB_price_date, ") FROM ", PRICES, where, DB_symbol, "=", symbol])
            result = self.execute(sql_statement, vars_)
            if result[0][0]:
                # convert datetime to string
                price_dates.append(str(result[0][0])[:10])
        if price_dates:
            return max(price_dates)
        else:
            return None

    def row_exists(self, table, **kwargs):
        '''
        Returns True row exists
        '''

        where, vars_ = self._where_clause(**kwargs)
        sql_statement = "SELECT EXISTS(SELECT * FROM " + table + where + ")"
        result = self.execute(sql_statement, vars_=vars_)
        if result:
            return result[0][0]  # returns 1/0

    def iban_exists(self, table, bank_code, **kwargs):
        '''
        Returns True iban exists
        '''
        clause = ' '.join([DB_iban, "LIKE", "'%" + bank_code + "%')"])
        where, vars_ = self._where_clause(clause=clause, **kwargs)
        sql_statement = ' '.join(
            ["SELECT * FROM ", table, "WHERE EXISTS(SELECT * FROM ", table, where])
        result = self.execute(sql_statement, vars_=vars_)
        if result:
            return True
        else:
            return False

    def select_transactions_data(
            self,
            field_list='price_date, counter, transaction_type, price_currency,\
                          price, pieces, amount_currency, posted_amount, comments',
            **kwargs):
        ''' returns a list of tuples '''
        where, vars_ = self._where_clause(**kwargs)
        if isinstance(field_list, list):
            field_list = ','.join(field_list)
        sql_statement = ("SELECT  " + field_list +
                         " FROM " + TRANSACTION + where)
        sql_statement = sql_statement + " ORDER BY price_date ASC, counter ASC;"
        return self.execute(sql_statement, vars_=vars_)

    def transaction_pieces(self, **kwargs):
        '''
        Returns transaction balance of pieces
        '''
        where, vars_ = self._where_clause(**kwargs)

        sql_statement = ("SELECT  t1.isin_code, t1.name, t1.pieces FROM"
                         " (SELECT t.isin_code, t.name, SUM(t.pieces) AS pieces FROM"
                         " (SELECT isin_code, name, SUM(pieces) AS pieces FROM transaction_view "
                         + where + " AND transaction_type = '" + TRANSACTION_RECEIPT +
                         "' GROUP BY name"
                         " UNION"
                         " SELECT isin_code, name, -SUM(pieces) AS pieces FROM transaction_view "
                         + where + " AND transaction_type = '" + TRANSACTION_DELIVERY +
                         "' GROUP BY name ) AS t  GROUP BY t.isin_code) AS t1 WHERE t1.pieces != 0")
        return self.execute(sql_statement, vars_ + vars_)

    def _transaction_profit_closed_sql(self, where):

        sql_statement = ("SELECT t.isin_code AS isin_code, t. NAME AS name, sum(posted_amount) as profit, amount_currency, sum(pieces) FROM \
                         (\
                         (SELECT  isin_code, NAME, price_date, counter, transaction_type, price, sum(pieces) AS pieces, \
                          sum(posted_amount) AS posted_amount, amount_currency FROM " + TRANSACTION_VIEW + where +
                         " AND transaction_type='" + TRANSACTION_DELIVERY +
                         "' GROUP BY isin_code ORDER  by price_date ASC, counter ASC) \
                         UNION \
                         (SELECT  isin_code, NAME, price_date, counter, transaction_type, price, -sum(pieces) AS pieces, \
                         -sum(posted_amount)AS posted_amount, amount_currency  FROM " + TRANSACTION_VIEW + where +
                         " AND transaction_type='" + TRANSACTION_RECEIPT +
                         "' GROUP BY isin_code ORDER  by price_date ASC, counter ASC)\
                         ) \
                         AS t GROUP BY t.isin_code HAVING sum(pieces) = 0")
        return sql_statement

    def transaction_profit_closed(self, **kwargs):
        '''
        Returns profit of closed stocks
        '''
        where, vars_ = self._where_clause(**kwargs)
        sql_statement = self._transaction_profit_closed_sql(where)
        return self.execute(sql_statement, vars_ + vars_)

    def _transaction_profit_portfolio_sql(self, where, max_price_date):

        sql_statement = ("SELECT isin_code, name, total_amount AS profit, \
                         amount_currency AS currency, pieces FROM " + HOLDING_VIEW +
                         + where + " AND price_date='" + str(max_price_date) +
                         "' GROUP BY isin_code ")
        return sql_statement

    def transaction_profit_all(self, **kwargs):
        '''
        Returns profit all transactions inclusive portfolio values
        '''
        where, vars_ = self._where_clause(**kwargs)
        max_price_date = self.select_max_column_value(
            HOLDING, DB_price_date, **kwargs)
        if max_price_date is None:
            return None
        else:
            sql_statement = (self._transaction_profit_closed_sql(where) +
                             " UNION  "
                             " SELECT isin_code, name, (total_amount - acquisition_amount) AS profit,"
                             " amount_currency AS currency, pieces FROM holding_view "
                             + where + " AND price_date='" + str(max_price_date) +
                             "' GROUP BY isin_code ")
        return self.execute(sql_statement, vars_ + vars_ + vars_)

    def transaction_portfolio(self, **kwargs):
        '''
        Returns comparison between Portfolio and stored Transactions
        '''
        where, vars_ = self._where_clause(**kwargs)
        max_price_date = self.select_max_column_value(
            HOLDING, DB_price_date, **kwargs)
        if max_price_date is None:
            return None
        else:
            result_transaction = self.transaction_pieces(**kwargs)
            sql_statement = ("SELECT isin_code, NAME, pieces FROM holding_view" + where +
                             " AND price_date='" + str(max_price_date) + "'")
            result_portfolio = self.execute(sql_statement, vars_)
            result = []
            for item in set(result_transaction).symmetric_difference(set(result_portfolio)):
                if item in result_portfolio:
                    result.append(('PORTFOLIO',) + item)
                else:
                    result.append(('TRANSACTION',) + item)
            return result

    def update_holding_acquisition(self, iban, isin, HoldingAcquisition, period=None, mode=None):

        if HoldingAcquisition.origin == ORIGIN:
            sql_statement = ("UPDATE " + HOLDING +
                             " SET acquisition_amount=? WHERE iban=? AND isin_code=?")
            vars_ = (HoldingAcquisition.acquisition_amount, iban, isin,
                     HoldingAcquisition.price_date)
        else:
            sql_statement = ("UPDATE " + HOLDING + " SET acquisition_price=?, "
                             " acquisition_amount=? WHERE iban=? AND isin_code=?")
            vars_ = (HoldingAcquisition.acquisition_price, HoldingAcquisition.acquisition_amount,
                     iban, isin, HoldingAcquisition.price_date)
        if mode is None:
            sql_statement = sql_statement + " AND price_date=?"
        else:
            if period is None:
                sql_statement = sql_statement + " AND price_date>=?"
            else:
                _, to_date = period
                vars_ = vars_ + (to_date,)
                sql_statement = sql_statement + " AND price_date>=? AND price_date<=?"
        self.execute(sql_statement, vars_=vars_)

    def update_prices_histclose(self, name, symbol, adjustments):

        adjustments = loads(adjustments)
        for to_date, adjustment in adjustments.items():
            r_factor, used = adjustment
            if used == FALSE:  # histclose not yet calculated
                # calculate histclose
                sql_statement = "UPDATE " + PRICES + \
                    " SET histclose = close / " + r_factor + " WHERE symbol=? AND price_date<=?"
                vars_ = (symbol, to_date)
                self.execute(sql_statement, vars_=vars_)
                # histclose calculated > set used
                adjustments[to_date] = (r_factor, True)

        sql_statement = "UPDATE " + PRICES + \
            " SET histclose=close WHERE symbol=? AND histclose=0"
        vars_ = (symbol)
        self.execute(sql_statement, vars_=vars_)

        adjustments[to_date] = (r_factor, TRUE)
        sql_statement = "UPDATE " + ISIN + " SET adjustments=?  WHERE name=?"
        vars_ = (dumps(adjustments), name)
        self.execute(sql_statement, vars_=vars_)

    def update_total_holding_amount(self, **kwargs):

        where, vars_ = self._where_clause(**kwargs)
        sql_statement = ("select iban, price_date, sum(total_amount) from "
                         + HOLDING + where + " group by price_date")
        result = self.execute(sql_statement, vars_=vars_)
        for row in result:
            iban, price_date, total_amount_portfolio = row
            sql_statement = ("UPDATE " + HOLDING + " SET total_amount_portfolio=? "
                             "where iban=? and price_date=?")
            vars_ = (total_amount_portfolio, iban, price_date)
            self.execute(sql_statement, vars_=vars_)
