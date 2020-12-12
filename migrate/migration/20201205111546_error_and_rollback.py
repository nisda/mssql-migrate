
SQL_UP=[
    "INSERT INTO schema02.mg_user VALUES(5, 'ユーザーE', GETDATE());",
    "INSERT INTO schema02.mg_user VALUES(1, 'violation of primary key', GETDATE());",
    "INSERT INTO schema02.mg_user VALUES(7, 'ユーザーG', GETDATE());"
]

SQL_DOWN=[
    "DELETE FROM schema02.mg_user WHERE id = 5;",
    "DELETE FROM schema02.mg_user WHERE id = 6;",
    "DELETE FROM schema02.mg_user WHERE id = 7;"
]
