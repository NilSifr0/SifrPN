import logging.config
import tkinter.filedialog as fd
import tkinter.font as tk_font
from datetime import datetime
from pathlib import Path

import ttkbootstrap as ttk
import yaml
from tktooltip import ToolTip
from ttkbootstrap.scrolled import ScrolledText

import src.utilities as utilities
from src.decryptor import Decryptor
from src.encryptor_ui import CustomToastNotification

config_path = Path(__file__).parent.parent / "configs" / "logging_config.yaml"

with open(config_path, "r") as yf:
    config = yaml.safe_load(yf)
    logging.config.dictConfig(config)

logger = logging.getLogger(__name__)

IMG_PATH = Path(__file__).parent.parent / "assets"


class DecryptUI(ttk.Frame):
    def __init__(self, parent: ttk.Notebook):
        super().__init__(parent, padding=(5, 5))
        self.pack(fill="both", expand=1)

        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=999)
        self.rowconfigure(2, weight=1)
        self.columnconfigure(0, weight=1)

        self.input_manager = InputManager(self)


class InputManager(ttk.Frame):
    def __init__(self, master: ttk.Frame):
        super().__init__(master)
        self.grid(row=0, column=0, sticky="nsew")

        for _ in range(3):
            self.rowconfigure(_, weight=1)
        for _ in range(2):
            self.columnconfigure(_, weight=1, uniform="col_group")

        # font styles
        self.md_font = tk_font.Font(family="Inter Bold", size=14)
        self.sm_font = tk_font.Font(family="Inter Regular", size=12)

        # icons
        self.icons = {
            "delete": ttk.PhotoImage(file=IMG_PATH / "delete.png"),
            "unlock": ttk.PhotoImage(file=IMG_PATH / "unlock.png"),
            "clipboard": ttk.PhotoImage(file=IMG_PATH / "clipboard.png"),
            "copy": ttk.PhotoImage(file=IMG_PATH / "copy.png"),
            "trash": ttk.PhotoImage(file=IMG_PATH / "trash.png"),
        }

        # class instances
        self.custom_toast_notification = CustomToastNotification(master)
        self.submission_manager = SubmissionManager()
        self.output_display = OutputDisplay(master)
        self.button_set = ButtonSet(master, reset_cb=self.reset_instance)

        # variables
        self.upload_file_name = ""
        self.paste_popup = None

        self.input_container_child = ttk.Frame(master=self)
        self.input_container_child.grid(row=0, column=0, columnspan=2, sticky="nsew")

        self.input_container_child.rowconfigure(0, weight=1)
        self.input_container_child.columnconfigure(0, weight=1)
        self.input_container_child.columnconfigure(1, weight=999)

        self.input_container_label = ttk.Label(
            master=self.input_container_child,
            font=self.sm_font,
            text="UPLOAD encrypted key & token images OR PASTE their text form.",
        )
        self.input_container_label.grid(
            row=0,
            column=0,
            sticky="sw",
            pady=(5, 10),
        )

        self.paste_button = ttk.Button(
            master=self.input_container_child,
            image=self.icons["clipboard"],
            bootstyle="info-outline",
            command=self._paste,
            padding=2,
            takefocus=0,
        )
        self.paste_button.grid(
            row=0,
            column=1,
            sticky="w",
        )

        self.upload_key = UploadManager(
            master=self,
            col=0,
            upload_type="KEY",
            on_validity_change=self._update_submit_state,
        )
        self.upload_token = UploadManager(
            master=self,
            col=1,
            upload_type="CIPHER",
            on_validity_change=self._update_submit_state,
        )

        self.submit_button = ttk.Button(
            master=self,
            text="DECRYPT",
            command=self._on_submit,
            image=self.icons["unlock"],
            compound="left",
            width=10,
            state="disabled",
        )
        self.submit_button.grid(row=2, column=0, columnspan=2, pady=(4, 4))
        self._update_submit_state()

    def _paste(self):
        remove_uli_cb = (
            self.upload_key.on_remove_file,
            self.upload_token.on_remove_file,
        )
        self.paste_popup = PastePopup(
            remove_uli_cb,
            self.output_display.display,
            self.button_set.display_buttons,
            self.button_set.file_content,
        )
        self.wait_window(self.paste_popup)

    def _update_submit_state(self):
        if self.upload_key.valid_state and self.upload_token.valid_state:
            self.submit_button.config(state="normal")
        else:
            self.submit_button.config(state="disabled")

    def _on_submit(self):
        current_key_path = self.upload_key.upload_file_path
        current_token_path = self.upload_token.upload_file_path

        current_submission = (current_key_path, current_token_path)
        type(current_submission)

        if self.submission_manager.is_stale(current_submission):
            logger.info("Submission ignored: stale inputs.")
            return

        self.submission_manager.update_submission(current_submission)

        key_bytes = self.upload_key.byte_string
        token_bytes = self.upload_token.byte_string

        # pass the text form to decryptor
        input_decryptor = InputDecryptor()
        result = input_decryptor.execute_decrypt(key_bytes, token_bytes)
        # display result
        self.output_display.display(result)
        self.button_set.display_buttons()
        # pass result object to button_set for saving
        self.button_set.file_content = result

    def reset_instance(self):
        def clear_children(frame: ttk.Frame):
            for _ in frame.winfo_children():
                _.grid_remove()

        self.upload_key.on_remove_file()
        self.upload_token.on_remove_file()
        self.output_display.result_container.text.delete("1.0", "end")
        clear_children(self.output_display)
        clear_children(self.button_set)


