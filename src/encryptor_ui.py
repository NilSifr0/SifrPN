import logging.config
import multiprocessing as mp
import tkinter.filedialog as fd
import tkinter.font as tk_font
from datetime import datetime
from pathlib import Path

import ttkbootstrap as ttk
import yaml
from PIL import Image, ImageTk
from tktooltip import ToolTip
from ttkbootstrap.scrolled import ScrolledText
from ttkbootstrap.style import Style
from ttkbootstrap.toast import ToastNotification

import src.utilities as utilities
from src.encryptor import Encryptor

config_path = Path(__file__).parent.parent / "configs" / "logging_config.yaml"

with open(config_path, "r") as yf:
    config = yaml.safe_load(yf)
    logging.config.dictConfig(config)

logger = logging.getLogger(__name__)

IMG_PATH = Path(__file__).parent.parent / "assets"


class EncryptUI(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=(5, 5))
        self.pack(fill="both", expand=1)

        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=999)
        self.rowconfigure(2, weight=1)
        self.columnconfigure(0, weight=1)

        self.input_manager = InputManager(self)


class InputManager(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.grid(row=0, column=0, sticky="nsew")

        for _ in range(3):
            self.rowconfigure(_, weight=1)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=999)

        # FONT STYLES
        self.md_font = tk_font.Font(family="Inter Bold", size=14)
        self.sm_font = tk_font.Font(family="Inter Regular", size=12)

        # ICONS
        self.icons = {
            "upload": ttk.PhotoImage(file=IMG_PATH / "upload.png"),
            "delete": ttk.PhotoImage(file=IMG_PATH / "delete.png"),
            "clear": ttk.PhotoImage(file=IMG_PATH / "clear.png"),
            "lock": ttk.PhotoImage(file=IMG_PATH / "lock.png"),
        }

        # CLASS INSTANCES
        self.custom_toast_notification = CustomToastNotification(master)
        self.input_encryptor = InputEncryptor()
        self.image_display = ImageDisplay(master)
        self.button_set = ButtonSet(master, reset_cb=self.reset_instance)

        # INSTANCE VARIABLES
        self.upload_file_path = ""
        self.upload_state = False
        self.input_string = ""
        self.old_input = ""

        self.key_bytes: bytes = b""
        self.token_bytes: bytes = b""

        self.save_ready_state = False

        self.input_label = ttk.Label(
            master=self,
            font=self.sm_font,
            text="Enter string to encrypt OR upload '.txt' file for extremely long inputs.",
        )
        self.input_label.grid(row=0, column=0, sticky="sw")

        self.upload_button = ttk.Button(
            master=self,
            image=self.icons["upload"],
            command=self.on_upload,
            bootstyle="success-outline",
            padding=(2, 0),
        )
        self.upload_button.grid(row=0, column=1, sticky="w", padx=(5, 0))

        self.upload_file_container = ttk.Frame(self)

        self.upload_file_container.rowconfigure(0, weight=1)
        self.upload_file_container.columnconfigure(0, weight=1)
        self.upload_file_container.columnconfigure(1, weight=999)

        self.upload_file = ttk.Label(
            master=self.upload_file_container,
            text="",
            font=("Inter Italic", 11),
            foreground="#ba68c8",
        )
        self.upload_file.grid(row=0, column=0, sticky="sw")

        self.remove_file_button = ttk.Button(
            master=self.upload_file_container,
            image=self.icons["delete"],
            command=self.on_remove_file,
            bootstyle="danger-outline",
            padding=1,
        )
        self.remove_file_button.grid(row=0, column=1, sticky="w")
        ToolTip(self.remove_file_button, msg="Remove.")

        self.input_entry = ScrolledText(
            master=self,
            height=4,
            wrap="word",
            undo=True,
            font=self.sm_font,
            bootstyle="round dark",
            autohide=True,
        )
        self.input_entry.grid(row=1, column=0, columnspan=3, sticky="nsew", pady=(5, 5))
        self.input_entry.text.bind("<KeyPress>", self.limit_entry)
        self.input_entry.text.bind("<KeyRelease>", self.limit_entry)
        self.input_entry.text.bind("<Control-v>", self.on_paste, add=True)

        self.clear_input_entry = ttk.Button(
            master=self,
            image=self.icons["clear"],
            command=self.on_clear_input,
            bootstyle="danger-outline",
            padding=0,
        )
        self.clear_input_entry.grid(row=2, column=0, sticky="w", padx=(3, 0))
        ToolTip(self.clear_input_entry, msg="Clear text.")

        self.character_limit_label = ttk.Label(
            master=self,
            text="0 / 15000",
        )
        self.character_limit_label.grid(row=2, column=2, sticky="ne")

        self.submit_button = ttk.Button(
            master=self,
            image=self.icons["lock"],
            compound="left",
            text="ENCRYPT",
            command=self.on_submit,
            width=10,
        )
        self.submit_button.grid(row=2, column=0, columnspan=3)

    def on_upload(self):
        self.upload_file_path = fd.askopenfilename(
            title="Select TEXT File",
            filetypes=[("Text Files", ("*.txt"))],
        )
        if not self.upload_file_path:
            return

        self.upload_state = True

        self.upload_file.config(
            text=f'"{Path(self.upload_file_path).name}"',
        )
        self.upload_file_container.grid(row=0, column=2, sticky="sw", padx=(10, 0))

        self.input_entry.text.delete("1.0", "end")
        self.input_entry.text.config(
            state="disabled",
            background="#1F1F1F",
        )
        self.character_limit_label.config(text="0 / 15000")

    def on_remove_file(self):
        self.upload_state = False

        self.input_entry.text.config(state="normal", background="#2F2F2F")

        self.upload_file_container.grid_remove()

    def limit_entry(self, event):
        max_characters = 15000
        text = self.input_entry.text.get("1.0", "end-1c")
        char_count = len(text)

        self.character_limit_label.config(
            text=f"{min(char_count, max_characters)} / {max_characters}"
        )

        if max_characters - char_count < 500:
            self.custom_toast_notification.show_toast(
                "warning",
                "Nearing limit.",
            )

        if char_count >= max_characters and event.keysym not in ("BackSpace", "Delete"):
            self.custom_toast_notification.show_toast(
                "warning",
                "Limit reached.",
            )
            self.after(
                1000,
                lambda: self.custom_toast_notification.show_toast(
                    "info",
                    "Upload file.",
                ),
            )

            return "break"

    def on_paste(self, *_):
        try:
            content = self.clipboard_get()
            content_len = len(content)
            if content_len >= 15000:
                self.custom_toast_notification.show_toast("warning", "Large input.")
                self.after(
                    1000,
                    lambda: self.custom_toast_notification.show_toast(
                        "info", "Upload file."
                    ),
                )
                return "break"
        except Exception as e:
            logger.exception(f"Paste Error: {e}")
            return "break"

    def on_clear_input(self):
        self.input_entry.text.delete("1.0", "end")
        self.character_limit_label.config(text="0 / 15000")

    def on_submit(self):
        def validate_input(input_string):
            if not input_string:
                return False

            if input_string == self.old_input:
                return False

            return True

        def execute_process(process: mp.Process):
            try:
                process.start()
            except Exception as e:
                logger.exception(f"Error: {e}")
            else:
                self.old_input = self.input_string

                self.key_bytes, self.token_bytes = queue.get()

                self.image_display.display_image(
                    self.key_bytes,
                    self.token_bytes,
                    self.button_set,
                )
                # queue results needed for saving this instance
                self.button_set.key = self.key_bytes
                self.button_set.token = self.token_bytes

                self.custom_toast_notification.show_toast("success", "Input encrypted.")

                self.save_ready_state = True
            finally:
                process.join()
                logger.info("Input processed.")

        process = None
        queue = mp.Queue()
        self.input_string = self.input_entry.text.get("1.0", "end-1c").strip()

        if validate_input(self.input_string):
            self.button_set.input = self.input_string

            process = mp.Process(
                target=self.input_encryptor.encrypt,
                args=(self.input_string, queue),
            )

            try:
                execute_process(process)
            except Exception as e:
                logger.exception(f"Error: {e}")
            else:
                if self.save_ready_state:
                    self.button_set.display_buttons()
            finally:
                logger.info("Input string encrypted.")
                self.save_ready_state = False

        if self.upload_state:
            try:
                with open(self.upload_file_path, encoding="utf-8") as tf:
                    self.upload_content = tf.read()
                    self.button_set.input = self.upload_content

                process = mp.Process(
                    target=self.input_encryptor.encrypt,
                    args=(self.upload_content, queue),
                )

                execute_process(process)
            except Exception as e:
                logger.exception(f"Error reading uploaded file: {e}")
                self.custom_toast_notification.show_toast("error", "Bad File.")
            else:
                if self.save_ready_state:
                    self.button_set.display_buttons()
            finally:
                logger.info("Uploaded file encrypted.")
                self.save_ready_state = False

    def reset_instance(self):
        def clear_children(frame: ttk.Frame):
            for _ in frame.winfo_children():
                _.grid_remove()

        self.upload_state = False
        self.upload_file_container.grid_remove()
        self.input_entry.text.delete("1.0", "end")
        self.input_entry.text.config(state="normal", bg="#2f2f2f")
        self.character_limit_label.config(text="0 / 15000")
        self.old_input = ""
        self.save_ready_state = False
        clear_children(self.image_display)
        clear_children(self.button_set)


