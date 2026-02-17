"""
Created on 26.11.2019
__updated__ = "2026-02-15"
@author: Wolfgang Kramer
"""
import sqlalchemy
import json
import re


from decimal import Decimal
from collections.abc import Sequence
from pandas import DataFrame
from inspect import stack
from typing import NamedTuple, Iterable, List, Tuple, Any, Dict, Optional, Union
from mariadb import connect, Error
from itertools import chain
from datetime import date
from collections import namedtuple
from fints.types import ValueList
from banking.declarations_mariadb import (
    TABLE_NAMES, TABLE_FIELDS, TABLE_FIELDS_PROPERTIES, DATABASE_FIELDS_PROPERTIES,
    FieldsProperty, DB_account, DB_amount, DB_bankdata, DB_code, DB_data, DB_id_no,
    DB_iban, DB_entry_date, DB_ledger, DB_name, DB_counter, DB_price_date, DB_ISIN,
    DB_purpose_wo_identifier, DB_purpose, DB_row_id, DB_total_amount, DB_acquisition_amount,
    DB_status, DB_symbol, PRODUCTIVE_DATABASE_NAME, APPLICATION, BANKIDENTIFIER,
    DB_balance, LEDGER_DAILY_BALANCE,
    CREATE_TABLES, HOLDING, ISIN, PRICES, LEDGER, LEDGER_VIEW, LEDGER_COA, LEDGER_STATEMENT,
    SELECTION, SERVER, STATEMENT, SHELVES, TRANSACTION, TRANSACTION_VIEW, DB_credit_account,
    DB_debit_account, DB_bank_reference, DB_closing_balance, DB_closing_status,
    DB_close
    )
from banking.declarations import (
    KEY_ACC_OWNER_NAME, KEY_ACC_ALLOWED_TRANSACTIONS, INFORMATION,
    CREDIT, DEBIT, HoldingAcquisition, ERROR, FN_PROFIT_LOSS,
    COST_LIFO, COST_FIFO, COST_AVERAGE,
    KEY_ACCOUNTS, KEY_ACC_IBAN, KEY_ACC_ACCOUNT_NUMBER,
    KEY_ACC_PRODUCT_NAME, KEY_BANK_NAME, NOT_ASSIGNED,
    ORIGIN, PERCENT, SCRAPER_BANKDATA, START_DATE_STATEMENTS, TRANSACTION_RECEIPT,
    TRANSACTION_DELIVERY, WARNING, START_DIALOG_FAILED
    )
from banking.declarations import TYP_ALPHANUMERIC, TYP_DECIMAL, TYP_DATE, WM_DELETE_WINDOW
from banking.message_handler import (
    get_message,
    MESSAGE_TEXT,
    Informations, bankdata_informations_append,
    MessageBoxError, MessageBoxInfo
    )
from banking.ledger import transfer_statement_to_ledger
from banking.utils import (
    application_store, dec2,
    date_days, date_yyyymmdd, Termination,
    )
from banking.declarations_mariadb import (
    HOLDING_VIEW, DB_closing_entry_date,
    DB_asset_accounting
    )
from banking.trading_calendar import xetra_cls, xetra_bday

NAMED_PARAM_RE = re.compile(r":([a-zA-Z_][a-zA-Z0-9_]*)")


class MariaDBConnection:

    def __init__(self, user, password, database, host="localhost"):

        self.user = user
        self.password = password
        self.database = database.lower()
        self.host = host
        self.conn = None
        self.cursor = None
        self.engine = None

    def connect(self):
        """
        Connects user to database.
        Creates an empty database if it does not exist.
        """
        # 1. Admin-Verbindung (ohne DB)
        with connect(
            host=self.host,
            user=self.user,
            password=self.password
        ) as admin_conn:

            admin_cur = admin_conn.cursor()

            # 2. Existenz prüfen
            admin_cur.execute(
                "SELECT SCHEMA_NAME FROM information_schema.SCHEMATA "
                "WHERE SCHEMA_NAME = ?",
                (self.database,)
            )

            exists = admin_cur.fetchone() is not None

            # 3. Falls nicht vorhanden → leere DB anlegen
            if not exists:
                admin_cur.execute(
                    f"CREATE DATABASE {self.database} "
                )

        # 4. Jetzt mit der (neuen oder bestehenden) DB verbinden
        self._connect_to_database()

    def _connect_to_database(self):

        self._create_engine()

        self.conn = connect(
            host=self.host,
            user=self.user,
            password=self.password,
            database=self.database
        )

        self.conn.autocommit = True
        self.cursor = self.conn.cursor()
        self.cursor.execute("SELECT DATABASE()")

    def _create_engine(self):

        credentials = ''.join(
            [self.user, ":", self.password, "@", self.host, "/", self.database])
        self.engine = sqlalchemy.create_engine("mariadb+mariadbconnector://" + credentials)

    def close(self):
        if self.conn and self.conn.is_connected():
            self.cursor.close()
            self.conn.close()


class MariaDBExecutor:
    """
    Centralized SQL execution layer.
    GUI independent.
    """

    SELECT_RE = re.compile(r'^\s*(SELECT|WITH)\b', re.I)
    MODIFY_RE = re.compile(r'^\s*(INSERT|UPDATE|DELETE|REPLACE)\b', re.I)

    def __init__(self, db: 'MariaDB'):
        self._db = db
        self._cursor = db.cursor
        self._conn = db.conn

    def execute(
        self,
        sql: str,
        vars_: tuple | None = None,
        *,
        duplicate: bool = False,
        result_dict: bool = False,
        compress: bool = False
    ):
        """
        Execute SQL statement.

        Parameters:
            sql_statement: SQL string
            vars_: bind parameters
            duplicate: ignore duplicate key error (1062)
            result_dict: return list of dicts instead of tuples
            compress: normalize whitespace in SQL

        Returns:
            SELECT/WITH   -> list[tuple] | list[dict]
            INSERT/UPDATE/DELETE/REPLACE -> affected row count
            otherwise    -> None
        """
        sql = self._prepare_sql(sql, compress)

        try:
            # print(sql, vars_)
            self._execute(sql, vars_)

            if self._is_select(sql):
                return self._fetch(result_dict)

            if self._is_modify(sql):
                return self._row_count()

            return None

        except Exception as exc:
            # Executor does NOT decide how to display errors
            exc.statement = sql
            exc.params = vars_
            raise

    # ---------- helpers ----------

    def _prepare_sql(self, sql: str, compress: bool) -> str:
        if not compress:
            return sql
        return re.sub(r'\s+', ' ', sql.replace('\n', ' ')).strip()

    def _execute(self, sql: str, params):
        if params:
            self._cursor.execute(sql, params)
        else:
            self._cursor.execute(sql)

    def _is_select(self, sql: str) -> bool:
        return bool(self.SELECT_RE.match(sql))

    def _is_modify(self, sql: str) -> bool:
        return bool(self.MODIFY_RE.match(sql))

    def _fetch(self, result_dict: bool):
        rows = self._cursor.fetchall()
        if not result_dict:
            return rows
        columns = [c[0] for c in self._cursor.description]
        return [dict(zip(columns, row)) for row in rows]

    def _row_count(self) -> int:
        self._cursor.execute('SELECT ROW_COUNT()')
        return self._cursor.fetchone()[0]


class DatabaseErrorHandler:
    """
    Handles database-related errors and user-facing error messages.
    Fully compatible with legacy MariaDB.execute() error handling.
    """

    @staticmethod
    def handle_error(
        title: str,
        storage,
        exc: Exception,
        *,
        sql: str | None = None,
        params=None,
        duplicate: bool = False
    ):
        messages: list[str] = []

        # --- Base SQL error message -------------------------------------
        if sql is not None:
            messages.append(
                get_message(
                    MESSAGE_TEXT,
                    'MARIADB_ERROR_SQL',
                    sql,
                    params
                )
            )

        # --- DB error details (errno / errmsg) --------------------------
        errno = getattr(exc, 'errno', None)
        errmsg = getattr(exc, 'errmsg', None)

        if errno is not None and errmsg is not None:
            messages.append(
                get_message(
                    MESSAGE_TEXT,
                    'MARIADB_ERROR',
                    errno,
                    errmsg
                )
            )

        # --- Duplicate key handling ------------------------------------
        if duplicate and errno == 1062:
            MessageBoxInfo(
                title=title,
                info_storage=storage,
                information=ERROR,
                message="\n\n".join(messages)
            )
            return errno

        # --- LOAD statement handling -----------------------------------
        if sql and sql.upper().startswith('LOAD'):
            MessageBoxInfo(
                title=title,
                info_storage=storage,
                information=ERROR,
                message="\n\n".join(messages)
            )
            return False

        # --- Stack trace (legacy behavior) -----------------------------
        try:
            frame = stack()[2]
            filename = frame.filename
            line = frame.lineno
            method = frame.function

            messages.append(
                get_message(
                    MESSAGE_TEXT,
                    'STACK',
                    line,
                    filename,
                    method
                )
            )
        except Exception:
            pass

        # --- Fatal error ------------------------------------------------
        MessageBoxError(
            title=title,
            info_storage=storage,
            message="\n\n".join(messages)
        )
        return False


class MariaDBConfig(NamedTuple):
    user: str
    password: str
    database: str
    host: str


class MariaDBContext:
    """
    Application context for MariaDB.

    Responsible for:
    - Managing the database connection
    - Exposing conn, cursor and engine
    - Creating the SQL executor
    """

    def __init__(self, user, password, database, host):
        self.connection = MariaDBConnection(
            user=user,
            password=password,
            database=database,
            host=host
            )
        self.connection.connect()

        # Public DB handles
        self.conn = self.connection.conn
        self.cursor = self.connection.cursor
        self.engine = self.connection.engine
        self.config = MariaDBConfig(
            user=user,
            password=password,
            database=database.lower(),
            host=host
            )


class MariaDBInitializer:
    """
    Basic Class
    This class is responsible for:
    - Creating and initializing the database
    - Creating tables and views
    - Managing connections and cursors
    - Collecting table and column metadata
    """

    def __init__(self, user: str = 'root',
                 password: str = 'FINTS',
                 database: str = PRODUCTIVE_DATABASE_NAME,
                 host='localhost'):
        """
        Initialize the MariaDB singleton.
        Contains only domain-level initialization.
        """

        if hasattr(self, '_initialized'):
            return
        self._initialized = True

        # --- Context / infrastructure ---------------------------------------
        self.context = MariaDBContext(
            user=user,
            password=password,
            database=database,
            host=host
        )

        # Backward compatibility
        self.conn = self.context.conn
        self.cursor = self.context.cursor
        self.engine = self.context.engine
        # Explicit backward compatibility / public API
        self.user = self.context.config.user
        self.password = self.context.config.password
        self.database = self.context.config.database
        self.host = self.context.config.host
        # --- Domain initialization ------------------------------------------
        self.executor = MariaDBExecutor(self)
        self.table_names: list[str] = []

        self._initialize_database()
        self._init_database_info()

    def _initialize_database(self) -> None:
        """Create database, connect, and initialize tables/views."""
        try:
            self._create_database_if_missing()
            self._create_tables_and_views()
        except Error as exc:
            DatabaseErrorHandler.handle_error(self.database, Informations.BANKDATA_INFORMATIONS, exc)

    def _create_database_if_missing(self) -> None:
        """Create the database if it does not yet exist."""
        with connect(
            host=self.host,
            user=self.user,
            password=self.password,
        ) as conn:
            cur = conn.cursor()
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS {self.database.upper()} "
            )
            cur.execute("SHOW DATABASES")

            for (db_name,) in cur:
                if db_name not in {
                    "information_schema",
                    "mysql",
                    "performance_schema",
                }:
                    self.DATABASES.append(db_name)

    def _create_tables_and_views(self) -> None:
        """Create tables and update views if necessary."""
        for statement in CREATE_TABLES:
            self.cursor.execute(statement)
            if statement.startswith('CREATE ALGORITHM'):
                alter_stmt = statement.replace('CREATE ALGORITHM', 'ALTER ALGORITHM').replace('IF NOT EXISTS', '')
                self.cursor.execute(alter_stmt)

    def _create_engine(self):
        """Create and return a SQLAlchemy engine."""
        credentials = (
            f'{self.user}:{self.password}@{self.host}/{self.database}')
        try:
            return sqlalchemy.create_engine(
                f'mariadb+mariadbconnector://{credentials}')
        except sqlalchemy.exc.SQLAlchemyError as exc:
            DatabaseErrorHandler.handle_error(self.database, Informations.PRICES_INFORMATIONS, exc)
            return None

    def _init_database_info(self) -> None:
        """
        Initialize table and column metadata structures.

        Populates:
        - TABLE_NAMES
        - TABLE_FIELDS
        - TABLE_FIELDS_PROPERTIES
        - DATABASE_FIELDS_PROPERTIES
        """
        self._load_table_names()
        self._load_column_metadata()

    def _load_table_names(self) -> None:
        """Load all table names from the current schema."""
        sql = (
            'SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE();'
            )
        self.table_names = list(chain(*self.executor.execute(sql)))
        TABLE_NAMES[:] = self.table_names

    def _load_column_metadata(self) -> None:
        """Load column properties for all tables."""
        columns = [
            'column_name',
            'character_maximum_length',
            'numeric_scale',
            'numeric_precision',
            'data_type',
            'column_comment'
            ]
        Column = namedtuple('Column', columns)
        for table in self.table_names:
            sql = (
                f"SELECT {','.join(columns)} FROM information_schema.columns WHERE table_schema = DATABASE() AND table_name = '{table}' ORDER BY ordinal_position;"
                )
            result = self.executor.execute(sql)
            field_properties = {}
            for row in result:
                column = Column(*row)
                field_properties[column.column_name] = self._build_field_property(column)
            TABLE_FIELDS[table] = list(field_properties.keys())
            TABLE_FIELDS_PROPERTIES[table] = field_properties
            DATABASE_FIELDS_PROPERTIES.update(field_properties)

    def _build_field_property(self, column):
        """Create a FieldsProperty instance for a column."""
        if column.data_type == 'decimal':
            typ = TYP_DECIMAL
        elif column.data_type == 'date':
            typ = TYP_DATE
        else:
            typ = TYP_ALPHANUMERIC
        length = (
            column.character_maximum_length
            or column.numeric_precision
            or 30
            )
        scale = column.numeric_scale or 0
        return FieldsProperty(length, scale, typ, column.column_comment, column.data_type)

    def _handle_sql_error(self, error: Error) -> None:
        """Format and display SQL errors with stack context."""
        message = get_message(
            MESSAGE_TEXT,
            'MARIADB_ERROR',
            error.errno,
            error.errmsg
            )
        filename, line, method = stack()[1][1:4]
        message = '\n\n'.join(
            [
                message,
                get_message(
                    MESSAGE_TEXT,
                    'STACK',
                    method,
                    line,
                    filename
                    )
                ]
            )
        MessageBoxInfo(message=message)

    def destroy_connection(self):
        """
        close connection >database<
        """
        if self.conn.is_connected():
            self.conn.close()
            self.cursor.close()


