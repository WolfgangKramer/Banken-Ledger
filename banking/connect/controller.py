'''
Created on 02.01.2026

@author: Wolfg
'''
# banking/connect/controller.py
from banking.connect.view import ConnectView
from banking.connect.model import ConnectionResult


class ConnectController:

    def run(self) -> ConnectionResult:
        view = ConnectView()
        view.show()
        return view.result