class InputEncryptor:
    def __init__(self):
        self.encryptor = Encryptor()

    def encrypt(self, input_string, queue: mp.Queue):
        try:
            key, token = self.encryptor.encrypt(input_string)
        except Exception as e:
            logger.exception(f"Input Error: {e}")
            queue.put((None, None))
            return
        else:
            queue.put((key, token))
        finally:
            logger.info("Input process attempted.")


class ImageDisplay(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.grid(row=1, column=0, sticky="nsew")

        for _ in range(3):
            self.rowconfigure(_, weight=1)
        for _ in range(5):
            self.columnconfigure(_, weight=1)

        # FONTS
        self.md_font = tk_font.Font(family="Inter Bold", size=14)

        self.key_pi = None
        self.token_pi = None
        self.bs_instance = None

        self.header_label = ttk.Label(
            master=self,
            text="Pixel Noise Form",
            font=self.md_font,
        )

        self.key_label = ttk.Label(self, text="KEY", font=self.md_font)
        self.key_image = ttk.Label(self)

        self.cipher_label = ttk.Label(self, text="CIPHER", font=self.md_font)
        self.cipher_image = ttk.Label(self)

    def _prep_image(self, data):
        arr_util = utilities.ArrayUtil(data)
        image = arr_util.transform_array_image()

        resized_image = image[0].resize((400, 400), resample=Image.NEAREST)

        tk_image = ImageTk.PhotoImage(resized_image)

        return image, tk_image

    def display_image(self, key_bytes, token_bytes, button_set_instance):
        key_image, self.key_pi = self._prep_image(key_bytes)
        token_image, self.token_pi = self._prep_image(token_bytes)
        self.bs_instance = button_set_instance
        self.bs_instance.key_image = key_image
        self.bs_instance.token_image = token_image

        self.header_label.grid(row=0, column=0, columnspan=5, pady=(10, 0))

        self.key_label.grid(row=1, column=1, pady=(0, 5))

        self.key_image.config(image=self.key_pi)
        self.key_image.grid(row=2, column=1, padx=(2, 0))

        self.cipher_label.grid(row=1, column=3, pady=(0, 5))

        self.cipher_image.config(image=self.token_pi)
        self.cipher_image.grid(row=2, column=3)


class OutputPopup(ttk.Toplevel):
    def __init__(self, key: str, token: str):
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

        for _ in range(3):
            self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=999)
        self.columnconfigure(1, weight=1)

        # ICONS
        self.icons = {
            "close": ttk.PhotoImage(file=IMG_PATH / "close.png"),
        }

        self.output_label = ttk.Label(
            master=self,
            text="TEXT FORM",
            font=("Inter Bold", 14),
        )
        self.output_label.grid(
            row=0, column=0, sticky="nw", padx=(10, 10), pady=(10, 10)
        )

        self.close_button = ttk.Button(
            master=self,
            image=self.icons["close"],
            command=lambda: self.destroy(),
            bootstyle="primary-outline",
            padding=0,
        )
        self.close_button.grid(
            row=0, column=1, sticky="ne", padx=(10, 10), pady=(10, 10)
        )

        # DISPLAY OUTPUT BOX
        OutputBox(self, row=1, output_type="KEY", entry_height=1, text=key)
        OutputBox(self, row=2, output_type="CIPHER", entry_height=8, text=token)