class MariaDBTables:
    # ------------------------------------------------------------------
    # Core QueryBuilder helpers
    # ------------------------------------------------------------------
    def _order_clause(self, order=None, sort: str = 'ASC') -> str:
        """Build ORDER BY clause"""
        if not order:
            return ''

        sort = sort.upper()

        if isinstance(order, list) and isinstance(order[0], str):
            clause = ', '.join(f"{o} {sort}" for o in order)
        elif isinstance(order, tuple):
            clause = f"{order[0]} {order[1]}"
        elif isinstance(order, list) and isinstance(order[0], tuple):
            clause = ', '.join(f"{o[0]} {o[1]}" for o in order)
        else:
            clause = f"{order} {sort}"

        return f" ORDER BY {clause} "

    def _where_clause(
        self,
        *,
        clause: str | None = None,
        clause_vars: Sequence[Any] = (),
        date_name: str | None = None,
        **kwargs
    ) -> tuple[str, tuple[Any, ...]]:
        """
        Build WHERE clause and bind variables.

        Returns:
            (sql, vars)
        """
        sql_parts: list[str] = []
        vars_: list[Any] = []

        for key, value in kwargs.items():
            if isinstance(value, date):
                value = date_days.convert_to_str(value)
            if key == "period":
                from_date, to_date = map(date_days.convert_to_str, value)
                field = date_name or DB_price_date
                sql_parts.append(f"{field} BETWEEN ? AND ?")
                vars_.extend((from_date, to_date))
            elif isinstance(value, (list, tuple)):
                placeholders = ", ".join("?" for _ in value)
                sql_parts.append(f"{key} IN ({placeholders})")
                vars_.extend(value)
            else:
                sql_parts.append(f"{key} = ?")
                vars_.append(value)

        if clause:
            sql_parts.append(f"({clause})")
            vars_.extend(clause_vars)

        if not sql_parts:
            return "", ()

        return "WHERE " + " AND ".join(sql_parts) + " ", tuple(vars_)

    def _normalize_fields(
        self,
        fields: str | Iterable[str]
    ) -> str:
        """
        Normalize the field list to a SQL-compatible string.
        """

        if isinstance(fields, (list, tuple, set)):
            return ', '.join(fields)

        return fields

    def _normalize_vars(self, vars_):
        """
        Normalize SQL variables to a tuple.

        Accepts:
        - tuple
        - list
        - dict (values only, ordered)
        - None

        Returns
        -------
        tuple
        """
        if vars_ is None:
            return ()
        if isinstance(vars_, tuple):
            return vars_
        if isinstance(vars_, list):
            return tuple(vars_)
        if isinstance(vars_, dict):
            return tuple(vars_.values())
        raise TypeError(f"Unsupported vars type: {type(vars_)}")

    def _normalize_named_sql(self, sql: str, vars_: dict):
        """
        Replace :named parameters with ? placeholders
        and return ordered tuple of bind variables.
        """
        if not vars_:
            return sql, ()

        order = []

        def repl(match):
            key = match.group(1)
            if key not in vars_:
                raise KeyError(f"Missing SQL bind parameter: {key}")
            order.append(key)
            return "?"

        sql = NAMED_PARAM_RE.sub(repl, sql)
        values = tuple(vars_[k] for k in order)
        return sql, values

    # ------------------------------------------------------------------
    # Generic SELECT methods
    # ------------------------------------------------------------------
    def _select(
        self,
        *,
        table: str,
        fields: str | list[str] | tuple[str, ...],
        distinct: bool = False,
        clause: str | None = None,
        clause_vars: tuple = (),
        date_name: str | None = None,
        order: str | list[str] | tuple | list[tuple] | None = None,
        sort: str = "ASC",
        group_by: str | list[str] | None = None,
        having: str | None = None,
        having_vars: tuple = (),
        limit: int | None = None,
        result_dict: bool = False,
        **kwargs
    ) -> list:
        """
        Build and execute a unified SQL SELECT statement.

        This internal helper constructs a SELECT query supporting DISTINCT,
        WHERE filtering, GROUP BY, HAVING, ORDER BY, and LIMIT clauses.
        All SQL execution is delegated to the configured database executor.

        Parameters
        ----------
        table : str
            Name of the database table or view.
        fields : str | list[str] | tuple[str, ...]
            Fields to select. May be a comma-separated string or an iterable
            of column names.
        distinct : bool, optional
            If True, generate a SELECT DISTINCT statement.
        clause : str | None, optional
            Additional raw SQL WHERE clause fragment. This fragment may
            contain positional placeholders (`?`) which must be bound via
            `clause_vars`.
        date_name : str | None, optional
            Overrides the default date column used for period-based filters.
        order : str | list[str] | None, optional
            Column or columns used for ORDER BY.
            Tuple or list of tuples used for ORDER BY e.g. [(column, 'ASC'), ...]
        sort : str, optional
            Sort direction for ORDER BY. Must be 'ASC' or 'DESC'.
            Not used if order are tuple o list of tuples
        group_by : str | list[str] | None, optional
            Column or columns used for GROUP BY.
        having : str | None, optional
            SQL HAVING clause applied after GROUP BY. May contain positional
            placeholders (`?`) which must be bound via `having_vars`.
        limit : int | None, optional
            Maximum number of rows to return.
        result_dict : bool, optional
            If True, return rows as dictionaries.
            If False, return rows as tuples.
        clause_vars : tuple, optional
            Positional bind variables for placeholders defined in `clause`.
        having_vars : tuple, optional
            Positional bind variables for placeholders defined in `having`.
        **kwargs
            Column-value filters passed to `_where_clause()`.

        Returns
        -------
        list
            Query result rows. Each row is returned either as a tuple or
            as a dictionary depending on `result_dict`.
        """

        if not fields:
            return []

        # ------------------------------------------------------------
        # Normalize SELECT fields
        # ------------------------------------------------------------
        fields = self._normalize_fields(fields)

        # ------------------------------------------------------------
        # Base SELECT clause
        # ------------------------------------------------------------
        select_kw = "SELECT DISTINCT" if distinct else "SELECT"
        sql = f"{select_kw} {fields} FROM {table} "

        # ------------------------------------------------------------
        # WHERE clause and bind variables
        # ------------------------------------------------------------
        where_sql, vars_ = self._where_clause(
            clause=clause,
            clause_vars=clause_vars,
            date_name=date_name,
            **kwargs
        )
        sql += where_sql

        # ------------------------------------------------------------
        # GROUP BY clause
        # ------------------------------------------------------------
        if group_by:
            group_sql = (
                ", ".join(group_by)
                if isinstance(group_by, (list, tuple))
                else group_by
            )
            sql += f" GROUP BY {group_sql} "

        # ------------------------------------------------------------
        # HAVING clause
        # ------------------------------------------------------------
        if having:
            sql += f" HAVING {having} "
            vars_ += having_vars

        # ------------------------------------------------------------
        # ORDER BY clause
        # ------------------------------------------------------------
        if order:
            sql += self._order_clause(order=order, sort=sort)

        # ------------------------------------------------------------
        # LIMIT clause
        # ------------------------------------------------------------
        if limit is not None:
            sql += f" LIMIT {limit} "

        # ------------------------------------------------------------
        # Execute query
        # ------------------------------------------------------------
        return self.executor.execute(
            sql,
            vars_=vars_,
            result_dict=result_dict
        )

    def _select_scalar(
        self,
        *,
        table: str,
        expression: str,
        clause: str | None = None,
        clause_vars: tuple = (),
        date_name: str | None = None,
        default=None,
        **kwargs
    ):
        """
        Execute a SELECT query that returns a single scalar value.

        This helper is intended for aggregate queries such as COUNT, SUM,
        MIN, MAX, or any SQL expression that yields exactly one value.

        Parameters
        ----------
        table : str
            Name of the database table or view.
        expression : str
            SQL expression to select (e.g. 'COUNT(*)', 'SUM(amount)',
            'MAX(created_at)').
        clause : str | None, optional
            Additional raw SQL WHERE clause fragment.
        date_name : str | None, optional
            Overrides the default date column used for period-based filters.
        default : Any, optional
            Value returned if the query yields no result or NULL.
        **kwargs
            Column-value filters passed to `_where_clause()`.

        Returns
        -------
        Any
            The scalar result value, or `default` if no row was returned.
        """

        rows = self._select(
            table=table,
            fields=expression,
            clause=clause,
            clause_vars=clause_vars,
            date_name=date_name,
            limit=1,
            **kwargs
        )

        if not rows:
            return default

        value = rows[0][0]
        return default if value is None else value

    def _select_exists(
        self,
        *,
        table: str,
        clause: str | None = None,
        clause_vars: tuple = (),
        date_name: str | None = None,
        **kwargs
    ) -> bool:
        """
        Check whether at least one row exists for the given conditions.

        Parameters
        ----------
        table : str
            Table or view name.
        clause : str | None, optional
            Additional SQL WHERE clause fragment.
        date_name : str | None, optional
            Overrides the default date column for period filters.
        **kwargs
            WHERE filters passed to `_where_clause()`.

        Returns
        -------
        bool
            True if at least one matching row exists, otherwise False.
        """

        rows = self._select(
            table=table,
            fields="1",
            clause=clause,
            clause_vars=clause_vars,
            date_name=date_name,
            limit=1,
            **kwargs
        )

        return bool(rows)

    def _select_cte(
        self,
        *,
        sql: str,
        fields: str | Iterable[str],
        vars_: dict | tuple | None = None,
        result_dict: bool = False,
    ) -> list:
        """
        Execute a CTE-based SELECT statement.

        Parameters
        ----------
        sql : str
            Inner SELECT or CTE SQL statement.
            May contain positional ('?') or named (':name') placeholders.
        fields : str | Iterable[str]
            Fields to select from the CTE result.
        vars_ : dict | tuple | None, optional
            Bind parameters for the SQL statement.
            - dict: named parameters
            - tuple/list: positional parameters
        result_dict : bool, optional
            If True, return rows as dictionaries.

        Returns
        -------
        list
            Query result rows as tuples or dictionaries.
        """
        if not fields:
            fields = '*'
        if isinstance(vars_, dict):
            sql, vars_ = self._normalize_named_sql(sql, vars_)
        else:
            vars_ = self._normalize_vars(vars_)

        fields_sql = self._normalize_fields(fields)

        final_sql = f"""
            SELECT {fields_sql}
            FROM (
                {sql}
            ) AS cte
        """
        return self.executor.execute(
            final_sql,
            vars_=vars_,
            result_dict=result_dict,
            compress=True
        )

    def select_table(
        self,
        table: str,
        field_list,
        *,
        order=None,
        sort: str = "ASC",
        result_dict: bool = False,
        date_name: str | None = None,
        **kwargs
    ):
        """Select rows from a table."""
        return self._select(
            table=table,
            fields=field_list,
            order=order,
            sort=sort,
            date_name=date_name,
            result_dict=result_dict,
            **kwargs
        )

    def select_table_distinct(
        self,
        table: str,
        field_list,
        *,
        order=None,
        clause=None,
        clause_vars: tuple = (),
        result_dict: bool = False,
        date_name: str | None = None,
        **kwargs
    ):
        """Select distinct rows from a table."""
        return self._select(
            table=table,
            fields=field_list,
            distinct=True,
            clause=clause,
            clause_vars=clause_vars,
            order=order,
            date_name=date_name,
            result_dict=result_dict,
            **kwargs
        )

    def select_first_row(
        self,
        table: str,
        fields: str | list[str] | tuple[str, ...],
        *,
        clause: str | None = None,
        clause_vars: tuple = (),
        date_name: str | None = None,
        order: str | list[str] | None = None,
        result_dict: bool = False,
        **kwargs
    ) -> str | list:
        """Select first row based on ordering."""
        rows = self._select(
            table=table,
            fields=fields,
            clause=clause,
            clause_vars=clause_vars,
            order=order,
            date_name=date_name,
            sort="ASC",
            limit=1,
            result_dict=result_dict,
            **kwargs
        )
        if isinstance(fields, str):
            if fields == '*':
                return rows[0] if rows else None  # returns list or dict
            else:
                return rows[0] if rows[0][0] else None  # returns scalar
        else:
            return rows[0] if rows else None

    def select_last_row(
        self,
        table: str,
        fields: str | list[str] | tuple[str, ...],
        *,
        clause: str | None = None,
        clause_vars: tuple = (),
        date_name: str | None = None,
        order: str | list[str] | None = None,
        result_dict: bool = False,
        **kwargs
    ) -> str | list:
        """Select last row based on ordering."""
        rows = self._select(
            table=table,
            fields=fields,
            clause=clause,
            clause_vars=clause_vars,
            order=order,
            date_name=date_name,
            sort="DESC",
            limit=1,
            result_dict=result_dict,
            **kwargs
        )
        if isinstance(fields, str):
            if fields == '*':
                return rows[0] if rows else None  # returns list or dict
            else:
                return rows[0] if rows[0][0] else None  # returns scalar
        else:
            return rows[0] if rows else None

    def select_grouped(
        self,
        table: str,
        fields,
        *,
        group_by,
        having: str | None = None,
        date_name: str | None = None,
        **kwargs
    ):
        """
        Select grouped rows with optional HAVING conditions.
        """

        return self._select(
            table=table,
            fields=fields,
            group_by=group_by,
            having=having,
            date_name=date_name,
            **kwargs
        )

    def select_dict(
        self,
        table: str,
        key_name: str,
        value_name: str,
        *,
        order: str | None = None,
        clause: str | None = None,
        clause_vars: tuple = (),
        **kwargs
    ) -> dict:
        """
        Return a dictionary mapping keys to values from a table.

        Parameters
        ----------
        table : str
            Table or view name.
        key_name : str
            Column used as dictionary key.
        value_name : str
            Column used as dictionary value.
        order : str | list[str], optional
            ORDER BY column(s).
        **kwargs
            WHERE filters passed to `_where_clause()`.

        Returns
        -------
        dict
            Dictionary mapping key_name -> value_name.
            Returns an empty dict if no rows match.
        """

        rows = self._select(
            table=table,
            fields=[key_name, value_name],
            order=order,
            clause=clause,
            clause_vars=clause_vars,
            **kwargs
        )

        return dict(rows) if rows else {}

    def select_rows(
        self,
        *,
        table: str,
        fields,
        distinct: bool = False,
        clause: str | None = None,
        date_name: str | None = None,
        order: str | list[str] | None = None,
        sort: str = "ASC",
        group_by: str | list[str] | None = None,
        having: str | None = None,
        limit: int | None = None,
        result_dict: bool = False,
        **kwargs
    ) -> list:
        """
        Select rows from a table.

        This is the primary public entry point for row-based SELECT queries.
        """

        return self._select(
            table=table,
            fields=fields,
            distinct=distinct,
            clause=clause,
            date_name=date_name,
            order=order,
            sort=sort,
            group_by=group_by,
            having=having,
            limit=limit,
            result_dict=result_dict,
            **kwargs
        )

    def select_scalar(
        self,
        table: str,
        expression: str,
        *,
        clause: str | None = None,
        clause_vars: tuple = (),
        date_name: str | None = None,
        default=None,
        **kwargs
    ):
        """
        Execute a SELECT query returning a single scalar value.
        """

        return self._select_scalar(
            table=table,
            expression=expression,
            clause=clause,
            clause_vars=clause_vars,
            date_name=date_name,
            default=default,
            **kwargs
        )

    def select_exists(
        self,
        table: str,
        *,
        clause: str | None = None,
        date_name: str | None = None,
        **kwargs
    ) -> bool:
        """
        Return True if at least one matching row exists.
        """

        return self._select_exists(
            table=table,
            clause=clause,
            date_name=date_name,
            **kwargs
        )

    def select_cte(
        self,
        *,
        sql: str,
        fields: str | Iterable[str],
        vars_: dict | tuple | None = None,
        result_dict: bool = False,
    ) -> list:
        """
        Execute a SELECT statement based on a Common Table Expression (CTE).

        This method wraps an arbitrary SELECT or CTE SQL statement and applies
        a unified result projection and execution strategy. It supports both
        positional and named SQL parameters and returns the result either as
        tuples or dictionaries.

        Parameters
        ----------
        sql : str
            Inner SELECT or CTE SQL statement.
            May contain positional ('?') or named (':name') placeholders.
        fields : str | Iterable[str]
            Fields to select from the CTE result.
            Must not be empty.
        vars_ : dict | tuple | None, optional
            Bind parameters for the SQL statement.
            - dict: named parameters
            - tuple/list: positional parameters
            - None: no bind parameters
        result_dict : bool, optional
            If True, rows are returned as dictionaries.
            If False, rows are returned as tuples.

        Returns
        -------
        list
            Query result rows.
            Returns an empty list if `fields` is empty.
        """

        # ------------------------------------------------------------
        # Guard clause – consistent with other select_* methods
        # ------------------------------------------------------------
        if not fields:
            return []

        return self._select_cte(
            sql=sql,
            fields=fields,
            vars_=vars_,
            result_dict=result_dict,
        )

    def iban_exists(self, table: str, bank_code: str, **kwargs) -> bool:
        """
        Check whether at least one IBAN containing the given bank code exists.

        Parameters
        ----------
        table : str
            Table or view name.
        bank_code : str
            Bank code fragment to search for within the IBAN.
        **kwargs
            Additional WHERE filters passed to `_where_clause()`.

        Returns
        -------
        bool
            True if at least one matching IBAN exists, otherwise False.
        """
        return self.select_exists(
            table=table,
            clause=f"{DB_iban} LIKE ?",
            clause_vars=(f"%{bank_code}%",),
            **kwargs
        )
    # ------------------------------------------------------------------
    # INSERT / UPDATE / DELETE / REPLACE
    # ------------------------------------------------------------------

    def execute(self, *args, **kwargs):

        def _normalize_execute_args(args, kwargs):
            """
            Normalize positional and keyword arguments of execute()
            into explicit named values.
            """
            sql = args[0] if len(args) > 0 else kwargs.get("sql")
            params = args[1] if len(args) > 1 else kwargs.get("vars_")

            duplicate = kwargs.get("duplicate", False)
            result_dict = kwargs.get("result_dict", False)
            compress = kwargs.get("compress", False)

            return {
                "sql": sql,
                "params": params,
                "duplicate": duplicate,
                "result_dict": result_dict,
                "compress": compress,
            }

        exec_args = _normalize_execute_args(args, kwargs)

        try:
            return self.executor.execute(*args, **kwargs)

        except Exception as exc:
            return DatabaseErrorHandler.handle_error(
                title="Database error",
                storage=self,
                exc=exc,
                sql=exec_args["sql"],
                params=exec_args["params"],
                duplicate=exec_args["duplicate"],
            )

    def execute_insert(self, table: str, field_dict: dict) -> None:
        """Insert a record into a table."""
        columns = ', '.join(field_dict.keys())
        placeholders = ', '.join('?' for _ in field_dict)
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        self.executor.execute(sql, vars_=tuple(field_dict.values()))

    def execute_update(self, table: str, field_dict: dict, **kwargs) -> None:
        """Update rows in a table."""
        set_clause = ', '.join(f"{k}=?" for k in field_dict)
        sql = f"UPDATE {table} SET {set_clause} "
        where_sql, vars_where = self._where_clause(**kwargs)
        sql += where_sql
        vars_ = tuple(field_dict.values()) + vars_where
        self.executor.execute(sql, vars_=vars_)

    def execute_replace(self, table, field_dict):
        """
        Insert/Change Record in MARIADB table
        """
        set_fields = ' SET '
        vars_ = ()
        for key_ in field_dict.keys():
            set_fields = set_fields + ' ' + key_ + '=?, '
            if table == ISIN and key_ == DB_name:
                field_dict[key_] = field_dict[key_].upper()
            vars_ = vars_ + (field_dict[key_],)
        sql_statement = 'REPLACE INTO ' + table + set_fields
        sql_statement = sql_statement[:-2]
        self.executor.execute(sql_statement, vars_=vars_)

    def execute_delete(
        self,
        table: str,
        *,
        clause: str | None = None,
        clause_vars: Sequence[Any] = (),
        **kwargs
    ) -> None:
        """Delete rows from a table."""
        where_sql, vars_ = self._where_clause(
            clause=clause,
            clause_vars=clause_vars,
            **kwargs
        )

        sql = f"DELETE FROM {table} {where_sql}"

        self.executor.execute(sql, vars_)


