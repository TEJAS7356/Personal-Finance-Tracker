import os
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as tmp:
    os.chdir(tmp)
    import database

    database.DB_NAME = str(Path(tmp) / "reset.db")
    database.create_database()
    user_id = database.create_user("recoverme", "old-password", "recoverme@example.com")
    assert database.get_user_by_email("RECOVERME@example.com")["id"] == user_id
    assert database.verify_user("recoverme", "old-password")["id"] == user_id
    assert database.reset_user_password(user_id, "new-password") is True
    assert database.verify_user("recoverme", "old-password") is None
    assert database.verify_user("recoverme", "new-password")["id"] == user_id

print("password reset database test passed")
