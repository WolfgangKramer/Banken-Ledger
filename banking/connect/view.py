'''
Created on 02.01.2026

@author: Wolfg
'''
from tkinter import (
    Tk, Canvas, StringVar, GROOVE, END
)
from tkinter.ttk import Style, Entry, Label, Combobox, Button
from PIL import ImageTk
from mariadb import connect, Error

from banking.declarations import (
    MARIADB_NAME, MARIADB_USER,
    MARIADB_PASSWORD, MARIADB_HOST,
    WM_DELETE_WINDOW, BUTTON_OK
)
from banking.declarations_mariadb import (
    APPLICATION, DB_directory, DB_logging
)
from banking.message_handler import  get_message, MESSAGE_TITLE, MESSAGE_TEXT
from banking.mariadb import MariaDB
from banking.connect.model import ConnectionResult


class ConnectView:

    def __init__(self, title=MESSAGE_TITLE):
        self.result = ConnectionResult(
            user="root",
            password="FINTS",
            host="localhost",
            database="",
            connected=False,
        )

        self.directory = ""
        self.logging = False
        self.load_timer = None

        self.window = Tk()
        self.window.title(title)
        self.window.geometry("600x450+1+1")
        self.window.resizable(0, 0)

        self.canvas = Canvas(self.window, width=600, height=400)
        self.canvas.pack(fill="both", expand=True)

        try:
            self.bg_photo = ImageTk.PhotoImage(file="background.gif")
            self.canvas.create_image(0, 0, image=self.bg_photo, anchor="nw")
        except Exception as e:
            print(get_message(MESSAGE_TEXT, "CONNECT_IMAGE_ERROR", e))

        self._build_ui()

        self.footer = StringVar(value="")
        self.message_widget = Label(
            self.window,
            textvariable=self.footer,
            foreground="RED",
            justify="center"
        )
        self.message_widget.pack(side="bottom", fill="x")

        self.window.protocol(WM_DELETE_WINDOW, self._on_close)

    def _build_ui(self):
        self._define_styles()

        self.user_entry = self._add_labeled_entry(
            MARIADB_USER, self.result.user, 40
        )
        self.user_entry.focus_set()
        self.user_entry.bind("<KeyRelease>", self._schedule_db_load)

        self.password_entry = self._add_labeled_entry(
            MARIADB_PASSWORD, self.result.password, 80, show="*"
        )
        self.password_entry.bind("<KeyRelease>", self._schedule_db_load)

        self.host_entry = self._add_labeled_entry(
            MARIADB_HOST, self.result.host, 120
        )

        self.db_label = Label(self.window, text=MARIADB_NAME)
        self.db_combo = Combobox(self.window, state="normal", width=30)
        self.db_combo.bind("<<ComboboxSelected>>", self._database_selected)

        self.canvas.create_window(150, 160, window=self.db_label, anchor="e")
        self.canvas.create_window(160, 160, window=self.db_combo, anchor="w")

        self.connect_button = Button(
            self.window,
            text=BUTTON_OK,
            command=self._connect_to_db
        )
        self.canvas.create_window(300, 240, window=self.connect_button)

    def _define_styles(self):
        style = Style()
        style.theme_use(style.theme_names()[0])
        style.configure("TLabel", font=("Arial", 8, "bold"))
        style.configure("OPT.TLabel", font=("Arial", 8, "bold"), foreground="Grey")
        style.configure("HDR.TLabel", font=("Courier", 12, "bold"), foreground="Grey")
        style.configure(
            "TButton",
            font=("Arial", 8, "bold"),
            relief=GROOVE,
            highlightcolor="blue",
            highlightthickness=5,
            shiftrelief=3,
        )
        style.configure("TText", font=("Courier", 8))

    def _add_labeled_entry(self, label_text, field_value, y, show=None):
        label = Label(self.window, text=label_text)
        entry = Entry(self.window, show=show) if show else Entry(self.window)
        entry.delete(0, END)
        entry.insert(0, field_value)
        entry.bind("<FocusIn>", self._schedule_db_load)

        self.canvas.create_window(150, y, window=label, anchor="e")
        self.canvas.create_window(160, y, window=entry, anchor="w")

        return entry

    def _schedule_db_load(self, event=None):
        if self.load_timer:
            self.window.after_cancel(self.load_timer)
        self.load_timer = self.window.after(500, self._load_databases)

    def _load_databases(self):
        self.result.user = self.user_entry.get().strip()
        self.result.password = self.password_entry.get().strip()
        self.result.host = self.host_entry.get().strip()

        if not self.result.user or not self.result.password:
            return

        try:
            conn = connect(
                host=self.result.host,
                user=self.result.user,
                password=self.result.password,
            )
            cursor = conn.cursor()
            cursor.execute("SHOW DATABASES")

            databases = [db[0] for db in cursor.fetchall()]
            system_dbs = {
                "information_schema",
                "mysql",
                "performance_schema",
                "sys",
            }
            databases = [db for db in databases if db not in system_dbs]

            self.db_combo["values"] = databases
            if databases:
                self.db_combo.set(databases[0])

        except Error:
            self.db_combo["values"] = []
            self.db_combo.set("")

    def _database_selected(self, event=None):
        self.result.database = self.db_combo.get()

    def _connect_to_db(self):
        self.result.database = self.db_combo.get()
        self.mariadb = MariaDB(
            self.result.user,
            self.result.password,
            self.result.database,
        )
        self.footer.set(get_message(MESSAGE_TEXT, "CONNECT_MARIADB", self.result.database))
        self.result.connected = True

        result = self.mariadb.select_table(
            APPLICATION,
            [DB_directory, DB_logging],
            result_dict=True,
            row_id=1,
        )

        if result:
            self.result.logging = result[0][DB_logging]
            self.result.directory = result[0][DB_directory]

        self.window.destroy()

    def _on_close(self):
        self.result.connected = False
        self.window.quit()

    def show(self):
        self.window.mainloop()
        return self.result
