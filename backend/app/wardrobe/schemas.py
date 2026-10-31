from datetime import datetime

from pydantic import Field

from app.catalog.schemas import Contract
from app.tofi.schemas import TofiProduct, TofiProfile


class SaveWardrobe(Contract):
    profile: TofiProfile
    comment: str = Field(default="", max_length=1000)


class SavedItem(SaveWardrobe):
    product: TofiProduct
    savedAt: datetime


class WardrobeResponse(Contract):
    items: list[SavedItem]
