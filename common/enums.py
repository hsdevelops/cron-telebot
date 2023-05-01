from enum import Enum


class ContentType(Enum):
    TEXT = "text"
    PHOTO = "single_photo"
    MEDIA = "photo_group"
    POLL = "poll"


class Restriction(Enum):
    OWNER = "creator"
    ADMIN = "administrator"
