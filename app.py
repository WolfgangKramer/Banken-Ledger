'''
Created on 02.01.2026

@author: Wolfg
'''
# banking/app.py
import logging

from banking.executing import BankenLedger
from banking.declarations import WM_DELETE_WINDOW
from banking.connect.controller import ConnectController


def configure_logging(directory: str):
    logging.basicConfig(
        filename=f"{directory}/logging.txt",
        level=logging.DEBUG
    )


def main():
    controller = ConnectController()
    result = controller.run()

    if not result.connected:
        return

    if result.logging:
        configure_logging(result.directory)

    while True:
        executing = BankenLedger(
            result.user,
            result.password,
            result.database,
            result.host
        )
        if executing.button_state == WM_DELETE_WINDOW:
            break


if __name__ == "__main__":
    main()
