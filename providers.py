import abc
import logging
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class Conf(BaseModel):
    """Image provider configuration"""
    class Phone(BaseModel):
        """Phone configuration"""
        ip: str
        photo_button_location: list[int] = Field(..., min_length=2, max_length=2)
        photos_folder: str = "/storage/emulated/0/DCIM/Camera/"

    # Namespace the configuration for the Phone provider
    phone: Phone


def run(cmd) -> str:
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if proc.returncode != 0:
        raise Exception(f"Error running command {cmd}")
    return proc.stdout.strip()


class ImageProvider(abc.ABC):
    def __init__(self, raw_conf, mock_photo: Path | None = None):
        self.raw_conf: dict[str, Any] = raw_conf

        # When not None we return this value instead of asking the phone
        self.mock_photo: bytes | None = None if mock_photo is None else mock_photo.read_bytes()

    def take_photo(self) -> bytes | None:
        """Takes a new photo and saves it to local storage. Returns the path to the saved photo."""
        if self.mock_photo is not None:
            return self.mock_photo

        try:
            file_path = self._take_photo()
            if file_path is not None:
                return open(file_path, 'rb').read()
            return None
        except Exception as e:
            logging.error(f"Error taking photo: {e}")
            return None

    @abc.abstractmethod
    def _take_photo(self) -> bytes:
        """Actual implementation of taking a photo."""

OUT_PATH = Path(tempfile.gettempdir()) / "archive" / "original.jpg"

class Phone(ImageProvider):
    def __init__(self, conf, mock_photo: Path | None = None):
        super().__init__(conf, mock_photo)
        self.conf: Conf.Phone = Conf(**conf).phone

        self.last_photo_remote_path = self._update_last_remote_photo()


    def init(self):
        """Get the last photo taken on the device so we can detect when a new one is generated"""
        if self.last_photo_remote_path is None:
            self.last_photo_remote_path = self._update_last_remote_photo()

    def _tab(self, coords):
        """Taps on the screen at the given coordinates"""
        run(f"adb shell input tap {coords[0]} {coords[1]}")

    def _pull(self, remote, local):
        """Pulls a file from the device to local storage"""
        run(f"adb pull {remote} {local}")

    def _take_photo(self) -> bytes:
        """Takes the photo and saves it to the device"""
        self._tab(self.conf.photo_button_location)
        remote_photo_path = self._get_new_photo_path()
        self._pull(remote_photo_path, OUT_PATH)
        self._remove_remote_file(remote_photo_path)
        logging.info(f"Took photo: {Path(remote_photo_path).name}")
        return OUT_PATH.read_bytes()

    def _update_last_remote_photo(self):
        return run(f"adb shell find {self.conf.photos_folder} -type f -exec ls -t1 {{}} + | head -1")

    def _get_new_photo_path(self):
        new_photo_path = self.last_photo_remote_path
        while new_photo_path == self.last_photo_remote_path or new_photo_path.split("/")[-1].startswith("."):
            new_photo_path = self._update_last_remote_photo()
            time.sleep(0.1)

        self.last_photo_remote_path = new_photo_path
        return new_photo_path

    def _remove_remote_file(self, remote_photo_path):
        """Removes a file from the phone"""
        run(f"adb shell rm {remote_photo_path}")