class UploadManager(ttk.Frame):
    def __init__(
        self, master: ttk.Frame, col: int, upload_type: str, on_validity_change=None
    ):
        super().__init__(master)
        self.grid(row=1, column=col, sticky="nsew", pady=(0, 5))

        # font styles
        self.sm_font = tk_font.Font(family="Inter Regular", size=12)
        self.mm_font = tk_font.Font(family="Inter Italic", size=11)

        # icons
        self.icons = {
            "upload": ttk.PhotoImage(file=IMG_PATH / "upload.png"),
            "check": ttk.PhotoImage(file=IMG_PATH / "check.png"),
            "error": ttk.PhotoImage(file=IMG_PATH / "error.png"),
            "delete": ttk.PhotoImage(file=IMG_PATH / "delete.png"),
        }

        # CLASS INSTANCES
        self.validator = utilities.Validator()

        # variables
        self.upload_type = upload_type
        self.upload_file_path: str = ""
        self.valid_state = False
        self._byte_string = ""
        self.on_validity_change = on_validity_change

        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=999)

        self.upload_label = ttk.Label(
            master=self,
            text=f"{self.upload_type}\t→ ",
            font=self.sm_font,
        )
        self.upload_label.grid(row=0, column=0, sticky="sw")

        self.upload_button = ttk.Button(
            master=self,
            image=self.icons["upload"],
            command=self.on_upload,
            bootstyle="success-outline",
            padding=(2, 0),
        )
        self.upload_button.grid(row=0, column=1, sticky="w", padx=(5, 10))

        # update childe border hack
        self.bottom_border = ttk.Frame(
            master=self,
            relief="groove",
            border=1,
        )
        self.bottom_border.grid(row=1, column=2, sticky="ew", padx=(0, 65))

        self.upload_child = ttk.Frame(master=self)

        self.upload_child.rowconfigure(0, weight=1)
        for _ in range(3):
            self.upload_child.columnconfigure(_, weight=1)

        self.upload_file_name = ttk.Label(
            master=self.upload_child,
            font=self.mm_font,
            foreground="#ba68c8",
        )
        self.upload_file_name.grid(row=0, column=0, sticky="sw")

        self.upload_validity_label = ttk.Label(
            master=self.upload_child,
        )
        self.upload_validity_label.grid(row=0, column=1, sticky="e", padx=(10, 5))
        self.uvl_tt = ToolTip(self.upload_validity_label, msg="")

        self.upload_remove_key_file = ttk.Button(
            master=self.upload_child,
            image=self.icons["delete"],
            command=self.on_remove_file,
            bootstyle="danger-outline",
            padding=1,
        )
        self.upload_remove_key_file.grid(row=0, column=2, sticky="w")

    def on_upload(self):
        self.upload_file_path = fd.askopenfilename(
            title=f"Select {self.upload_type} File",
            filetypes=[("PNG Images", ("*.png"))],
        )

        if not self.upload_file_path:
            return

        self._validate_image(self.upload_file_path)

    def _validate_image(self, upload_path: str):
        def format_file_name(file_name: str):
            limit_len = 40
            total_len = len(file_name)
            if total_len < limit_len:
                return file_name

            start_part = file_name[:limit_len]
            end_part = file_name[total_len - 4 :]
            return f"{start_part}...{end_part}"

        prev_state = self.valid_state
        container_type = self.upload_type
        state, byte_string = self.validator.validate_upload(upload_path, container_type)

        if state:
            self.valid_state = True
            self._byte_string = byte_string
            self.upload_validity_label.config(
                image=self.icons["check"],
                bootstyle="success",
            )
            self.uvl_tt.msg = f"Valid {self.upload_type} image."
        else:
            self.valid_state = False
            self._byte_string = ""
            self.upload_validity_label.config(
                image=self.icons["error"],
                bootstyle="danger",
            )
            self.uvl_tt.msg = f"Invalid {self.upload_type} image."

        self.upload_file_name.config(
            text=format_file_name(Path(upload_path).name),
        )

        self.upload_child.grid(row=0, column=2, sticky="w")

        if self.on_validity_change and self.valid_state != prev_state:
            self.on_validity_change()

    def on_remove_file(self):
        self.valid_state = False
        self.on_validity_change()
        self.upload_file_path = ""
        self.upload_child.grid_remove()

    @property
    def byte_string(self):
        return self._byte_string


