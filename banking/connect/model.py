'''
Created on 02.01.2026

@author: Wolfg
'''
# banking/connect/model.py
from dataclasses import dataclass


@dataclass
class ConnectionResult:
    user: str
    password: str
    host: str
    database: str
    connected: bool
    logging: bool = False
    directory: str = ""