class OutputBox(ttk.Frame):
    def __init__(self, master, row, output_type, entry_height, text):
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
            "copy": ttk.PhotoImage(file=IMG_PATH / "copy.png"),
            "check": ttk.PhotoImage(file=IMG_PATH / "check.png"),
            "info": ttk.PhotoImage(file=IMG_PATH / "info.png"),
        }

        # INSTANCE VARIABLES
        self.output_type = output_type
        self.text = text.decode()

        for _ in range(2):
            self.rowconfigure(_, weight=1)
        self.columnconfigure(0, weight=999)
        self.columnconfigure(1, weight=1)

        self.output_label_container = ttk.Frame(master=self)
        self.output_label_container.grid(row=0, column=0, sticky="ew")

        self.output_label_container.rowconfigure(0, weight=1)
        self.output_label_container.columnconfigure(0, weight=1)
        self.output_label_container.columnconfigure(1, weight=999)

        self.output_label = ttk.Label(
            master=self.output_label_container,
            font=self.md_font,
            text=f"{self.output_type}",
        )
        self.output_label.grid(row=0, column=0, sticky="sw")

        self.info_label = ttk.Label(
            master=self.output_label_container,
            image=self.icons["info"],
        )
        self.info_label.grid(row=0, column=1, sticky="w")
        rep_len = f"{len(text):,}".replace(",", " ")
        ToolTip(
            self.info_label,
            f"Total Length: {rep_len} chars\nActual Memory Size: {self._compute_size(text)}",
        )

        self.output_text_box = ScrolledText(
            master=self,
            height=entry_height,
            wrap="word",
            undo=True,
            font=self.sm_font,
            bootstyle="round dark",
            autohide=True if len(self.text) < 792 else False,
        )
        self.output_text_box.grid(row=1, column=0, sticky="nsew")
        self.output_text_box.insert(ttk.INSERT, self._preprocess_text(self.text))
        self.output_text_box.text.config(state="disabled")

        self.copy = ttk.Button(
            master=self,
            image=self.icons["copy"],
            command=self._on_copy,
            padding=2,
            bootstyle="dark-outline",
        )
        self.copy.grid(
            row=1,
            column=1,
            sticky="ne",
            padx=(0, 2),
            pady=(2, 0),
        )

    def _on_copy(self):
        self.copy.config(image=self.icons["check"], state="disabled")

        self.clipboard_clear()
        self.clipboard_append(string=self._preprocess_text(self.text))

        self.copy.after(
            2000,
            lambda: self.copy.config(
                image=self.icons["copy"],
                state="normal",
            ),
        )

    def _preprocess_text(self, text, line_len=0):
        line_len = 100 if len(text) < 792 else 99
        lines = [text[i : i + line_len] for i in range(0, len(text), line_len)]
        line = "\n".join(lines)
        return line

    def _compute_size(self, text):
        size = len(text)

        units = ["Bytes", "KB", "MB", "GB"]
        index = 0

        while size >= 1024 and index < len(units) - 1:
            size /= 1024.0
            index += 1

        rep_size = f"{size:.2f}" if len(text) >= 1024 else f"{size}"
        return f"{rep_size} {units[index]}"


