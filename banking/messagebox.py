"""
Created on 28.01.2020
__updated__ = "2025-07-17"
@author: Wolfgang Kramer
"""

import inspect
import sys

from tkinter import (
    Tk, TclError, messagebox
    )

from banking.declarations import (
    Informations, ERROR, INFORMATION,
    MESSAGE_TEXT, MESSAGE_TITLE
    )
from banking.utils import exception_error
from banking.utils import (
    check_main_thread,
    bankdata_informations_append, prices_informations_append
    )


def extend_message_len(title, message):
    """
    returns possibly extended message
    """
    try:
        title_len = max(len(x) for x in list(title.splitlines()))
        message_len = max(len(x) for x in list(message.splitlines()))
        if title_len > message_len:
            return message + '\n' + ' ' * title_len
        else:
            return message
    except Exception:
        return message


def destroy_widget(widget):
    """
    exit and destroys windows or
    destroys widget  and rest of root window will be left
    don't stop the tcl/tk interpreter
    """
    try:
        widget.destroy()
    except TclError:
        pass


class MessageBoxInfo():
    """
    bank                  if true: store message in bankdata_informations_append
    information_storage   Instance of Class Informations gathering messages in ClassVar informations
    """

    def __init__(self, message=None, title=MESSAGE_TITLE, bank=False, information_storage=None, information=INFORMATION):

        if not check_main_thread() or information_storage:
            if information_storage == Informations.PRICES_INFORMATIONS:  # messages downloading prices threading
                prices_informations_append(information, message)
            else:
                if bank:  # messages downloading bank threading
                    bankdata_informations_append(information, message)
                else:
                    print(message)
        else:
            if information != INFORMATION:
                bankdata_informations_append(information, message)
            window = Tk()
            window.withdraw()
            message = extend_message_len(title, message)
            window.title(title)
            messagebox.showinfo(title=title, message=message,)
            destroy_widget(window)


class MessageBoxError():

    def __init__(self, message=None, title=MESSAGE_TITLE):
        print(message)
        try:
            if not check_main_thread:
                # its a banking Dialogue
                bankdata_informations_append(ERROR, message)
            else:
                window = Tk()
                window.withdraw()
                message = extend_message_len(title, message)
                window.title(title)
                messagebox.showerror(title=title, message=message)
                MessageBoxTermination()
        except Exception:
            
            exception_error(message=message)
            

class MessageBoxTermination(MessageBoxInfo):
    """
    bank                  Instance of Class InitBank gathering fints_codes in ClassVar
    information_storage   Instance of Class Informations gathering messages in ClassVar informations
    """

    def __init__(self, info='', bank=None):

        message = MESSAGE_TEXT['TERMINATION'] + ' '
        if info:
            message = message + '\n' + info
        for stack_item in inspect.stack()[2:]:
            filename = stack_item[1]
            line = stack_item[2]
            method = stack_item[3]
            message = (
                message + '\n' + filename + '\n' + 'LINE:   ' +
                str(line) + '   METHOD: ' + method
            )
        if not check_main_thread():
            # its a banking Dialogue
            message = ' '.join([bank.bank_name, bank.iban, message])
            bankdata_informations_append(ERROR, message)
        else:
            super().__init__(message=message, title=MESSAGE_TITLE, bank=bank)
            sys.exit()


class MessageBoxAsk():
    """
    returns True if answer is YES
    """

    def __init__(self, message=None, title=MESSAGE_TITLE):

        if not check_main_thread:
            # its a banking Dialogue
            bankdata_informations_append(ERROR, message)
        else:
            window = Tk()
            window.withdraw()
            window.title(title)
            self.result = messagebox.askyesno(
                title=title, message=message, default='no')
            destroy_widget(window)