class PastePopup(ttk.Toplevel):
    def __init__(
        self, remove_uli_cb, output_display_cb, button_display_cb, file_content
    ):
        super().__init__(
            minsize=(980, 1),
            resizable=(False, False),
            overrideredirect=True,
        )
        self.config(
            highlightthickness=2,
            highlightbackground="#555555",
            relief="raised",
        )
        self.grab_set()

        # POSITION
        self.x = (self.winfo_screenwidth() // 2) - (980 // 2)
        self.y = (self.winfo_screenheight() // 2) - (590 // 2)
        offset = 8
        self.geometry(f"+{self.x + offset}+{self.y - offset}")

        for _ in range(4):
            self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=999)
        self.columnconfigure(1, weight=1)

        # ICONS
        self.icons = {
            "close": ttk.PhotoImage(file=IMG_PATH / "close.png"),
            "unlock": ttk.PhotoImage(file=IMG_PATH / "unlock.png"),
        }

        # VARIABLES
        self.remove_uli_cb = remove_uli_cb
        self.out_display_cb = output_display_cb
        self.button_show_cb = button_display_cb
        self.file_content = file_content

        self.paste_label = ttk.Label(
            master=self,
            text="PASTE KEY & CIPHER STRINGS",
            font=("Inter Bold", 14),
        )
        self.paste_label.grid(
            row=0, column=0, sticky="nw", padx=(10, 10), pady=(12, 10)
        )

        self.close_button = ttk.Button(
            master=self,
            image=self.icons["close"],
            command=lambda: self.destroy(),
            bootstyle="primary-outline",
            padding=0,
        )
        self.close_button.grid(
            row=0, column=1, sticky="ne", padx=(10, 10), pady=(12, 10)
        )

        # DISPLAY PASTE BOX
        self.key_ib = InputBox(
            self,
            row=1,
            input_type="KEY",
            entry_height=1,
            on_validity_change=self._update_submit_state,
        )
        self.cipher_ib = InputBox(
            self,
            row=2,
            input_type="CIPHER",
            entry_height=8,
            on_validity_change=self._update_submit_state,
        )

        self.submit_button = ttk.Button(
            master=self,
            text="DECRYPT",
            command=self._on_submit,
            image=self.icons["unlock"],
            compound="left",
            state="disabled",
        )
        self.submit_button.grid(row=3, column=0, columnspan=2, pady=(0, 12))
        self._update_submit_state()

    def _update_submit_state(self):
        if self.key_ib.valid_state and self.cipher_ib.valid_state:
            self.submit_button.config(state="normal")
        else:
            self.submit_button.config(state="disabled")

    def _on_submit(self):
        input_decryptor = InputDecryptor()
        result = input_decryptor.execute_decrypt(
            self.key_ib.clean_string,
            self.cipher_ib.clean_string,
        )
        # pass this result to output box
        # self destruct after
        self._show_result(result=result)
        self.after(10, lambda: self.destroy())

    def _show_result(self, result):
        for i in self.remove_uli_cb:
            i()
        self.out_display_cb(result)
        self.button_show_cb()
        self.file_content = result


class InputBox(ttk.Frame):
    def __init__(self, master, row, input_type, entry_height, on_validity_change=None):
        super().__init__(master)
        self.grid(
            row=row,
            column=0,
            columnspan=2,
            sticky="nsew",
            padx=(10, 10),
            pady=(10, 10),
        )

        # FONTS
        self.md_font = tk_font.Font(family="Inter Display Bold", size=13)
        self.sm_font = tk_font.Font(family="JetBrainsMono NF Regular", size=11)

        # ICONS
        self.icons = {
            "paste": ttk.PhotoImage(file=IMG_PATH / "paste.png"),
            "check_sm": ttk.PhotoImage(file=IMG_PATH / "check_sm.png"),
            "error_sm": ttk.PhotoImage(file=IMG_PATH / "error_sm.png"),
        }

        # CLASS INSTANCES
        self.validator = utilities.Validator()

        # INSTANCE VARIABLES
        self.input_type = input_type
        self.on_validity_change = on_validity_change
        self.old_input = ""
        self.valid_state = False

        for _ in range(2):
            self.rowconfigure(_, weight=1)
        self.columnconfigure(0, weight=999)
        self.columnconfigure(1, weight=1)

        self.input_label_container = ttk.Frame(self)
        self.input_label_container.grid(row=0, column=0, sticky="ew")

        self.input_label_container.rowconfigure(0, weight=1)
        self.input_label_container.columnconfigure(0, weight=1)
        self.input_label_container.columnconfigure(1, weight=999)

        self.input_label = ttk.Label(
            master=self.input_label_container,
            font=self.md_font,
            text=f"{self.input_type}",
        )
        self.input_label.grid(row=0, column=0, sticky="sw")

        self.validity_label = ttk.Label(
            master=self.input_label_container,
        )
        self.validity_label.grid(row=0, column=1, sticky="w")
        self.validity_tt = ToolTip(self.validity_label, msg="")

        self.input_entry = ScrolledText(
            master=self,
            height=entry_height,
            wrap="word",
            undo=True,
            font=self.sm_font,
            bootstyle="round dark",
        )
        self.input_entry.set_autohide(True)
        self.input_entry.grid(row=1, column=0, sticky="nsew")
        self.input_entry.text.config(state="disabled")

        self.paste_button = ttk.Button(
            master=self,
            image=self.icons["paste"],
            command=self._on_paste,
            padding=2,
            bootstyle="dark-outline",
        )
        self.paste_button.grid(
            row=1,
            column=1,
            sticky="ne",
            padx=(0, 2),
            pady=(2, 0),
        )

    def _on_paste(self):
        try:
            input_string = self.clipboard_get()
        except Exception:
            logger.info("Clipboard empty.")
            return

        if not input_string:
            return

        if input_string == self.old_input:
            return

        if len(input_string) > 792:
            self.input_entry.set_autohide(False)
        else:
            self.input_entry.set_autohide(True)

        self.input_entry.text.config(state="normal")
        self.input_entry.text.delete("1.0", "end")
        self.input_entry.insert(ttk.INSERT, input_string)
        self.input_entry.text.config(state="disabled")
        self.old_input = input_string

        self._update_label(input_string)

    def _update_label(self, string):
        prev_state = self.valid_state
        curr_state, self._clean_string = self.validator.validate_string(
            string,
            self.input_type,
        )
        if curr_state:
            self.valid_state = True
            self.validity_label.config(image=self.icons["check_sm"])
            self.validity_tt.msg = f"Valid {self.input_type} string."
        else:
            self.valid_state = False
            self.validity_label.config(image=self.icons["error_sm"])
            self.validity_tt.msg = f"Invalid {self.input_type} string."

        if self.on_validity_change and self.valid_state != prev_state:
            self.on_validity_change()

    @property
    def clean_string(self):
        return self._clean_string


class SubmissionManager:
    def __init__(self):
        self.previous_submission = None

    def is_stale(self, current_submission):
        """Checks if the current submission is the same as the previous one."""
        return self.previous_submission == current_submission

    def update_submission(self, current_submission):
        self.previous_submission = current_submission


class OutputDisplay(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.grid(row=1, column=0, sticky="nsew")

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.result_container = ScrolledText(
            master=self,
            height=25,
            wrap="word",
            undo=True,
            font=("JetBrainsMono NF Regular", 13),
            bootstyle="round dark",
        )
        self.result_container.set_autohide(True)

    def display(self, text: str):
        self.result_container.grid(row=0, column=0, sticky="nsew")
        self.result_container.text.delete("1.0", "end")
        self.result_container.insert(ttk.INSERT, text)
        if len(text) > 2500:
            self.result_container.set_autohide(False)
        else:
            self.result_container.set_autohide(True)


class ButtonSet(ttk.Frame):
    def __init__(self, master: ttk.Frame, reset_cb):
        super().__init__(master)
        self.grid(row=2, column=0, sticky="nsew", pady=(6, 2))
        self.reset_callback = reset_cb

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=999)

        # ICONS
        self.icons = {
            "save": ttk.PhotoImage(file=IMG_PATH / "save.png"),
            "trash": ttk.PhotoImage(file=IMG_PATH / "trash.png"),
        }

        # CLASS INSTANCES
        self.custom_toast_notification = CustomToastNotification(master)

        # VARIABLES
        self._file_content: str = ""

        # BUTTONS
        self.save_button = ttk.Button(
            master=self,
            image=self.icons["save"],
            command=self._on_save,
            padding=4,
            bootstyle="primary-outline",
        )

        ToolTip(self.save_button, msg="Save file.")

        self.clear_button = ttk.Button(
            master=self,
            image=self.icons["trash"],
            command=self._on_reset,
            padding=4,
            bootstyle="danger-outline",
        )

        ToolTip(self.clear_button, msg="Reset.")

    @property
    def file_content(self):
        return self._file_content

    @file_content.setter
    def file_content(self, new_value: str):
        self._file_content = new_value

    def _on_save(self):
        save_file_name_path: str = ""
        save_file_name_path = fd.asksaveasfilename(
            defaultextension=".txt",
            initialdir=Path.home() / "Documents" / "ciphers",
            initialfile=f"ciphertext-{datetime.now():%b%d-%H%M%S-%f}.txt",
            filetypes=[("Text Files", ("*.txt"))],
        )

        if not save_file_name_path:
            return

        utilities.ResultSaver(save_file_name_path).save_result(self._file_content)

        self.custom_toast_notification.show_toast("success", "Instance saved.")

    def _on_reset(self):
        self.reset_callback()
        self.custom_toast_notification.show_toast("info", "Instance cleared.")

    def display_buttons(self):
        # show only when save_state ready/true
        self.save_button.grid(row=0, column=0, sticky="sw", padx=(2, 12))
        self.clear_button.grid(row=0, column=1, sticky="sw")


class InputDecryptor:
    def __init__(self):
        self.decryptor = Decryptor()

    def execute_decrypt(self, key: str | bytes, token: str | bytes):
        result = self.decryptor.decrypt(key=key, token=token)
        return result.decode()


if __name__ == "__main__":
    pass
