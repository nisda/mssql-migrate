
SQL_UP=[
    "INSERT INTO schema02.mg_user VALUES(1, 'ユーザーA', GETDATE());",
    "INSERT INTO schema02.mg_user VALUES(2, 'ユーザーB', GETDATE());",
    "",
    "INSERT INTO schema02.mg_user VALUES(3, 'ユーザーC', GETDATE());"
]

SQL_DOWN=[
    "DELETE FROM schema02.mg_user WHERE id = 1;",
    "DELETE FROM schema02.mg_user WHERE id = 2;",
    "",
    "DELETE FROM schema02.mg_user WHERE id = 3;"
]
