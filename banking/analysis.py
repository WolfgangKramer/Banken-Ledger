'''
Created on 17.07.2025

@author: Wolfg
'''
'''
https://technical-analysis-library-in-python.readthedocs.io/en/latest/ta.html


'''


from pandas import DataFrame, concat
import numpy as np
from ta.momentum import RSIIndicator
from banking.formbuilts import BuiltPandasBox, NUMERIC
from banking.mariadb import MariaDB
from banking.declarations_mariadb import PRICES, DB_price_date, DB_close
MariaDBuser = 'root'
MariaDBpassword = 'FINTS'
MariaDBname = 'test'
mariadb = MariaDB(MariaDBuser, MariaDBpassword, MariaDBname)


class RSI(object):
    '''
    Relative Strength Indicator
    RSI: https://technical-analysis-library-in-python.readthedocs.io/en/latest/ta.html
    Provide short-term  buy and sell signals.
    The average gain or loss used in this calculation is the average percentage gain or loss
    during a look-back period. 

    symbol    > ticker symbol
    close     > column_name of prices
    period    > days look-back period
    '''

    def __init__(self, mariadb, symbol, close, period=14):

        self.mariadb = mariadb
        self.symbol = symbol
        self.close = close
        self.period = period
        self.rsi_signals()

    def rsi_signals(self):

        columns = [DB_price_date, self.close]
        data = self.mariadb.select_table(PRICES, columns, symbol=self.symbol)
        df = DataFrame(data=data, columns=columns)
        # Calculate RSI
        rsi = RSIIndicator(close=df[self.close], window=self.period)
        df['RSI'] = rsi.rsi()
        # Mark Signal condition
        df['Signal'] = np.where(df['RSI'] > 70, 'PUT', np.where(
            df['RSI'] < 30, 'CALL', ''))
        # Find first row with 'PUT' o 'CALL'
        df_gain = df[df['Signal'].isin(['PUT', 'CALL'])].head(1)
        # Loop through the DataFrame starting from the given row
        while True:
            # Find the next row_number with 'CALL' or 'PUT'
            if df_gain.iloc[-1]['Signal'] == 'PUT':
                # Filter the DataFrame starting from the given Date
                filtered_df = df[df[DB_price_date] >
                                 df_gain.iloc[-1][DB_price_date]]
                if not filtered_df[filtered_df['Signal'] == 'CALL'].empty:
                    # Find the first occurrence
                    first_occurrence = filtered_df[filtered_df['Signal']
                                                   == 'CALL'].iloc[0]
                    row_to_append = first_occurrence
                    df_gain = concat(
                        [df_gain, row_to_append.to_frame().T], ignore_index=True)
                else:
                    break
            else:
                # Filter the DataFrame starting from the given Date
                filtered_df = df[df[DB_price_date] >
                                 df_gain.iloc[-1][DB_price_date]]

                if not filtered_df[filtered_df['Signal'] == 'PUT'].empty:
                    # Find the first occurrence
                    first_occurrence = filtered_df[filtered_df['Signal']
                                                   == 'PUT'].iloc[0]
                    row_to_append = first_occurrence
                    df_gain = concat(
                        [df_gain, row_to_append.to_frame().T], ignore_index=True)
                else:
                    break

        df_gain['Profit'] = df_gain[DB_close].diff().shift(
            periods=-1, fill_value=0)
        df_gain['Profit'] = df_gain[['Profit', 'Signal']].apply(
            lambda x: -x[0] if x[1] == 'PUT' else x[0], axis=1)
        title = ' '.join(['RSI with Period ', str(self.period)])
        BuiltPandasBox(title=title, dataframe=df_gain,
                       mode=NUMERIC, dataframe_sum=['Profit'])
        title = ' '.join(['RSI with Period ', str(self.period)])
        BuiltPandasBox(title=title, dataframe=df,
                       mode=NUMERIC)

        BuiltPandasBox(title='RSI', dataframe=df, mode=NUMERIC)
