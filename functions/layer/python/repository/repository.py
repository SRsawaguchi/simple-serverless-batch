from abc import ABCMeta, abstractmethod
from datetime import date

from model.message import Message


class Repository(metaclass=ABCMeta):
    @abstractmethod
    def get_message(self, target_date: date) -> Message:
        pass