class MariaDBLedger:
    """
    Ledger-related read-only database queries.

    This class is designed as a mixin and relies on the QueryBuilder
    API provided by MariaDBTables.
    """

    def _select_ledger_totals(
        self,
        *,
        account: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        exclude_account: Optional[str] = None,
    ) -> Tuple[Decimal, Decimal, Decimal]:
        """
        Calculate debit sum, credit sum and balance for a ledger account.

        The balance is calculated as:
            credit_sum - debit_sum

        Parameters
        ----------
        account : str
            Ledger account number to calculate totals for.
        from_date : Optional[str]
            Start date (inclusive), format YYYY-MM-DD.
            If None, no lower date bound is applied.
        to_date : Optional[str]
            End date (inclusive), format YYYY-MM-DD.
            If None, no upper date bound is applied.
        exclude_account : Optional[str]
            Ledger account to exclude from the calculation.
            Used to ignore opening balance postings.

        Returns
        -------
        Tuple[Decimal, Decimal, Decimal]
            A tuple containing:
            - debit_sum  : Total debit amount for the account
            - credit_sum : Total credit amount for the account
            - balance    : Net balance (credit - debit)
        """

        # Base condition: account appears on either debit or credit side
        conditions = [
            f"({DB_debit_account} = :account OR {DB_credit_account} = :account)"
        ]

        vars_ = {"account": account}

        # Apply optional date range filters
        if from_date:
            conditions.append(f"{DB_entry_date} >= :from_date")
            vars_["from_date"] = from_date

        if to_date:
            conditions.append(f"{DB_entry_date} <= :to_date")
            vars_["to_date"] = to_date

        # Exclude postings involving a specific account (e.g. opening balance account)
        if exclude_account:
            conditions.append(
                f"NOT ({DB_debit_account} = :exclude OR {DB_credit_account} = :exclude)"
            )
            vars_["exclude"] = exclude_account

        where_sql = " AND ".join(conditions)

        rows = self.select_cte(
            sql=f"""
                SELECT
                    SUM(
                        CASE
                            WHEN {DB_debit_account} = :account
                            THEN {DB_amount}
                            ELSE 0
                        END
                    ) AS debit_sum,
                    SUM(
                        CASE
                            WHEN {DB_credit_account} = :account
                            THEN {DB_amount}
                            ELSE 0
                        END
                    ) AS credit_sum,
                    SUM(
                        CASE
                            WHEN {DB_debit_account}  = :account THEN -{DB_amount}
                            WHEN {DB_credit_account} = :account THEN  {DB_amount}
                            ELSE 0
                        END
                    ) AS balance
                FROM {LEDGER}
                WHERE {where_sql}
            """,
            vars_=vars_,
            fields=("debit_sum", "credit_sum", "balance"),
        )

        # Normalize NULL aggregates to Decimal(0)
        if not rows:
            return Decimal("0.00"), Decimal("0.00"), Decimal("0.00")

        debit_sum, credit_sum, balance = rows[0]
        return (
            debit_sum or Decimal("0.00"),
            credit_sum or Decimal("0.00"),
            balance or Decimal("0.00"),
        )

    # ------------------------------------------------------------------
    # Ledger account selection
    # ------------------------------------------------------------------

    def select_ledger_account(
        self,
        field_list: list[str] | str,
        account: str,
        *,
        order: str | list[str] | None = None,
        result_dict: bool = True,
        date_name: str | None = None,
        **kwargs
    ) -> list[dict] | list[tuple]:
        """
        Select ledger entries where the account appears on debit or credit side.
        """

        if not field_list:
            return []

        return self._select(
            table=LEDGER_VIEW,
            fields=field_list,
            clause=f"({DB_credit_account} = ? OR {DB_debit_account} = ?)",
            clause_vars=(account, account),
            order=order,
            date_name=date_name,
            result_dict=result_dict,
            **kwargs,
        )

    def select_ledger_statement_missed(
        self,
        period: tuple
    ) -> tuple[list[int], list[int]]:
        """
        Return ledger entry IDs that have no corresponding statement entries
        within the given period.

        The result is separated into credit and debit ledger IDs.
        """

        # ------------------------------------------------------------
        # WHERE clause for date filtering
        # ------------------------------------------------------------
        where_sql, vars_ = self._where_clause(
            date_name=DB_entry_date,
            period=period
        )

        # ------------------------------------------------------------
        # Base SQL template
        # ------------------------------------------------------------
        sql_template = f"""
            WITH eligible_ledger AS (
                SELECT
                    l.id_no,
                    {{account_field}} AS account
                FROM ledger l
                JOIN ledger_coa c
                  ON {{account_field}} = c.account
                 AND c.download = 1
                 AND c.portfolio = 0
                {where_sql}
            )
            SELECT el.id_no
            FROM eligible_ledger el
            WHERE NOT EXISTS (
                SELECT 1
                FROM ledger_statement s
                WHERE s.id_no = el.id_no
                  AND s.status = ?
            )
        """

        # ------------------------------------------------------------
        # Debit side
        # ------------------------------------------------------------
        debit_ids = [
            row[0]
            for row in self.select_cte(
                sql=sql_template.format(account_field="l.debit_account"),
                vars_=vars_ + (DEBIT,),
                fields=("id_no",),
            )
        ]

        # ------------------------------------------------------------
        # Credit side
        # ------------------------------------------------------------
        credit_ids = [
            row[0]
            for row in self.select_cte(
                sql=sql_template.format(account_field="l.credit_account"),
                vars_=vars_ + (CREDIT,),
                fields=("id_no",),
            )
        ]

        return credit_ids, debit_ids

    # ------------------------------------------------------------------
    # Posting text → account mapping
    # ------------------------------------------------------------------
    def select_ledger_posting_text_account(
        self,
        iban: str,
        credit: bool = True
    ) -> dict[str, str]:
        """
        Return recommended ledger accounts per posting text
        based on the last 365 days.
        """

        from_date = date_days.convert(
            date_days.subtract(date.today(), 365)
        )
        status = CREDIT if credit else DEBIT

        rows = self._select(
            table=(
                f"{STATEMENT} AS s "
                f"JOIN {LEDGER_COA} AS c ON s.iban = c.iban"
            ),
            fields=["s.posting_text", "c.account"],
            distinct=True,
            clause=(
                "s.entry_date > ? "
                "AND s.status = ? "
                "AND s.iban = ?"
            ),
            clause_vars=(from_date, status, iban),
            result_dict=False,
        )

        return dict(rows)

    def select_ledger_balance(
        self,
        account_dict: Dict[str, any],
        opening_balance_account: str,
        period: Tuple[str, str],
    ) -> Optional[Decimal]:
        """
        Determine the balance of a ledger account for a given period.

        Priority order:
        0. Use table LEDGER_DAILY_BALANCE
        1. Use the latest opening balance booking involving the opening balance account
           before or at period end.
        2. If no opening balance booking exists:
           - Use the latest STATEMENT entry (closing balance + movements).
        3. If neither exists:
           - Calculate balance purely from ledger movements within the period.

        Parameters
        ----------
        account_dict : Dict[str, any]
            Ledger account metadata dictionary.
        opening_balance_account : str
            Ledger account used for opening balance postings.
        period : Tuple[str, str]
            Period (from_date, to_date), format YYYY-MM-DD.

        Returns
        -------
        Optional[Decimal]
            Calculated ledger balance, or None if no data exists.
        """

        from_date, to_date = period
        account = account_dict[DB_account]

        balance = self.select_table(LEDGER_DAILY_BALANCE, DB_balance, account=account, entry_date=to_date)
        if balance:
            return balance

        # Resolve IBAN (if available)
        iban = self.select_scalar(
            LEDGER_COA,
            DB_iban,
            account=account
        )

        if account_dict[DB_asset_accounting]:
            # ------------------------------------------------------------------
            # Only relevant for non-bank accounts
            # 1. Determine latest opening balance booking
            # ------------------------------------------------------------------
            opening_rows = self.select_cte(
                sql=f"""
                    SELECT
                        l.{DB_entry_date} AS opening_date,
                        SUM(
                            CASE
                                WHEN l.{DB_debit_account}  = :account THEN -l.{DB_amount}
                                WHEN l.{DB_credit_account} = :account THEN  l.{DB_amount}
                                ELSE 0
                            END
                        ) AS opening_balance
                    FROM {LEDGER} l
                    WHERE (
                            l.{DB_debit_account}  = :opening_account
                         OR l.{DB_credit_account} = :opening_account
                    )
                      AND (
                            l.{DB_debit_account}  = :account
                         OR l.{DB_credit_account} = :account
                    )
                      AND l.{DB_entry_date} <= :to_date
                    GROUP BY l.{DB_entry_date}
                    ORDER BY l.{DB_entry_date} DESC
                    LIMIT 1
                """,
                vars_={
                    "account": account,
                    "opening_account": opening_balance_account,
                    "to_date": to_date,
                },
                fields=("opening_date", "opening_balance"),
            )

            # ------------------------------------------------------------------
            # Case A: Opening balance exists
            # ------------------------------------------------------------------
            if opening_rows:
                opening_date, opening_balance = opening_rows[0]

                _, _, movements = self._select_ledger_totals(
                    account=account,
                    from_date=opening_date,
                    to_date=to_date,
                    exclude_account=opening_balance_account,
                )
                if account_dict[DB_asset_accounting]:
                    # An opening booking must only exist for asset accounts
                    return opening_balance + movements
                else:
                    return movements

        # ------------------------------------------------------------------
        # Case B: No opening balance → STATEMENT fallback
        # ------------------------------------------------------------------
        if iban and self.select_exists(STATEMENT, iban=iban):

            statement_row = self.select_last_row(
                table=STATEMENT,
                fields=(DB_closing_balance, DB_closing_status, DB_closing_entry_date),
                order=DB_entry_date,
                iban=iban,
            )

            if statement_row:
                closing_balance, closing_status, statement_date = statement_row

                # Normalize statement balance sign
                base_balance = (
                    -closing_balance
                    if closing_status == CREDIT
                    else closing_balance
                )

                _, _, movements = self._select_ledger_totals(
                    account=account,
                    from_date=statement_date,
                    to_date=to_date,
                )

                return base_balance + movements

        # ------------------------------------------------------------------
        # Case C: Pure ledger movements within period
        # ------------------------------------------------------------------
        _, _, balance = self._select_ledger_totals(
            account=account,
            from_date=from_date,
            to_date=to_date,
        )

        return balance

    def select_ledger_total_amount(
        self,
        iban: str,
    ) -> dict[str, Any]:
        """
        Return the most recent ledger entry (date, status, amount)
        for the given IBAN, excluding opening balance postings.
        """

        # ------------------------------------------------------------
        # Resolve opening balance account
        # ------------------------------------------------------------
        opening_account = self.select_scalar(
            LEDGER_COA,
            DB_account,
            opening_balance_account=True,
        )
        if not opening_account:
            MessageBoxInfo(
                message=get_message(MESSAGE_TEXT, "OPENING_ACCOUNT_MISSED")
            )
            return {}

        # ------------------------------------------------------------
        # Resolve internal ledger account for IBAN
        # ------------------------------------------------------------
        account = self.select_scalar(
            LEDGER_COA,
            DB_account,
            iban=iban,
        )
        if not account:
            return {}

        # ------------------------------------------------------------
        # SQL: unified debit / credit view
        # ------------------------------------------------------------
        sql = """
            SELECT
                l.entry_date,
                CASE
                    WHEN l.credit_account = ? THEN ?
                    ELSE ?
                END AS status,
                l.amount
            FROM ledger l
            WHERE (
                    l.credit_account = ?
                AND l.debit_account <> ?
            )
               OR (
                    l.debit_account = ?
                AND l.credit_account <> ?
            )
            ORDER BY l.entry_date DESC
            LIMIT 1
        """

        rows = self.select_cte(
            sql=sql,
            vars_=(
                account, CREDIT, DEBIT,
                account, opening_account,
                account, opening_account,
            ),
            fields=(DB_entry_date, DB_status, DB_amount),
        )

        if not rows:
            return {}

        entry_date, status, amount = rows[0]

        return {
            DB_entry_date: entry_date,
            DB_status: status,
            DB_amount: amount,
        }


