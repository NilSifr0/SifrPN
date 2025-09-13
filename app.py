from pathlib import Path

import ttkbootstrap as ttk

import src.decryptor_ui as dui
import src.encryptor_ui as eui


class UI(ttk.Frame):
    def __init__(self, app: ttk.Window):
        super().__init__(app)

        # POSITION
        self.screen_width = app.winfo_screenwidth()
        self.screen_height = app.winfo_screenheight()
        self.x = (self.screen_width // 2) - (1280 // 2)
        self.y = (self.screen_height // 2) - (800 // 2)
        app.geometry(f"+{self.x}+{self.y}")

        # TABS
        self.tab_control = ttk.Notebook(app)
        self.tab_control.pack(fill="both", expand=1)

        # MAIN FRAMES
        self.encrypt_ui = eui.EncryptUI(self.tab_control)
        self.tab_control.add(self.encrypt_ui, text="ENCRYPT")

        self.decrypt_ui = dui.DecryptUI(self.tab_control)
        self.tab_control.add(self.decrypt_ui, text="DECRYPT")


def main():
    app = ttk.Window(
        title="SifrPN: Pixel Noise Encryption/Decryption Tool",
        themename="darkly",
        resizable=(False, False),
        minsize=(1280, 1),
    )

    icon_path = Path(__file__).parent / "assets" / "zero.png"
    app_icon = ttk.PhotoImage(file=icon_path)
    app.iconphoto(False, app_icon)

    UI(app)

    app.update_idletasks()
    app.mainloop()


if __name__ == "__main__":
    main()