class ButtonSet(ttk.Frame):
    def __init__(self, master: ttk.Frame, reset_cb):
        super().__init__(master)
        self.grid(row=2, column=0, sticky="nsew", padx=(2, 2))
        self.reset_callback = reset_cb

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=999)

        # ICONS
        self.icons = {
            "save": ttk.PhotoImage(file=IMG_PATH / "save.png"),
            "trash": ttk.PhotoImage(file=IMG_PATH / "trash.png"),
            "view": ttk.PhotoImage(file=IMG_PATH / "view.png"),
        }

        # CLASS INSTANCES
        self.custom_toast_notification = CustomToastNotification(master)
        self.output_popup = None

        # VARIABLES
        self._input = None
        self._key = None
        self._token = None
        self._key_image = None
        self._token_image = None

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

        self.view_button = ttk.Button(
            master=self,
            image=self.icons["view"],
            command=self._on_view,
            padding=4,
            bootstyle="info-outline",
        )

        ToolTip(self.view_button, msg="View text form.")

    @property
    def input(self):
        return self._input

    @input.setter
    def input(self, instance_input):
        self._input = instance_input

    @property
    def key(self):
        return self._key

    @key.setter
    def key(self, instance_key):
        self._key = instance_key

    @property
    def token(self):
        return self._token

    @token.setter
    def token(self, instance_token):
        self._token = instance_token

    @property
    def key_image(self):
        return self._key_image

    @key_image.setter
    def key_image(self, image):
        self._key_image = image

    @property
    def token_image(self):
        return self._token_image

    @token_image.setter
    def token_image(self, image):
        self._token_image = image

    def _on_save(self):
        save_file_name_path: str = ""
        save_file_name_path = fd.asksaveasfilename(
            defaultextension=".zip",
            initialdir=Path.home() / "Documents" / "ciphers",
            initialfile=f"cipher-{datetime.now():%b%d-%H%M%S-%f}.zip",
            filetypes=[("Zip Files", ("*.zip"))],
        )

        if not save_file_name_path:
            return

        utilities.CipherSaver(
            self._input,
            self._key,
            self._token,
            self._key_image,
            self._token_image,
        ).save_cipher(save_file_name_path)

        self.custom_toast_notification.show_toast("success", "Instance saved.")

    def _on_reset(self):
        self.reset_callback()
        self.custom_toast_notification.show_toast("info", "Instance cleared.")

    def _on_view(self):
        self.output_popup = OutputPopup(self._key, self._token)
        self.wait_window(self.output_popup)

    def display_buttons(self):
        # show only when save_state ready/true
        self.save_button.grid(row=0, column=0, sticky="sw", padx=(0, 12))
        self.clear_button.grid(row=0, column=1, sticky="sw")
        self.view_button.grid(row=0, column=2, sticky="se")