class MariaDBHolding:

    def select_isin_with_ticker(
        self,
        field_list: list[str] | str,
        order: str | list[str] | None = None,
        **kwargs
    ):
        """
        Select ISIN records that have a valid ticker symbol.
        """

        if not field_list:
            return []

        return self._select(
            table=ISIN,
            fields=field_list,
            clause=f"{DB_symbol} <> ?",
            clause_vars=('NA',),
            order=order,
            **kwargs
        )

    def select_holding_all_total(self, *, result_dict: bool = False, **kwargs):
        return self._select(
            table=HOLDING,
            fields=[
                DB_price_date,
                f"SUM({DB_total_amount}) AS {DB_total_amount}",
                f"SUM({DB_acquisition_amount}) AS {DB_acquisition_amount}",
            ],
            group_by=DB_price_date,
            order=DB_price_date,
            sort="ASC",
            result_dict=result_dict,
            **kwargs
            )

    def select_holding_isins_interval(
        self,
        iban: str | None,
        comparison_field: str,
        isin_codes: Iterable[str],
        **kwargs
    ) -> Tuple[Any, Any, list]:
        """
        Select holding data for multiple ISINs within their maximum common
        available time interval.

        The method determines the overlapping date range in which *all*
        given ISINs have data available and then selects the corresponding
        holding data for that interval.

        Parameters
        ----------
        iban : str | None
            IBAN to restrict the holding data to a specific account.
            If None, all IBANs are considered.
        comparison_field : str
            Database field used for comparison or calculation.
            If FN_PROFIT_LOSS is provided, the value is calculated as
            (total_amount - acquisition_amount).
        isin_codes : Iterable[str]
            List or iterable of ISIN codes to be evaluated.
        **kwargs
            Additional filters passed to `_where_clause()`
            (e.g. portfolio, currency, period).

        Returns
        -------
        tuple
            (
                from_date,
                to_date,
                selected_holding_data
            )

            from_date : date
                Start date of the common interval.
            to_date : date
                End date of the common interval.
            selected_holding_data : list
                Holding data rows for the calculated interval.
        """
        # ------------------------------------------------------------
        # Determine min/max price_date per ISIN (QueryBuilder-basiert)
        # ------------------------------------------------------------
        periods: list[tuple] = []

        for isin in isin_codes:
            min_date = self.select_scalar(
                HOLDING,
                f"MIN({DB_price_date})",
                isin_code=isin,
                **kwargs
            )
            max_date = self.select_scalar(
                HOLDING,
                f"MAX({DB_price_date})",
                isin_code=isin,
                **kwargs
            )

            if min_date and max_date:
                periods.append((min_date, max_date))

        if not periods:
            return None, None, []
        # ------------------------------------------------------------
        # Calculate common overlapping interval
        # ------------------------------------------------------------
        from_dates, to_dates = zip(*periods)

        from_date = max(from_dates)
        to_date = min(to_dates)

        if from_date > to_date:
            return None, None, []
        # ------------------------------------------------------------
        # Define selected fields
        # ------------------------------------------------------------
        if comparison_field == FN_PROFIT_LOSS:
            field_list = [
                DB_name,
                DB_price_date,
                f"{DB_total_amount} - {DB_acquisition_amount} AS {FN_PROFIT_LOSS}",
            ]
        else:
            field_list = [
                DB_name,
                DB_price_date,
                comparison_field,
            ]
        # ------------------------------------------------------------
        # Fetch holding data for common interval
        # ------------------------------------------------------------
        query_kwargs = {
            DB_ISIN: list(isin_codes),
            "period": (from_date, to_date),
        }

        if iban:
            query_kwargs[DB_iban] = iban

        selected_holding_data = self.select_holding_data(
            field_list=field_list,
            **query_kwargs
        )

        return from_date, to_date, selected_holding_data

    def select_holding_total(
        self,
        **kwargs
                ) -> List[Tuple]:
        """
        Select aggregated holding totals per price date.

        The method returns the total portfolio amount and the summed
        acquisition amount grouped by price date. Optional filters
        are applied via `_where_clause()`.

        Parameters
        ----------
        **kwargs
            Additional WHERE filters passed to `_where_clause()`
            (e.g. iban, portfolio, isin_code, period).

        Returns
        -------
        list[tuple]
            Rows containing:
                (
                    price_date,
                    total_amount_portfolio,
                    acquisition_amount_sum
                )
            Ordered by price_date ascending.
        """
        return self._select(
            table=HOLDING,
            fields=[
                DB_price_date,
                "total_amount_portfolio",
                f"SUM({DB_acquisition_amount}) AS acquisition_amount_sum",
            ],
            group_by=[DB_price_date, "total_amount_portfolio"],
            order=DB_price_date,
            sort="ASC",
            **kwargs
        )

    def select_holding_data(
        self,
        field_list: Union[str, Iterable[str]] = (
            "isin_code, name, total_amount, acquisition_amount, "
            "pieces, market_price, price_currency, amount_currency"
        ),
        *,
        result_dict: bool = True,
        **kwargs
    ) -> List[dict] | List[tuple]:
        """
        Select holding data from HOLDING_VIEW with optional filters.

        The method builds the WHERE clause using `_where_clause()` and
        returns holding rows either as dictionaries or tuples.

        Parameters
        ----------
        field_list : str | Iterable[str], optional
            Fields to select. Can be a comma-separated string or
            an iterable of column names.
        result_dict : bool, optional
            If True, rows are returned as dictionaries.
            If False, rows are returned as tuples.
        **kwargs
            Additional filters passed to `_where_clause()`
            (e.g. iban, isin_code, period).

        Returns
        -------
        list[dict] | list[tuple]
            Selected holding rows.
            Returns an empty list if no fields are specified.
        """
        if not field_list:
            return []

        return self._select(
            table=HOLDING_VIEW,
            fields=field_list,
            result_dict=result_dict,
            **kwargs
        )

    def select_holding_last(
        self,
        iban: str,
        name: str,
        period: tuple,
        field_list: str | Iterable[str] = (
            "price_date, market_price, pieces, "
            "total_amount, acquisition_amount"
        ),
    ) -> Tuple[Any, ...] | None:
        """
        Select the most recent holding entry for a given ISIN name
        within a specified period.

        The method resolves the ISIN from the provided name, determines
        the latest available price date within the given period, and
        returns the corresponding holding data row.

        Parameters
        ----------
        iban : str
            IBAN of the holding account.
        name : str
            Security name used to resolve the ISIN.
        period : tuple
            (from_date, to_date) date range.
        field_list : str | Iterable[str], optional
            Fields to select. Can be a comma-separated string or
            an iterable of column names.

        Returns
        -------
        tuple | None
            Tuple containing the selected holding fields for the
            latest price date, or None if no data is found.
        """
        # ------------------------------------------------------------
        # Resolve ISIN from name
        # ------------------------------------------------------------
        isin = self.select_scalar(
            ISIN,
            DB_ISIN,
            name=name
        )

        if not isin:
            return None
        # ------------------------------------------------------------
        # Determine latest price_date within period
        # ------------------------------------------------------------
        last_price_date = self.select_scalar(
            HOLDING,
            f"MAX({DB_price_date})",
            iban=iban,
            isin_code=isin,
            period=period
        )

        if last_price_date is None:
            return None
        # ------------------------------------------------------------
        # Fetch holding row for latest price_date
        # ------------------------------------------------------------
        rows = self._select(
            table=HOLDING_VIEW,
            fields=field_list,
            iban=iban,
            isin_code=isin,
            price_date=last_price_date,
            result_dict=False
        )

        return rows[0] if rows else None

    def select_holding_field_values(
        self,
        field: str,
        **kwargs
    ) -> list:
        """
        Select distinct field values from the HOLDING table.

        The method returns a flat list containing unique values of the
        specified field(s). Filters are applied using `_where_clause()`.

        Parameters
        ----------
        field : str
            Field to select.
        **kwargs
            Additional WHERE filters passed to `_where_clause()`
            (e.g. iban, isin_code, period).

        Returns
        -------
        list
            List of distinct values for the selected field.
        """
        rows = self._select(
            table=HOLDING,
            fields=field,
            distinct=True,
            result_dict=False,
            **kwargs
        )

        # flatten result: [(v,), (v,), ...] -> [v, v, ...]
        return [row[0] for row in rows]

    def update_total_holding_amount(self, **kwargs) -> None:
        """
        Update the portfolio total amount per price date in batch using MariaDBTables.

        Aggregates total_amount per IBAN and price_date and updates the
        HOLDING table with the calculated totals in a single query.

        Parameters
        ----------
        **kwargs
            Filters passed to `_where_clause()` to restrict the aggregation
            (e.g. iban, period, portfolio).

        Returns
        -------
        None
        """
        # ------------------------------------------------------------
        # Aggregate total_amount per IBAN and price_date
        # ------------------------------------------------------------
        rows = self._select(
            table=HOLDING,
            fields=[
                DB_iban,
                DB_price_date,
                f"SUM({DB_total_amount}) AS total_amount_portfolio"
            ],
            group_by=[DB_iban, DB_price_date],
            **kwargs
        )

        if not rows:
            return  # nothing to update
        # ------------------------------------------------------------
        # Batch update each row using execute_update and _where_clause
        # ------------------------------------------------------------
        for iban, price_date, total_amount_portfolio in rows:
            self.execute_update(
                table=HOLDING,
                field_dict={"total_amount_portfolio": total_amount_portfolio},
                iban=iban,
                **{DB_price_date: price_date}
            )


