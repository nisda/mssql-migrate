
SQL_UP=[
    "INSERT INTO schema02.mg_user VALUES(8, 'ユーザーH', GETDATE());"
]

SQL_DOWN=[
    "DELETE FROM schema02.mg_user WHERE id = 8;"
]
