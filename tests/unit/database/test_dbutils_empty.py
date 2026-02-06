from database.dbutils.dbutils_empty import empty_update_result


def test_empty_update_result():
    res = empty_update_result()
    assert res.matched_count == 0
    assert res.modified_count == 0