class CustomToastNotification(ToastNotification):
    ACTIVE_TOAST = None

    def __init__(self, parent: ttk.Frame):
        # used to compute toast pos relative to parent size and pos
        self.parent = parent

        # ICONS
        self.icons = {
            "dot_success": ttk.PhotoImage(file=IMG_PATH / "dot_success.png"),
            "dot_info": ttk.PhotoImage(file=IMG_PATH / "dot_info.png"),
            "dot_warning": ttk.PhotoImage(file=IMG_PATH / "dot_warning.png"),
            "dot_error": ttk.PhotoImage(file=IMG_PATH / "dot_error.png"),
            "dot_default": ttk.PhotoImage(file=IMG_PATH / "dot_default.png"),
        }

        # INSTANCE VARIABLES
        self.custom_style = ""
        self.message = ""
        self.title = ""
        self.icon = ""
        self.title_font = ("Inter Bold", 14)
        self.message_font = ("Inter Regular", 11)
        self.char_length = 0
        self.duration = 0
        self.toplevel = None

    def show_toast(self, custom_style: str, message: str):
        if CustomToastNotification.ACTIVE_TOAST is not None:
            CustomToastNotification.ACTIVE_TOAST.toplevel.destroy()

        # build toast
        self.toplevel = ttk.Toplevel()
        CustomToastNotification.ACTIVE_TOAST = self
        self._setup()

        self.container = ttk.Frame(self.toplevel)
        self.container.pack(fill="both", expand=1)

        style = Style()
        style.configure("custom.TFrame", background="#FAFAFA")
        self.container.configure(style="custom.TFrame")

        self.message = message
        self.char_length = len(self.title) + len(self.message)
        self.duration = min(max((self.char_length * 50), 1000), 2000)

        fg_color = "#1B1B1B"
        bg_color = "#FAFAFA"

        match custom_style:
            case "success":
                self.title = "SUCCESS"
                self.icon = "dot_success"
            case "info":
                self.title = "INFO"
                self.icon = "dot_info"
            case "warning":
                self.title = "CAUTION"
                self.icon = "dot_warning"
            case "error":
                self.title = "FAILURE"
                self.icon = "dot_error"
            case _:
                self.title = "UNKNOWN"
                self.icon = "dot_default"

        # image label
        ttk.Label(
            self.container,
            image=self.icons[self.icon],
            background=bg_color,
            anchor="center",
        ).grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(10, 0))

        # title label
        ttk.Label(
            self.container,
            # text=self.title,
            text=self.title,
            font=self.title_font,
            foreground=fg_color,
            background=bg_color,
            anchor="nw",
        ).grid(row=0, column=1, sticky="nsew", padx=10, pady=(5, 0))

        # message label
        ttk.Label(
            self.container,
            text=self.message,
            font=self.message_font,
            foreground=fg_color,
            background=bg_color,
            anchor="nw",
        ).grid(row=1, column=1, sticky="nsew", padx=10, pady=(0, 5))

        self.toplevel.bind("<ButtonPress>", self._hide_toast)

        # specified duration to close
        if self.duration:
            self.toplevel.after(self.duration, self._hide_toast)

    def _hide_toast(self, *_):
        try:
            alpha = float(self.toplevel.attributes("-alpha"))
            if alpha <= 0:
                self.toplevel.destroy()
                CustomToastNotification.ACTIVE_TOAST = None
            else:
                self.toplevel.attributes("-alpha", alpha - 0.01)
                self.toplevel.after(1, self._hide_toast)
        except Exception:
            if self.toplevel:
                self.toplevel.destroy()
                CustomToastNotification.ACTIVE_TOAST = None

    def _setup(self):
        # toplevel configs
        self.toplevel.overrideredirect(True)
        self.toplevel.configure(relief="raised")

        self._set_geometry()

    def _set_geometry(self):
        self.toplevel.update_idletasks()  # actualize geometry

        toast_width = 220
        toast_height = 60
        offsets = (7, 10, 5)

        x_position: int = 0
        y_position: int = 0

        # x_position = (self.parent.winfo_rootx() + self.parent.winfo_width()) - (
        #     toast_width + offsets[0]
        # )

        x_position = (
            self.parent.winfo_rootx() + ((self.parent.winfo_width() // 2) - 1)
        ) - (toast_width // 2)

        y_position = (
            self.parent.winfo_rooty()
            + self.parent.winfo_height()
            - (toast_height + offsets[1])
        )

        self.toplevel.geometry(
            f"{toast_width}x{toast_height}+{x_position}+{y_position}"
        )
