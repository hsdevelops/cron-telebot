from common.enums import ContentType, Restriction


def test_enum_values():
    assert ContentType.TEXT.value == "text"
    assert ContentType.PHOTO.value == "single_photo"
    assert ContentType.MEDIA.value == "photo_group"
    assert ContentType.POLL.value == "poll"
    assert Restriction.OWNER.value == "creator"
    assert Restriction.ADMIN.value == "administrator"