class MariaDBStatements:
    """
    Statement-related database queries.

    Provides aggregated statement values, SEPA-related lookups,
    and consolidated balance calculations across STATEMENT,
    HOLDING, and LEDGER.
    """

    # ------------------------------------------------------------------
    # SEPA lookup
    # ------------------------------------------------------------------
    def select_sepa_fields_in_statement(
        self,
        iban: str,
        clause: str | None = None,
        clause_vars: tuple = (),
        **kwargs
    ) -> str:
        """
        Resolve the corresponding ledger account for a SEPA statement entry.

        Credit statement → debit ledger account
        Debit statement  → credit ledger account

        Parameters
        ----------
        iban : str
            IBAN of the statement account.
        **kwargs
            Filters forwarded to `_where_clause()` (exactly one SEPA field).

        Returns
        -------
        str
            Ledger account number or NOT_ASSIGNED.
        """

        rows = self._select(
            table=STATEMENT,
            fields=[DB_iban, DB_entry_date, DB_counter, DB_status],
            order=DB_entry_date,
            date_name=DB_entry_date,
            sort='DESC',
            limit=1,
            result_dict=True,
            iban=iban,
            clause=clause,
            clause_vars=clause_vars,
            **kwargs
        )

        if not rows:
            return NOT_ASSIGNED

        row = rows[0]

        id_no = self.select_scalar(
            LEDGER_STATEMENT,
            DB_id_no,
            iban=row[DB_iban],
            entry_date=row[DB_entry_date],
            counter=row[DB_counter],
            status=row[DB_status]
        )

        if not id_no:
            return NOT_ASSIGNED

        ledger_field = (
            DB_debit_account if row[DB_status] == CREDIT
            else DB_credit_account
        )

        account = self.select_scalar(
            LEDGER,
            ledger_field,
            id_no=id_no,
            default=NOT_ASSIGNED
        )

        return account

    # ------------------------------------------------------------------


