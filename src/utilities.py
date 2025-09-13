import json
import logging.config
import os
import re
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import datetime
from functools import wraps
from math import ceil, pow, sqrt
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import yaml
from PIL import Image
from PIL.PngImagePlugin import PngInfo

config_path = Path(__file__).parent.parent / "configs" / "logging_config.yaml"

with open(config_path, "r") as yf:
    config = yaml.safe_load(yf)
    logging.config.dictConfig(config)


logger = logging.getLogger(__name__)


class ArrayUtil:
    def __init__(self, data):
        self.data = data

    def _calc_array_shape(self, list_len: int) -> tuple[int, int]:
        side = sqrt(list_len / 3)

        if side % 1 != 0:
            side = int(ceil(side))
            size = pow(side, 2)
            pad = (int(size) * 3) - list_len

            return side, pad
        else:
            return int(side), 0

    def _prepare_array(self) -> tuple[list[int], int, int]:
        raw_bytes = urlsafe_b64decode(self.data)
        int_list = [_ for _ in raw_bytes]
        side, pad = self._calc_array_shape(len(int_list))

        if pad != 0:
            random_pad = os.urandom(pad)
            pad_list = [_ for _ in random_pad]
            int_list.extend(pad_list)

            return int_list, side, pad
        else:
            return int_list, side, 0

    def transform_array_image(self) -> tuple[Image.Image, int]:
        int_list: list[int]
        side: int
        pad: int

        int_list, side, pad = self._prepare_array()

        image_array = np.asarray(int_list, dtype=np.uint8).reshape(side, side, 3)

        image = Image.fromarray(image_array)

        return image, pad


class ImageUtil:
    def __init__(self, data: Image.Image):
        # data is loaded with
        # ("PaddingCountHint", str(pad))
        # ("ResizeScaleFactor", str(true_size))
        self.data = data

    def _prepare_image(self):
        if "IsSifrPNRescaled" in self.data.text:
            true_size = int(self.data.text["SifrPNTrueSize"])
            default_image = self.data.resize(
                (true_size, true_size),
                resample=Image.NEAREST,
            )
            return np.asarray(default_image)
        else:
            return np.asarray(self.data)

    def _array_slice(self, image_array):
        # use padding count hint to determine where to start slicing
        # return true int list
        pch = int(self.data.text["PaddingCountHint"])
        one_d_array = np.ravel(image_array)
        int_list = one_d_array[:-pch]
        return int_list

    def _prep_int_list(self, int_list):
        # convert int list to byte list
        # return byte list
        return bytes(int_list)

    def _encode_raw_bytes(self, raw_bytes):
        return urlsafe_b64encode(raw_bytes)

    def transform_image_array(self):
        # check first if image is scaled
        # array
        img_arr = self._prepare_image()
        # array - padding
        int_list = self._array_slice(img_arr)
        # array(int_list) -> bytes list
        raw_bytes = self._prep_int_list(int_list)

        b64_urlsafe = self._encode_raw_bytes(raw_bytes)

        return b64_urlsafe


