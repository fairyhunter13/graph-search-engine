"""A fixture with the shapes the golden counts are taken from."""

import logging
import os.path as path
from decimal import Decimal

from .rates import TAXES, convert

LOG = logging.getLogger(__name__)


class Order:
    total = Decimal(0)

    def __init__(self, lines):
        self.lines = lines

    def subtotal(self):
        return sum(line.amount for line in self.lines)

    def tax(self):
        return self.subtotal() * TAXES["default"]


class RushOrder(Order):
    def tax(self):
        return convert(super().tax())


def load(root):
    LOG.info(path.join(root, "orders"))
    return Order([])


def retry(fn):
    return fn()
