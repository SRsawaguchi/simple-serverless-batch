from abc import ABCMeta, abstractmethod


class Storage(metaclass=ABCMeta):
    @abstractmethod
    def upload_file(self, file_path: str, object_name: str) -> str:
        pass

    @abstractmethod
    def download_file(self, object_name: str, dist_dir: str) -> str:
        pass
