"""
Created on 09.12.2019
__updated__ = "2025-07-17"
Author: Wolfang Kramer
"""

from PIL import ImageTk

from mariadb import connect, Error
from tkinter import Tk, TclError, Canvas, StringVar, GROOVE    
from tkinter.ttk import Style, Entry, Label, Combobox, Button
from banking.declarations import (
    MESSAGE_TITLE, MESSAGE_TEXT, WARNING,
    MARIADB_NAME,
    MARIADB_USER,
    MARIADB_PASSWORD,
    MARIADB_HOST   
)
from banking.declarations_mariadb import APPLICATION, DB_directory, DB_logging, CREATE_APPLICATION
from banking.mariadb import MariaDB
from banking.formbuilts import WM_DELETE_WINDOW, BUTTON_OK, END
from banking.messagebox import MessageBoxInfo, MessageBoxAsk


class Connect(object):
    """
    Connect MariaDB
    Create database if not exist
    """

    def __init__(self, title=MESSAGE_TITLE):


        
        self.directory = ''
        self.logging = False
        self.connected = False
        self.window = Tk()
        self.window.title(title)
        self.window.geometry('600x450+1+1')
        self.window.resizable(0, 0)
        self.canvas = Canvas(self.window, width=600, height=400)
        self.canvas.pack(fill="both", expand=True)            
        try:
            self.bg_photo = ImageTk.PhotoImage(file="background.gif")
            self.canvas.create_image(0, 0, image=self.bg_photo, anchor="nw")
        except Exception as e:
            print(MESSAGE_TEXT['CONNECT_IMAGE_ERROR'].format(e))

        self.user = 'root'
        self.password = 'FINTS'
        self.host = 'localhost'
        self._create_connect_form()            
        self.footer = StringVar()
        self.message_widget = Label(self.window,
                                    textvariable=self.footer, foreground='RED', justify='center')
        self.footer.set('')
        self.message_widget.pack(side='bottom', fill='x')
        self.load_timer = None
        self.window.protocol(WM_DELETE_WINDOW, self._wm_deletion_window)
        self.window.mainloop()

    def destroy_widget(self, widget):
        """
        exit and destroys windows or
        destroys widget  and rest of root window will be left
        don't stop the tcl/tk interpreter
        """
        try:
            widget.destroy()
        except TclError:
            pass

    def _wm_deletion_window(self):

        self.window.quit()

    def _def_styles(self):

        style = Style()
        style.theme_use(style.theme_names()[0])
        style.configure('TLabel', font=('Arial', 8, 'bold'))
        style.configure('OPT.TLabel', font=(
            'Arial', 8, 'bold'), foreground='Grey')
        style.configure('HDR.TLabel', font=(
            'Courier', 12, 'bold'), foreground='Grey')
        style.configure('TButton', font=('Arial', 8, 'bold'), relief=GROOVE,
                        highlightcolor='blue', highlightthickness=5, shiftrelief=3)
        style.configure('TText', font=('Courier', 8))

    def _create_connect_form(self):

        self.user_entry = self._add_labeled_entry(MARIADB_USER, self.user, 40)
        self.user_entry.focus_set()
        self.user_entry.bind("<KeyRelease>", self._schedule_db_load)

        self.password_entry = self._add_labeled_entry(MARIADB_PASSWORD, self.password, 80, show="*")
        self.password_entry.bind("<KeyRelease>", self._schedule_db_load)

        self.host_entry = self._add_labeled_entry(MARIADB_HOST, self.host, 120)

        self.db_label = Label(self.window, text=MARIADB_NAME)
        self.db_combo = Combobox(self.window, state="normal", width=30, )
        self.db_combo.bind("<<ComboboxSelected>>", self._database_selected)
        self.canvas.create_window(150, 160, window=self.db_label, anchor="e")
        self.canvas.create_window(160, 160, window=self.db_combo, anchor="w")

       
        self.connect_button = Button(self.window, text=BUTTON_OK, command=self._connect_to_db)
        self.canvas.create_window(300, 240, window=self.connect_button)        

    def _add_labeled_entry(self, label_text, field_value, length, show=None):
        label = Label(self.window, text=label_text)
        entry = Entry(self.window, show=show) if show else Entry(self.window)
        entry.delete(0, END)
        entry.insert(0, field_value)
        entry.bind("<FocusIn>", self._schedule_db_load)
        self.canvas.create_window(150, length, window=label, anchor="e")
        self.canvas.create_window(160, length, window=entry, anchor="w")
        return entry

    def _schedule_db_load(self, event=None):
        if self.load_timer:
            self.window.after_cancel(self.load_timer)
        self.load_timer = self.window.after(500, self._load_databases)

    def _load_databases(self):
        self.user = self.user_entry.get().strip()
        self.password = self.password_entry.get().strip()
        self.host = self.host_entry.get().strip()

        if not self.user or not self.password:
            return

        try:
            conn = connect(host=self.host, user=self.user, password=self.password)
            cursor = conn.cursor()
            cursor.execute("SHOW DATABASES")
            self.databases = [db[0] for db in cursor.fetchall()]
            mariadb_databases = ['information_schema', 'mysql', 'performance_schema', 'sys']
            self.databases[:] = [x for x in self.databases if x not in set(mariadb_databases)]            
            self.db_combo['values'] = self.databases
            if self.databases:
                self.db_combo.set(self.databases[0])
                self._database_selected()
        except Error as err:
            self.db_combo['values'] = []
            self.db_combo.set("")
            self.footer.set(MESSAGE_TEXT['CONNECT_MARIADB_ERROR'].format(err))

    def _database_selected(self, event=None):
        selected_db = self.db_combo.get()
        self.footer.set(MESSAGE_TEXT['CONNECT_MARIADB'].format(selected_db))

    def _connect_to_db(self):
        self.database = self.db_combo.get().strip()
        self.mariadb = MariaDB(self.user, self.password, self.database)
        self.connected = True
        result = self.mariadb.select_table(APPLICATION, [DB_directory, DB_logging], result_dict=True, row_id=1)
        if result:
            self.logging = result[0][DB_logging]
            self.directory = result[0][DB_directory]
        else:
            self.logging = False    
        self.window.destroy()
  
       
  
                     