class MariaDBTransactions:

    def get_transaction_overview(
        self,
        isin_code: str,
        period: tuple,
        iban: str | None = None,
        cost_method: str = COST_FIFO
    ) -> list[list]:
        """
        Determine opening stock, transactions, profit/loss per sale
        and ending stock for a given ISIN and period.

        Supported cost methods:
            COST_FIFO    = "FIFO"
            COST_LIFO    = "LIFO"
            COST_AVERAGE = "AVERAGE"
        """

        # ------------------------------------------------------------
        # Helper functions
        # ------------------------------------------------------------

        def total_pieces(cost_basis):
            return sum(lot["pieces"] for lot in cost_basis)

        # -------------------- BUY --------------------

        def buy_lot(cost_basis, buy_pieces, posted_amount):
            """Add a new lot (used for FIFO and LIFO)."""
            buy_pieces = Decimal(buy_pieces)
            posted_amount = Decimal(posted_amount)

            price = abs(posted_amount) / buy_pieces

            cost_basis.append({
                "pieces": buy_pieces,
                "price": price
            })

            return buy_pieces

        def buy_average(state, buy_pieces, posted_amount):
            """Update average cost basis."""
            buy_pieces = Decimal(buy_pieces)
            posted_amount = Decimal(posted_amount)

            buy_value = abs(posted_amount)

            total_cost = state["pieces"] * state["avg_price"] + buy_value
            state["pieces"] += buy_pieces
            state["avg_price"] = total_cost / state["pieces"]

            return buy_pieces

        # -------------------- SELL --------------------

        def sell_lot(cost_basis, sell_pieces, market_price, lifo=False):
            """Sell using FIFO or LIFO."""
            sell_pieces = Decimal(sell_pieces)
            market_price = Decimal(market_price)

            remaining = sell_pieces
            cost_sum = Decimal("0.00")

            while remaining > 0 and cost_basis:
                lot = cost_basis[-1] if lifo else cost_basis[0]

                take = min(lot["pieces"], remaining)
                cost_sum += take * lot["price"]

                lot["pieces"] -= take
                remaining -= take

                if lot["pieces"] == 0:
                    cost_basis.pop(-1 if lifo else 0)

            if remaining > 0:
                raise ValueError("Not enough pieces to sell")

            proceeds = sell_pieces * market_price
            profit_loss = proceeds - cost_sum

            return -sell_pieces, proceeds, profit_loss

        def sell_average(state, sell_pieces, market_price):
            """Sell using average cost."""
            sell_pieces = Decimal(sell_pieces)
            market_price = Decimal(market_price)

            cost = sell_pieces * state["avg_price"]
            proceeds = sell_pieces * market_price

            state["pieces"] -= sell_pieces
            if state["pieces"] == 0:
                state["avg_price"] = Decimal("0.00")

            profit_loss = proceeds - cost
            return -sell_pieces, proceeds, profit_loss

        # -------------------- REBUILD --------------------

        def rebuild_cost_state(isin_code, iban, until_date):
            """
            Rebuild cost basis state from historical transactions.
            """
            rows = self.select_rows(
                table=TRANSACTION,
                fields=("transaction_type", "pieces", "posted_amount", "price"),
                isin_code=isin_code,
                iban=iban,
                clause="price_date < ?",
                clause_vars=(until_date,),
                order=[("price_date", "ASC"), ("counter", "ASC")]
            )

            if cost_method == COST_AVERAGE:
                state = {"pieces": Decimal("0.00"), "avg_price": Decimal("0.00")}

                for t_type, pieces, amount, price in rows:
                    if t_type != TRANSACTION_DELIVERY:
                        buy_average(state, pieces, amount)
                    else:
                        sell_average(state, pieces, price)

                return state

            else:
                cost_basis = []
                for t_type, pieces, amount, price in rows:
                    if t_type != TRANSACTION_DELIVERY:
                        buy_lot(cost_basis, pieces, amount)
                    else:
                        sell_lot(cost_basis, pieces, price, lifo=(cost_method == COST_LIFO))
                return cost_basis

        # ------------------------------------------------------------
        # Start of method
        # ------------------------------------------------------------

        from_date, to_date = period
        from_date, to_date = xetra_cls.adjust_period(from_date, to_date, xetra_bday)

        result: list[list] = []

        try:
            # --------------------------------------------------------
            # 1. Opening stock
            # --------------------------------------------------------

            cost_state = rebuild_cost_state(isin_code, iban, from_date)

            if cost_method == COST_AVERAGE:
                current_pieces = cost_state["pieces"]
            else:
                current_pieces = total_pieces(cost_state)

            if current_pieces > 0:
                market_price = self.get_close_price(isin_code, from_date)

                result.append([
                    from_date,
                    0,
                    "OPEN",
                    Decimal(market_price),
                    Decimal("0.00"),
                    current_pieces,
                    current_pieces * market_price,
                    Decimal("0.00"),
                    iban
                ])

            # --------------------------------------------------------
            # 2. Load transactions
            # --------------------------------------------------------

            transactions = self.select_rows(
                table=TRANSACTION,
                fields=(
                    "price_date",
                    "counter",
                    "transaction_type",
                    "price",
                    "pieces",
                    "posted_amount"
                ),
                order=[("price_date", "ASC"), ("counter", "ASC")],
                isin_code=isin_code,
                iban=iban,
                period=period
            )

            # --------------------------------------------------------
            # 3. Process transactions
            # --------------------------------------------------------

            for price_date, counter, t_type, price, pieces, posted_amount in transactions:

                if t_type != TRANSACTION_DELIVERY:
                    # BUY
                    if cost_method == COST_AVERAGE:
                        tx_pieces = buy_average(cost_state, pieces, posted_amount)
                    else:
                        tx_pieces = buy_lot(cost_state, pieces, posted_amount)

                    profit_loss = Decimal("0.00")
                    posted_amount = abs(Decimal(posted_amount))

                else:
                    # SELL
                    if cost_method == COST_AVERAGE:
                        tx_pieces, posted_amount, profit_loss = sell_average(
                            cost_state, pieces, price
                        )
                    else:
                        tx_pieces, posted_amount, profit_loss = sell_lot(
                            cost_state,
                            pieces,
                            price,
                            lifo=(cost_method == COST_LIFO)
                        )

                if cost_method == COST_AVERAGE:
                    current_pieces = cost_state["pieces"]
                else:
                    current_pieces = total_pieces(cost_state)

                result.append([
                    price_date,
                    counter,
                    t_type,
                    price,
                    tx_pieces,
                    current_pieces,
                    posted_amount,
                    profit_loss,
                    iban
                ])

            # --------------------------------------------------------
            # 4. Virtual CLOSE
            # --------------------------------------------------------

            if current_pieces > 0:
                end_price = self.get_close_price(isin_code, to_date)

                if cost_method == COST_AVERAGE:
                    tx_pieces, posted_amount, profit_loss = sell_average(
                        cost_state, current_pieces, end_price
                    )
                else:
                    tx_pieces, posted_amount, profit_loss = sell_lot(
                        cost_state,
                        current_pieces,
                        end_price,
                        lifo=(cost_method == COST_LIFO)
                    )

                if cost_method == COST_AVERAGE:
                    current_pieces = cost_state["pieces"]
                else:
                    current_pieces = total_pieces(cost_state)

                result.append([
                    to_date,
                    9999,
                    "CLOSE",
                    Decimal(end_price),
                    tx_pieces,
                    current_pieces,
                    posted_amount,
                    profit_loss,
                    iban
                ])

            return result

        except Exception as exc:
            MessageBoxError(
                title="TRANSACTION ERROR",
                info_storage=Informations.BANKDATA_INFORMATIONS,
                message=get_message(
                    MESSAGE_TEXT,
                    "UNEXCEPTED_ERROR",
                    __file__,
                    0,
                    "get_transaction_overview",
                    type(exc).__name__,
                    exc,
                    ""
                )
            )
            return []

    def select_transactions_data(
        self,
        field_list: str | Iterable[str] = (
            "price_date, counter, transaction_type, "
            "price, pieces, posted_amount"
        ),
        **kwargs
    ) -> List[Tuple]:

        # Normalize field list
        fields_sql = self._normalize_fields(field_list)
        fields = (
            [f.strip() for f in fields_sql.split(",")]
            if isinstance(fields_sql, str)
            else list(fields_sql)
        )

        # WHERE clause
        where_sql, vars_ = self._where_clause(**kwargs)

        # ❗ ORDER BY REMOVED FROM INNER SQL
        sql = f"""
            SELECT {fields_sql}
            FROM {TRANSACTION_VIEW}
            {where_sql}
        """

        # ORDER BY is applied by the OUTER query (select_cte wrapper)
        return self.select_cte(
            sql=sql,
            vars_=vars_,
            fields=fields,
        )

    def _transaction_base_cte(self, where_sql: str) -> str:
        return f"""
            WITH tx AS (
                SELECT
                    isin_code,
                    name,
                    amount_currency,
                    CASE
                        WHEN transaction_type = '{TRANSACTION_DELIVERY}' THEN  pieces
                        WHEN transaction_type = '{TRANSACTION_RECEIPT}'  THEN -pieces
                    END AS pieces,
                    CASE
                        WHEN transaction_type = '{TRANSACTION_DELIVERY}' THEN  posted_amount
                        WHEN transaction_type = '{TRANSACTION_RECEIPT}'  THEN -posted_amount
                    END AS posted_amount
                FROM {TRANSACTION_VIEW}
                {where_sql}
                AND transaction_type IN ('{TRANSACTION_DELIVERY}', '{TRANSACTION_RECEIPT}')
            )
        """

    def _transaction_profit_closed_sql(self, where_sql: str) -> str:
        return f"""
            {self._transaction_base_cte(where_sql)}
            SELECT
                isin_code,
                name,
                SUM(posted_amount) AS profit,
                amount_currency,
                SUM(pieces) AS pieces
            FROM tx
            GROUP BY isin_code, name, amount_currency
            HAVING SUM(pieces) = 0
        """

    def transaction_profit_closed(
        self,
        **kwargs
    ) -> List[Tuple[str, str, Decimal, str, Decimal]]:

        where_sql, vars_ = self._where_clause(**kwargs)
        sql = self._transaction_profit_closed_sql(where_sql)

        return self.select_cte(
            sql=sql,
            vars_=vars_,
            fields=['isin_code', 'name', 'profit', 'amount_currency', 'pieces']
        )

    def transaction_profit_all(
        self,
        **kwargs
    ) -> List[Tuple[str, str, Decimal, str, Decimal]]:

        where_sql, vars_ = self._where_clause(**kwargs)

        max_price_date = self.select_scalar(
            HOLDING, f"MAX({DB_price_date})", **kwargs
        )
        if max_price_date is None:
            return []

        closed_sql = self._transaction_profit_closed_sql(where_sql)

        holding_sql = """
            SELECT
                isin_code,
                name,
                (total_amount - acquisition_amount) AS profit,
                amount_currency,
                pieces
            FROM holding_view
            WHERE price_date = ?
        """

        sql = f"""
            {closed_sql}
            UNION ALL
            {holding_sql}
        """

        vars_ = vars_ + (str(max_price_date),)

        return self.select_cte(
            sql=sql,
            vars_=vars_,
            fields=['isin_code', 'name', 'profit', 'amount_currency', 'pieces']
        )


class MariaDBPrices:

    def select_first_price_date_of_prices(
        self,
        symbol_list: list[str],
        **kwargs
    ) -> str | None:
        """
        Select the first price_date for a list of symbols in the PRICES table.

        Only considers symbols with existing rows. Skips symbols with no row.
        Returns the latest among the first dates for all symbols found.

        Parameters
        ----------
        symbol_list : list[str]
            List of symbol identifiers to query.
        **kwargs
            Additional filters passed to `_where_clause()`.

        Returns
        -------
        str | None
            Latest first price_date across all symbols in 'YYYY-MM-DD' format,
            or None if no data exists.
        """
        first_dates: list[str] = []

        # Base WHERE clause from additional filters
        base_where, base_vars = self._where_clause(**kwargs)

        for symbol in symbol_list:
            # Add symbol filter
            where_clause = f"{base_where} AND {DB_symbol} = ?" if base_where else f"WHERE {DB_symbol} = ?"
            vars_ = base_vars + (symbol,)

            # Use _select_scalar to safely fetch MIN price_date
            first_date = self.select_scalar(
                PRICES,
                f"MIN({DB_price_date})",
                clause=where_clause,
                clause_vars=vars_
            )

            if first_date:
                first_dates.append(str(first_date)[:10])

        return max(first_dates) if first_dates else None

    def get_close_price(self, isin_code, price_date):

        symbol = self.select_scalar(ISIN, DB_symbol, isin_code=isin_code)
        close = self.select_scalar(PRICES, DB_close, symbol=symbol)
        if close:
            return Decimal(close)
        else:
            message = get_message(
                MESSAGE_TEXT, 'PRICES_NO',
                ' '.join([DB_price_date.upper(), price_date]),
                symbol,
                '',
                isin_code,
                ''
                )
            MessageBoxInfo(message=message)
            return Decimal("0.00")


class MariaDBShelves:
    """
    Helper class for managing bank and account information stored in the SHELVES table.

    Provides methods to list banks, retrieve accounts, and manipulate JSON-serialized bank data.
    """

    # ----------------------------
    # IBAN / Bank Helpers
    # ----------------------------
    def _remove_obsolete_iban_rows(self, row_list: list[tuple]) -> list[tuple]:
        """
        Filter out rows containing IBANs that are no longer available.

        Parameters
        ----------
        row_list : list[tuple]
            List of rows where the first element of each row is an IBAN.

        Returns
        -------
        list[tuple]
            Filtered list containing only rows with valid IBANs.
        """
        all_ibans = self._dict_all_ibans()
        return [row for row in row_list if row[0] in all_ibans]

    def listbank_codes(self) -> list[str]:
        """
        List all bank codes from the SHELVES table.

        Returns
        -------
        list[str]
            List of bank codes.
        """
        result = self._select(table=SHELVES, fields=DB_code)
        return list(chain.from_iterable(result))

    def dictbank_names(self) -> dict[str, str]:
        """
        Map bank codes to customized bank names (fall back to code if name missing).

        Returns
        -------
        dict[str, str]
            Dictionary {bank_code: bank_name}.
        """
        return {
            code: self.shelve_get_key(code, KEY_BANK_NAME) or code
            for code in self.listbank_codes()
        }

    def dictaccount(self, bank_code: str, account_number: str) -> dict | None:
        """
        Get account information from SHELVES for a specific bank and account number.

        Parameters
        ----------
        bank_code : str
            Bank code identifier.
        account_number : str
            Account number to look up.

        Returns
        -------
        dict | None
            Account dictionary or None if not found.
        """
        accounts = self.shelve_get_key(bank_code, KEY_ACCOUNTS) or []
        return next(
            (acc for acc in accounts if acc[KEY_ACC_ACCOUNT_NUMBER] == account_number.lstrip("0")),
            None
        )

    def _dict_all_ibans(self) -> dict[str, str]:
        """
        Build a dictionary of all IBANs and their associated product names.

        Returns
        -------
        dict[str, str]
            Dictionary {IBAN: product_name}.
        """
        all_ibans = {}
        for bank_code in self.listbank_codes():
            accounts = self.shelve_get_key(bank_code, KEY_ACCOUNTS) or []
            for acc in accounts:
                all_ibans[acc[KEY_ACC_IBAN]] = acc[KEY_ACC_PRODUCT_NAME]
        return all_ibans

    # ----------------------------
    # Shelve JSON Helpers
    # ----------------------------
    def shelve_serialize(self, obj) -> list:
        """
        Convert ValueList objects to JSON-serializable lists.

        Parameters
        ----------
        obj : ValueList
            Object to serialize.

        Returns
        -------
        list
            Serialized list.

        Raises
        ------
        TypeError
            If the object is not a ValueList.
        """
        if isinstance(obj, ValueList):
            return list(obj)
        raise TypeError(f"Expected ValueList, got {type(obj)}")

    def shelve_get_key(
        self,
        shelve_name: str,
        key: str | list[str],
        none: bool = True
    ) -> dict | Any:
        """
        Retrieve a key or list of keys from the shelve JSON data.

        Parameters
        ----------
        shelve_name : str
            Bank/shelve identifier.
        key : str | list[str]
            Key(s) to fetch from the JSON data.
        none : bool, default True
            If True, missing keys return None; otherwise return empty dict.

        Returns
        -------
        dict | any
            Dictionary (for list input) or single value (for string input).
        """
        _bankdata = self.select_scalar(SHELVES, DB_bankdata, code=shelve_name)
        if not _bankdata:
            Termination(
                info=get_message(MESSAGE_TEXT, "SHELVE_NAME_MISSED", shelve_name)
            ).terminate()

        bankdata = json.loads(_bankdata)

        if isinstance(key, list):
            res_dict = dict.fromkeys(key, None) if none else {}
            res_dict.update(bankdata)
            return res_dict
        return bankdata.get(key, {} if not none else None)

    def shelve_put_key(self, shelve_name: str, data: tuple | list[tuple]) -> None:
        """
        Insert or update key-value pairs in shelve JSON data.

        Parameters
        ----------
        shelve_name : str
            Bank/shelve identifier.
        data : tuple | list[tuple]
            Key-value pair(s) to update.
        """
        _bankdata = self.select_scalar(SHELVES, DB_bankdata, code=shelve_name)
        bankdata = json.loads(_bankdata) if _bankdata else {}

        if isinstance(data, tuple):
            data = [data]

        bankdata.update(dict(data))
        bankdata_json = json.dumps(bankdata, default=self.shelve_serialize)
        self.execute_replace(SHELVES, {DB_code: shelve_name, DB_bankdata: bankdata_json})

    def shelve_del_key(self, shelve_name: str, key: str) -> None:
        """
        Delete a key from shelve JSON data.

        Parameters
        ----------
        shelve_name : str
            Bank/shelve identifier.
        key : str
            Key to remove.
        """
        _bankdata = self.select_scalar(SHELVES, DB_bankdata, code=shelve_name)
        if _bankdata:
            bankdata = json.loads(_bankdata)
            bankdata.pop(key, None)
            self.execute_replace(SHELVES, {DB_code: shelve_name, DB_bankdata: json.dumps(bankdata)})


