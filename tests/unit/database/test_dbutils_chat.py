from database.dbutils.dbutils_chat import find_groups_created_by


def test_find_groups_created_by(mongo_service):
    mock_chats = [
        {"chat_type": "group", "created_by": 1},
        {"chat_type": "private", "created_by": 1},
        {"chat_type": "channel", "created_by": 1},
        {"chat_type": "supergroup", "created_by": 1},
        {"chat_type": "group", "created_by": 2},
        {"chat_type": "private", "created_by": 2},
        {"chat_type": "channel", "created_by": 2},
        {"chat_type": "supergroup", "created_by": 2},
    ]
    for chat in mock_chats:
        mongo_service.insert_new_chat(chat)

    # should only return groupchats
    res = find_groups_created_by(mongo_service, 1)
    assert len(res) == 2
    assert res[0]["chat_type"] == "group"
    assert res[1]["chat_type"] == "supergroup"