class CipherSaver:
    def __init__(
        self,
        input_string: str,
        key: bytes,
        token: bytes,
        key_image: Image.Image,
        token_image: Image.Image,
    ):
        self.session = {}
        self.input_string = input_string
        self.key = key
        self.token = token
        self.key_image = key_image
        self.token_image = token_image

    def _save_session(self):
        self.session["date"] = datetime.now().isoformat()
        self.session["input"] = self.input_string
        self.session["key"] = self.key.decode()
        self.session["token"] = self.token.decode()

        return self.session

    def _resize_image(self, image):
        true_size = image.width
        thresholds = [500, 1000, 1500, 2000]

        resize_width = next(
            (width for width in thresholds if image.width < width),
            None,
        )

        if resize_width is None:
            return image, true_size

        resized_image = image.resize(
            (resize_width, resize_width),
            resample=Image.NEAREST,
        )

        return resized_image, true_size

    def _create_path(self) -> Path:
        directory_path = Path.home() / "Documents" / "ciphers"
        directory_path.mkdir(parents=True, exist_ok=True)

        return directory_path

    def _clean_residuals(
        self,
        text_path: Path,
        key_path: Path,
        token_path: Path,
        resized_key_path: Path,
        resized_token_path: Path,
    ) -> None:
        text_path.unlink(missing_ok=True)
        key_path.unlink(missing_ok=True)
        token_path.unlink(missing_ok=True)
        resized_key_path.unlink(missing_ok=True)
        resized_token_path.unlink(missing_ok=True)

    def _prepare_files(save_function):
        @wraps(save_function)
        def wrapper_function(self, *args, **kwargs):
            cipher_name = kwargs.get("cipher_name", "item")
            try:
                result = save_function(self, *args, **kwargs)
            except Exception as e:
                logger.exception(f"Error saving files: {e}")
                return None
            else:
                logger.info("File %s created.", cipher_name)
                return result
            finally:
                logger.info("Saving file attempt completed.")

        return wrapper_function

    @_prepare_files
    def _save_json(self, session: list, cipher_name: str) -> Path:
        path = self._create_path()
        file_name = path / f"cipher-{cipher_name}-for_debugging.json"

        with file_name.open("w+", encoding="utf-8") as file:
            json.dump(session, file)

        return file_name

    @_prepare_files
    def _save_image(
        self,
        image: tuple[Image.Image, int],
        cipher_name: str,
        image_type: str,
    ) -> tuple[Path, Path]:
        # arr_util = ArrayUtil(cipher)
        # image, pad = arr_util.transform_array_image()

        instance_image, pad = image

        metadata = PngInfo()
        metadata.add_text("IsSifrPixelNoise", str(True))
        metadata.add_text("SifrPNImageType", str(image_type))
        metadata.add_text("PaddingCountHint", str(pad))

        path = self._create_path()

        file_name = path / f"cipher-{cipher_name}-default.png"
        instance_image.save(file_name, pnginfo=metadata)

        resized_image, true_size = self._resize_image(instance_image)
        metadata.add_text("SifrPNTrueSize", str(true_size))
        metadata.add_text("IsSifrPNRescaled", str(True))

        resized_file_name = path / f"cipher-{cipher_name}-resized.png"
        resized_image.save(resized_file_name, pnginfo=metadata)

        return file_name, resized_file_name

    def save_cipher(self, custom_file_name_path: str):
        session_json = self._save_session()
        json_info = self._save_json(
            session_json,
            cipher_name="json_info",
        )
        key_image, resized_key_image = self._save_image(
            self.key_image,
            cipher_name="key_image",
            image_type="KEY",
        )
        token_image, resized_token_image = self._save_image(
            self.token_image,
            cipher_name="token_image",
            image_type="CIPHER",
        )

        try:
            with ZipFile(custom_file_name_path, "w") as zip:
                zip.write(json_info, arcname=json_info.name)
                zip.write(key_image, arcname=key_image.name)
                zip.write(token_image, arcname=token_image.name)
                zip.write(resized_key_image, arcname=resized_key_image.name)
                zip.write(resized_token_image, arcname=resized_token_image.name)
        except Exception as e:
            logger.exception(f"Error saving files: {e}")
        else:
            logger.info("File saving and zipping successful.")
        finally:
            self._clean_residuals(
                json_info,
                key_image,
                token_image,
                resized_key_image,
                resized_token_image,
            )
            logger.info("Zip process attempt completed.")


class ResultSaver:
    def __init__(self, file_path):
        self.file_path = file_path
        self.result_file = None

    def save_result(self, content):
        with open(self.file_path, "w", encoding="utf-8") as file:
            file.write(content)


class Validator:
    def _prep_string(self, string):
        return "".join([string.strip() for string in string.split()])

    def validate_string(self, string, input_type):
        clean_string = self._prep_string(string)
        pattern = re.compile(
            r"^(?:[A-Za-z0-9_-]{4})*(?:[A-Za-z0-9_-]{4}|[A-Za-z0-9_-]{3}=|[A-Za-z0-9_-]{2}={2})$"
        )
        if input_type == "KEY" and len(clean_string) != 44:
            return False, ""

        if input_type == "CIPHER" and len(clean_string) < 100:
            return False, ""

        if not re.match(pattern, clean_string):
            return False, ""

        return True, clean_string

    def validate_upload(self, upload_file_path: str, container_type: str):
        try:
            with Image.open(upload_file_path, "r") as image:
                if "IsSifrPixelNoise" in image.text:
                    image_type = image.text["SifrPNImageType"]
                    if image_type != container_type:
                        logger.warning(
                            f"Image type mismatch: expected {container_type}, got {image_type}."
                        )
                        return False, ""

                    img_util = ImageUtil(image)
                    byte_string = img_util.transform_image_array()

                    is_valid, clean_string = self.validate_string(
                        byte_string.decode(),
                        image_type,
                    )

                    if not is_valid:
                        logger.warning("String validation failed.")
                        return False, ""
                    return True, clean_string
                else:
                    logger.warning("Image is not a SifrPixelNoise.")
                    return False, ""
        except Exception as e:
            logger.exception(f"Critical Error: {e}")
            return False, ""
        finally:
            logger.info("Validity check attempt completed.")


if __name__ == "__main__":
    print(config_path)