class MariaDBSelection:
    """
    Helper class for storing and retrieving last used selection values
    of selection forms in the SELECTION table.
    """

    def selection_get(self, selection_name: str) -> dict | list:
        """
        Retrieve the last used selection data for a given selection form.

        Parameters
        ----------
        selection_name : str
            Name of the selection form.

        Returns
        -------
        dict | list
            Dictionary of last used selection values, or list of last
            selected check button names. Returns empty dict if not found.
        """
        selection = self.select_scalar(SELECTION, DB_data, name=selection_name)
        if selection:
            return json.loads(selection)
        return {}

    def selection_put(self, selection_name: str, selection_dict: dict | list) -> None:
        """
        Store the last used selection data for a selection form in JSON format.

        Parameters
        ----------
        selection_name : str
            Name of the selection form.
        selection_dict : dict | list
            Dictionary of selection values or list of check button names to store.
        """
        selection_data = json.dumps(selection_dict)
        self.execute_replace(
            SELECTION,
            {DB_name: selection_name, DB_data: selection_data}
        )


class MariaDBApplication:
    """
    Helper class for storing and retrieving Alpha Vantage parameters and functions
    in the APPLICATION table.
    """

    def alpha_vantage_get(self, field_name: str) -> dict:
        """
        Retrieve Alpha Vantage values for a specific field.

        Parameters
        ----------
        field_name : str
            Column name in APPLICATION table (DB_alpha_vantage_parameter
            or DB_alpha_vantage_function).

        Returns
        -------
        dict
            Dictionary containing the Alpha Vantage values. Empty dict if not found.
        """
        alpha_vantage = self.select_scalar(APPLICATION, field_name, row_id=2)
        if alpha_vantage:
            return json.loads(alpha_vantage)
        return {}

    def alpha_vantage_put(self, field_name: str, data: dict) -> None:
        """
        Store Alpha Vantage values for a specific field in JSON format.

        Parameters
        ----------
        field_name : str
            Column name in APPLICATION table (DB_alpha_vantage_parameter
            or DB_alpha_vantage_function).
        data : dict
            Dictionary of values to store for the field.
        """
        json_data = json.dumps(data)
        if self.select_exists(APPLICATION, row_id=2):
            self.execute_update(APPLICATION, {field_name: json_data}, row_id=2)
        else:
            self.execute_insert(APPLICATION, {DB_row_id: 2, field_name: json_data})


class MariaDBServer:
    """
    Helper class for querying the SERVER table.
    """

    def select_server_code(self, **kwargs) -> list[str]:
        """
        Retrieve a list of server codes from the SERVER table.

        Parameters
        ----------
        **kwargs
            Filter arguments forwarded to `_where_clause()`.

        Returns
        -------
        list[str]
            List of server codes matching the filter criteria.
        """
        return [row[0] for row in self._select(table=SERVER, fields='code', **kwargs)]

    def select_server(self, **kwargs) -> list[str]:
        """
        Retrieve a list of server names from the SERVER table.

        Parameters
        ----------
        **kwargs
            Filter arguments forwarded to `_where_clause()`.

        Returns
        -------
        list[str]
            List of server names matching the filter criteria.
        """
        return [row[0] for row in self._select(table=SERVER, fields='server', **kwargs)]


class MariaDBServices:
    """
    Service class for storing bank holdings and statements in MariaDB.
    """

    def all_accounts(self, bank):
        """
        Insert downloaded  Bank Data in Database
        """
        for account in bank.accounts:
            bank.account_number = account[KEY_ACC_ACCOUNT_NUMBER]
            bank.account_product_name = account[KEY_ACC_PRODUCT_NAME]
            bank.iban = account[KEY_ACC_IBAN]
            bank.owner_name = account[KEY_ACC_OWNER_NAME]
            bank.statement_mt940 = False
            bank.statement_camt = False
            if 'HKKAZ' in account[KEY_ACC_ALLOWED_TRANSACTIONS]:
                bank.statement_mt940 = True
            elif 'HKCAZ' in account[KEY_ACC_ALLOWED_TRANSACTIONS]:
                if bank.supported_camt_messages:
                    bank.statement_camt = True
                else:
                    bankdata_informations_append(
                        WARNING,
                        get_message(
                            MESSAGE_TEXT,
                            'SUPPORTED_CAMT_MESSAGES',
                            bank.bank_name
                            )
                        )
            if self.select_exists(LEDGER_COA, iban=bank.iban, download=False):
                information = get_message(
                    MESSAGE_TEXT,
                    'DOWNLOAD_ACCOUNT_NOT_ACTIVATED',
                    bank.bank_name,
                    bank.owner_name,
                    bank.account_number,
                    bank.account_product_name,
                    bank.iban
                    )
                bankdata_informations_append(WARNING, information)
            else:
                information = get_message(
                    MESSAGE_TEXT,
                    'DOWNLOAD_ACCOUNT',
                    bank.bank_name,
                    bank.owner_name,
                    bank.account_number,
                    bank.account_product_name,
                    bank.iban
                    )
                if bank.scraper:
                    if 'HKKAZ' in account[KEY_ACC_ALLOWED_TRANSACTIONS]:
                        bankdata_informations_append(INFORMATION, information)
                        if self._statements(bank) is None:
                            bankdata_informations_append(
                                WARNING,
                                get_message(
                                    MESSAGE_TEXT,
                                    'DOWNLOAD_NOT_DONE',
                                    bank.bank_name
                                    )
                                )
                            return
                else:
                    if 'HKWPD' in account[KEY_ACC_ALLOWED_TRANSACTIONS]:
                        bankdata_informations_append(INFORMATION, information)
                        if self._holdings(bank) in START_DIALOG_FAILED:
                            bankdata_informations_append(
                                WARNING,
                                get_message(
                                    MESSAGE_TEXT,
                                    'DOWNLOAD_NOT_DONE',
                                    bank.bank_name
                                    )
                                )
                            return
                    if bank.statement_mt940 or bank.statement_camt:
                        bankdata_informations_append(INFORMATION, information)
                        if self._statements(bank) in START_DIALOG_FAILED:
                            bankdata_informations_append(
                                WARNING,
                                get_message(
                                    MESSAGE_TEXT,
                                    'DOWNLOAD_NOT_DONE',
                                    bank.bank_name
                                    )
                                )
                            return
        bankdata_informations_append(
            INFORMATION,
            get_message(
                MESSAGE_TEXT,
                'DOWNLOAD_DONE',
                bank.bank_name) + '\n\n'
            )

    def all_holdings(self, bank):
        """
        Insert downloaded  Holding Bank Data in Database
        """
        bankdata_informations_append(
            INFORMATION,
            get_message(
                MESSAGE_TEXT,
                'DOWNLOAD_BANK',
                bank.bank_name
                )
            )
        for account in bank.accounts:
            bank.account_number = account[KEY_ACC_ACCOUNT_NUMBER]
            bank.iban = account[KEY_ACC_IBAN]
            if 'HKWPD' in account[KEY_ACC_ALLOWED_TRANSACTIONS]:
                bankdata_informations_append(
                    INFORMATION,
                    get_message(
                        MESSAGE_TEXT,
                        'DOWNLOAD_ACCOUNT',
                        bank.bank_name,
                        '',
                        bank.account_number,
                        bank.account_product_name,
                        bank.iban
                        )
                    )
                if self._holdings(bank) in START_DIALOG_FAILED:
                    bankdata_informations_append(
                        WARNING,
                        get_message(
                            MESSAGE_TEXT,
                            'DOWNLOAD_NOT_DONE',
                            bank.bank_name
                            )
                        )
                    return

    def _holdings(self, bank) -> List[Dict[str, Any]]:
        """
        Persist daily holdings of a bank account into the HOLDING table.

        The method:
        1. Downloads current holdings from the bank.
        2. Normalizes the price date (adjusts weekends to the previous business day).
        3. Replaces existing holdings for the same IBAN and price date.
        4. Ensures referenced ISIN master data exists.
        5. Updates acquisition amounts per holding.
        6. Commits all changes as a single database transaction.

        Parameters
        ----------
        bank : Bank
            Bank object providing:
            - IBAN
            - bank_name
            - access to the holdings download dialog

        Returns
        -------
        List[Dict[str, Any]]
            List of holding records persisted in the database.
            Returns an empty list if:
            - no holdings are available, or
            - the transaction is rolled back due to user cancellation.
        """

        # ------------------------------------------------------------------
        # Start database transaction
        # ------------------------------------------------------------------
        self.executor.execute("START TRANSACTION;")

        # ------------------------------------------------------------------
        # Download holdings from bank
        # ------------------------------------------------------------------
        holdings: List[Dict[str, Any]] = bank.dialogs.holdings(bank)
        if holdings in START_DIALOG_FAILED:
            self.executor.execute("ROLLBACK;")
            return holdings

        # ------------------------------------------------------------------
        # Determine and normalize price date (weekend adjustment)
        # ------------------------------------------------------------------
        price_date_holding = max(h[DB_price_date] for h in holdings)

        weekday = date_yyyymmdd.convert(price_date_holding).weekday()
        if weekday == 5:          # Saturday
            price_date_holding = date_yyyymmdd.subtract(price_date_holding, 1)
        elif weekday == 6:        # Sunday
            price_date_holding = date_yyyymmdd.subtract(price_date_holding, 2)

        # -----------------------------------------------------------------
        # Remove existing holdings for the same IBAN and price date
        # ------------------------------------------------------------------
        self.execute_delete(
            HOLDING,
            iban=bank.iban,
            price_date=price_date_holding
        )

        # ------------------------------------------------------------------
        # Insert or replace holdings
        # ------------------------------------------------------------------
        for holding in holdings:
            isin = holding[DB_ISIN]
            name = holding[DB_name]

            # Ensure ISIN master record exists
            if not self.select_exists(ISIN, name=name):
                self.execute_replace(
                    ISIN,
                    {
                        DB_ISIN: isin,
                        DB_name: name,
                    }
                )

            # Prepare holding record
            holding_data = holding.copy()
            holding_data.pop(DB_name)
            holding_data[DB_price_date] = price_date_holding
            holding_data[DB_iban] = bank.iban

            # Persist holding
            self.execute_replace(HOLDING, holding_data)

            # Update acquisition amount (may require user interaction)
            button_state = self._set_acquisition_amount(bank, isin, name)
            if button_state == WM_DELETE_WINDOW:
                self.executor.execute("ROLLBACK;")
                MessageBoxInfo(
                    message=get_message(
                        MESSAGE_TEXT,
                        "DOWNLOAD_REPEAT",
                        bank.bank_name
                    )
                )
                return []

        # ------------------------------------------------------------------
        # Commit transaction
        # ------------------------------------------------------------------
        self.executor.execute("COMMIT;")

        return holdings

    def _set_acquisition_amount(self, bank, isin: str, name_: str):
        """
        Update the acquisition amount of a holding based on previous entries.

        Parameters
        ----------
        bank : Bank
            Bank object.
        isin : str
            ISIN of the holding.
        name_ : str
            Name of the security.

        Returns
        -------
        Optional[int]
            Button state if user interaction occurs, else None.
        """
        sql = f"""
            SELECT price_date, price_currency, market_price, acquisition_price,
                   pieces, amount_currency, total_amount, acquisition_amount, origin
            FROM {HOLDING}
            WHERE iban=? AND isin_code=?
            ORDER BY price_date DESC
            LIMIT 2
        """
        rows = self.executor.execute(sql, (bank.iban, isin))
        if not rows:
            return None

        data = [HoldingAcquisition(*row) for row in reversed(rows)]
        pieces_diff = data[0].pieces - data[-1].pieces

        if len(data) > 1 and pieces_diff == 0 and data[0].acquisition_price == data[-1].acquisition_price:
            acquisition_amount = data[0].acquisition_amount
        elif data[-1].price_currency == PERCENT:
            MessageBoxInfo(message=get_message(MESSAGE_TEXT, 'ACQUISITION_AMOUNT', bank.bank_name, bank.iban, name_, isin),
                           information=WARNING)
            acquisition_amount = data[0].acquisition_amount
        else:
            acquisition_amount = dec2.multiply(data[-1].pieces, data[-1].acquisition_price)

        data[-1].acquisition_amount = acquisition_amount
        self.update_holding_acquisition(bank.iban, isin, data[-1])
        return None

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

    def _statements(self, bank) -> list[dict]:
        """
        Store bank statements for a bank account in the STATEMENT table.

        Parameters
        ----------
        bank : Bank
            Bank object containing account info and download dialogs.

        Returns
        -------
        list[dict]
            List of statements inserted into the database.
        """
        max_entry_date = self.select_scalar(STATEMENT, f"MAX({DB_entry_date})", iban=bank.iban)
        bank.from_date = max_entry_date if max_entry_date else START_DATE_STATEMENTS
        bank.to_date = str(date.today())

        statements = bank.download_statements() if bank.scraper else bank.dialogs.statements(bank)

        if statements in START_DIALOG_FAILED or statements == []:
            return statements

        entry_date = None
        for statement in statements:
            if statement[DB_entry_date] != entry_date:
                entry_date = statement[DB_entry_date]
                counter = 0

            statement[DB_iban] = bank.iban
            statement[DB_counter] = counter

            # Skip if already exists
            if self.select_exists(STATEMENT, iban=statement[DB_iban], entry_date=statement[DB_entry_date], counter=counter):
                pass
            elif DB_bank_reference in statement and self.select_exists(STATEMENT, iban=statement[DB_iban], bank_reference=statement[DB_bank_reference]):
                pass
            else:
                if not statement.get(DB_purpose_wo_identifier):
                    statement[DB_purpose_wo_identifier] = statement[DB_purpose]
                self.execute_insert(STATEMENT, statement)

            counter += 1

        self.executor.execute('COMMIT;')

        if application_store.get(DB_ledger):
            transfer_statement_to_ledger(self, bank)

        return statements

    def select_total_amounts(self, period: tuple) -> list:
        """
        Return total balances for the given period.

        Combines:
        - HOLDING portfolio balances
        - STATEMENT closing balances
        - LEDGER balances for asset accounts without statements/holdings

        Parameters
        ----------
        period : tuple
            (from_date, to_date)

        Returns
        -------
        list
            [(iban/account, date, status, saldo), ...]
        """
        from_date, to_date = period

        # ------------------------------------------------------------
        # 1. Holding + Statement balances inside period
        # ------------------------------------------------------------
        total_amounts = self.select_cte(
            sql="""
                WITH total_amounts AS (
                    SELECT
                        iban,
                        price_date AS date,
                        ? AS status,
                        total_amount_portfolio AS saldo
                    FROM holding
                    WHERE price_date > ?
                      AND price_date <= ?

                    UNION ALL

                    SELECT
                        s.iban,
                        s.entry_date AS date,
                        s.closing_status AS status,
                        s.closing_balance AS saldo
                    FROM statement s
                    JOIN (
                        SELECT
                            iban,
                            entry_date,
                            MAX(counter) AS counter
                        FROM statement
                        WHERE entry_date > ?
                          AND entry_date <= ?
                        GROUP BY iban, entry_date
                    ) t
                    USING (iban, entry_date, counter)
                )
                SELECT iban, date, status, saldo
                FROM total_amounts
            """,
            vars_=(CREDIT, from_date, to_date, from_date, to_date),
            fields=("iban", "date", "status", "saldo")
        )

        total_amounts = self._remove_obsolete_iban_rows(total_amounts)

        # ------------------------------------------------------------
        # 2. Last statement balances before period
        # ------------------------------------------------------------
        total_amounts += self.select_cte(
            sql="""
                WITH last_statement AS (
                    SELECT
                        iban,
                        MAX(entry_date) AS entry_date
                    FROM statement
                    WHERE entry_date < ?
                    GROUP BY iban
                )
                SELECT
                    s.iban,
                    ? AS date,
                    s.closing_status AS status,
                    s.closing_balance AS saldo
                FROM statement s
                JOIN last_statement l
                  ON s.iban = l.iban
                 AND s.entry_date = l.entry_date
            """,
            vars_=(from_date, from_date),
            fields=("iban", "date", "status", "saldo")
        )

        # ------------------------------------------------------------
        # 3. Last holding balances before period
        # ------------------------------------------------------------
        total_amounts += self.select_cte(
            sql="""
                WITH last_holding AS (
                    SELECT
                        iban,
                        MAX(price_date) AS price_date
                    FROM holding
                    WHERE price_date <= ?
                    GROUP BY iban
                )
                SELECT
                    h.iban,
                    ? AS date,
                    ? AS status,
                    h.total_amount_portfolio AS saldo
                FROM holding h
                JOIN last_holding l
                  ON h.iban = l.iban
                 AND h.price_date = l.price_date
            """,
            vars_=(from_date, from_date, CREDIT),
            fields=("iban", "date", "status", "saldo")
        )

        # ------------------------------------------------------------
        # 4. Ledger-only asset accounts
        # ------------------------------------------------------------
        opening_balance_account = self.select_scalar(
            LEDGER_COA,
            DB_account,
            opening_balance_account=True
        )

        if not opening_balance_account:
            MessageBoxInfo(
                message=get_message(MESSAGE_TEXT, 'OPENING_ACCOUNT_MISSED')
            )
            return total_amounts

        asset_accounts = self.select_table(
            LEDGER_COA,
            [DB_account, DB_name, DB_asset_accounting],
            asset_accounting=True,
            result_dict=True,
            order=DB_account,
            download=False
        )

        for account_dict in asset_accounts:
            ledger_rows = self.select_ledger_balance(
                account_dict,
                opening_balance_account,
                period
            )
            if ledger_rows:
                total_amounts += ledger_rows
            else:
                MessageBoxInfo(
                    message=get_message(
                        MESSAGE_TEXT,
                        'OPENING_LEDGER_MISSED',
                        period,
                        account_dict[DB_name]
                    ),
                    info_storage=Informations.BANKDATA_INFORMATIONS,
                )

        return total_amounts


