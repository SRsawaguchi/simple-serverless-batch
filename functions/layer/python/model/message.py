from dataclasses import dataclass
from datetime import date

from model.model import Model


@dataclass
class Message(Model):
    date: date
    message: str
