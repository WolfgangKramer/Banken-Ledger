"""
Created on 13.09.2019
__updated__ = "2024-12-26"
@author: Wolfgang Kramer
"""
import logging

from banking.executing import BankenLedger
from banking.declarations import WM_DELETE_WINDOW
from banking.connect import Connect

connect = Connect()
if connect.connected:
    if connect.logging:
        logging_filename = ''.join([connect.directory, '\\logging.txt'])
        logging.basicConfig(filename=logging_filename, level=logging.DEBUG)
    while True:
        executing = BankenLedger(connect.user, connect.password, connect.database, connect.host)
        if executing.button_state == WM_DELETE_WINDOW:
            break