class MariaDBImporter:
    """
    Class to import bank identifiers, servers, transactions, and prices
    into MariaDB tables in a structured, safe way.
    """

    def import_bankidentifier(self, filename: str) -> None:
        """
        Import CSV file into the BANKIDENTIFIER table.

        Parameters
        ----------
        filename : str
            Path to the CSV file to import.

        Notes
        -----
        CSV download: Bundesbank - Bankleitzahlen
        https://www.bundesbank.de/de/aufgaben/unbarer-zahlungsverkehr/serviceangebot/bankleitzahlen/download-bankleitzahlen-602592
        """
        # Delete existing entries
        self.executor.execute(f'DELETE FROM {BANKIDENTIFIER}')

        # Load CSV
        sql = (
            f"LOAD DATA LOW_PRIORITY LOCAL INFILE '{filename}' "
            f"REPLACE INTO TABLE {BANKIDENTIFIER} "
            "CHARACTER SET latin1 "
            "FIELDS TERMINATED BY ';' OPTIONALLY ENCLOSED BY '\"' ESCAPED BY '\"' "
            "LINES TERMINATED BY '\r\n' IGNORE 1 LINES "
            "(`code`, `payment_provider`, `payment_provider_name`, `postal_code`, "
            "`location`, `name`, `pan`, `bic`, `check_digit_calculation`, "
            "`record_number`, `change_indicator`, `code_deletion`, `follow_code`);"
        )
        self.executor.execute(sql)

        # Delete unwanted payment providers
        self.executor.execute(f"DELETE FROM {BANKIDENTIFIER} WHERE payment_provider='2'")

    def import_server(self, filename: str) -> None:
        """
        Import CSV file into the SERVER table.

        Parameters
        ----------
        filename : str
            Path to the CSV file containing server data.

        Notes
        -----
        Only columns 'code' and 'server' are imported from the CSV (28 columns total).
        Registration: https://www.hbci-zka.de/register/prod_register.htm
        """
        columns = 28
        csv_columns = [f'@VAR{x}' for x in range(columns)]
        csv_columns[1] = 'code'
        csv_columns[24] = 'server'
        csv_columns_str = ', '.join(csv_columns)

        self.executor.execute(f'DELETE FROM {SERVER}')

        load_sql = (
            f"LOAD DATA LOW_PRIORITY LOCAL INFILE '{filename}' "
            f"REPLACE INTO TABLE {SERVER} "
            "CHARACTER SET latin1 "
            "FIELDS TERMINATED BY ';' OPTIONALLY ENCLOSED BY '\"' ESCAPED BY '\"' "
            f"LINES TERMINATED BY '\\r\\n' IGNORE 1 LINES ({csv_columns_str});"
        )
        self.executor.execute(load_sql)

        # Delete placeholder servers
        self.executor.execute(f"DELETE FROM {SERVER} WHERE server='\r'")

        # Insert additional known servers
        for code, (server, *_) in SCRAPER_BANKDATA.items():
            self.executor.execute(f"INSERT INTO {SERVER} SET code=?, server=?", (code, server))

    def import_transaction(self, iban: str, filename: str) -> None:
        """
        Import CSV file into TRANSACTION table.

        Parameters
        ----------
        iban : str
            IBAN of the account for which transactions belong.
        filename : str
            CSV file containing transactions.
        """
        sql = (
            f"LOAD DATA LOW_PRIORITY LOCAL INFILE '{filename}' "
            f"REPLACE INTO TABLE {TRANSACTION} "
            "CHARACTER SET latin1 "
            "FIELDS TERMINATED BY ';' OPTIONALLY ENCLOSED BY '\"' ESCAPED BY '\"' "
            "LINES TERMINATED BY '\r\n' IGNORE 1 LINES "
            f"(price_date, isin_code, counter, pieces, price) "
            f"SET iban='{iban}', transaction_type='{TRANSACTION_RECEIPT}', "
            "price_currency='EUR', amount_currency='EUR', posted_amount=price*pieces, "
            f"origin='{filename[-50:]}';"
        )
        self.executor.execute(sql)

        # Correct negative values
        update_sql = (
            f"UPDATE {TRANSACTION} "
            "SET transaction_type=?, counter=ABS(counter), pieces=ABS(pieces), posted_amount=ABS(posted_amount) "
            "WHERE pieces < 0"
        )
        self.executor.execute(update_sql, (TRANSACTION_DELIVERY,))

    def import_prices(self, title: str, dataframe: DataFrame) -> bool:
        """
        Insert or append price data into PRICES table.

        Parameters
        ----------
        title : str
            Title for logging or error handling.
        dataframe : pandas.DataFrame
            DataFrame containing prices to insert.

        Returns
        -------
        bool
            True if insertion succeeded, False if an error occurred.

        Notes
        -----
        Index is set to ['symbol', 'price_date'] for uniqueness.
        """
        try:
            dataframe.to_sql(PRICES, con=self.engine, if_exists='append', index_label=['symbol', 'price_date'])
            self.executor.execute('COMMIT')
            return True
        except sqlalchemy.exc.SQLAlchemyError as info:
            DatabaseErrorHandler.handle_error(title, Informations.PRICES_INFORMATIONS, info)
            return False


class MariaDB(
    MariaDBInitializer,
    MariaDBTables,
    MariaDBLedger,
    MariaDBHolding,
    MariaDBStatements,
    MariaDBTransactions,
    MariaDBPrices,
    MariaDBShelves,
    MariaDBSelection,
    MariaDBApplication,
    MariaDBServer,
    MariaDBServices,
    MariaDBImporter
):
    """
    Singleton access layer for MariaDB.

    Combines all MariaDB modules (Ledger, Transactions, Prices, Shelves, Selection,
    Application, Server, Services, Importer, Holdings, Statements, Tables, Initializer)
    into a single unified interface.

    Attributes
    ----------
    _instance : MariaDB | None
        Singleton instance.
    DATABASES : list
        List of available databases (currently empty).
    """
    _instance = None
    DATABASES: list = []

    def __new__(cls, *args, **kwargs) -> "MariaDB":
        """
        Singleton implementation: ensures only one instance exists.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, user: str = "root", password: str = "FINTS",
                 database: str = PRODUCTIVE_DATABASE_NAME):
        """
        Initialize the MariaDB connection once.

        Parameters
        ----------
        user : str
            Database username.
        password : str
            Database password.
        database : str
            Default database name to connect to.
        """
        if getattr(self, "_initialized", False):
            return  # Already initialized

        super().__init__(user=user, password=password, database=database)
        self._initialized = True

