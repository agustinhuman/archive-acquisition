import abc
import csv
import time
from os import PathLike
import yaml
from pathlib import Path


from pydantic import BaseModel, DirectoryPath


class Conf(BaseModel):
    """Image provider configuration"""
    class ExporterConf(BaseModel):
        """Phone configuration"""
        root_folder: Path

    # Namespace the configuration for the Phone provider
    export: ExporterConf


class Exporter(abc.ABC):

    def __init__(self, conf):
        self.conf: Conf.ExporterConf = Conf(**conf).export
        self.conf.root_folder.mkdir(parents=True, exist_ok=True)

    def export(self, image: bytes, metadata: dict):
        try:
            self._export(image, metadata)
        except Exception as e:
            print(f"Error exporting image: {e}")

    @abc.abstractmethod
    def _export(self, image: bytes, metadata: dict):
        pass

class FolderExporter(Exporter):
    def _export(self, image: bytes, metadata: dict):
        timestamp = round(time.time() * 1000)
        image_path = self.conf.root_folder / f"{timestamp}.jpg"
        metadata_path = self.conf.root_folder / f"{timestamp}.yaml"
        with open(image_path, "wb") as f:
            f.write(image)

        with open(metadata_path, 'w') as f:
            yaml.dump(metadata, f)
