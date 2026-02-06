from pymongo.results import UpdateResult, InsertOneResult


def empty_update_result() -> UpdateResult:
    return UpdateResult(
        {"n": 0, "nModified": 0, "ok": 0, "updatedExisting": False}, True
    )
