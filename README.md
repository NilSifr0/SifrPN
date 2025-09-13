# SifrPN: Pixel Noise Encryption/Decryption Tool

SifrPN is a desktop application for encrypting and decrypting text using pixel noise images. It provides a GUI for secure encryption and decryption and leverages the Fernet symmetric encryption scheme.

## Features

- **Encrypt Text**: Convert any string or text file into a secure, encrypted token and key.
- **Pixel Noise Images**: Visualize keys and tokens as pixel noise images.
- **Decrypt**: Restore original text from key and token images or their text forms.
- **Save/Export**: Export ciphered data as ZIP or text files.
- **User Interface**: UI built with [ttkbootstrap](https://github.com/israel-dryer/ttkbootstrap).
- **Logging**: Configurable logging for debugging and auditing.

## Installation

### Pre-built Installation

1. Download the latest release of SifrPN from the [Releases](https://github.com/NilSifr0/SifrPN/releases/tag/v1) page.
2. Run the installer and follow the on-screen instructions to complete the installation.

### Building from Source

1. **Clone the repository**

    ```sh
    git clone https://github.com/NilSifr0/sifrpn.git

    cd sifrpn
    ```

2. **Install dependencies**

    ```sh
    pip install -r requirements.txt
    ```

3. **Run the application**

    ```sh
    py app.py
    ```

4. **(Optionally) Build the project using Nuitka**

    ```sh
    nuitka --standalone --msvc=latest --enable-plugin=tk-inter --include-package-data=assets --include-package-data=etc --include-package-data=configs --windows-icon-from-ico=assets/zero.png --windows-console-mode=disable app.py
    ```

## Usage

- **Encrypt Tab**: Enter text or upload a .txt file, then encrypt. Save or view the generated key/token images or text.
- **Decrypt Tab**: Upload key/token images or paste their text forms to decrypt and recover the original message.

## Requirements

- Python 3.13+ (as this project was coded in 3.13.5)
- See [requirements.txt](/requirements.txt) for details.

## Logging

Logs are written to `app.log` and configured via [logging_config.yaml](/configs/logging_config.yaml)

## False Positive Warning

**Important Notice**: Some users may encounter a false positive warning from Microsoft Defender when running SifrPN. This is a known issue and does not indicate that the application is harmful.

### What to Do If Flagged

If Microsoft Defender flags SifrPN, you can safely ignore the warning. However, if you wish to run the application without interruptions, you can add an exclusion in Microsoft Defender by following these steps:

1. Open **Windows Security**.
2. Click on **Virus & threat protection**.
3. Under the **Virus & threat protection settings**, click on **Manage settings**.
4. Scroll down to **Exclusions** and click on **Add or remove exclusions**.
5. Click on **Add an exclusion** and select **Folder** or **File**.
6. Navigate to the location of the SifrPN executable and select it.

## Acknowledgments

- [NumPy](https://numpy.org/) - for numerical computations
- [Pillow (PIL)](https://github.com/python-pillow/Pillow) - for image processing
- [cryptography](https://github.com/pyca/cryptography) - for cryptographic functions
- [ttkbootstrap](https://github.com/israel-dryer/ttkbootstrap) - for the app GUI
- [tktooltip](https://pypi.org/project/TkToolTip/) - for customized tooltips

## License

MIT License. See [LICENSE](/etc/LICENSE) for details.  

## Note  

- All cipher files are saved in your `Documents/ciphers` directory by default.
- For any issues or feature requests, please open an issue on GitHub or contact me through:
  - Email: [jimmyiicaticat@gmail.com](mailto:jimmyiicaticat@gmail.com)
