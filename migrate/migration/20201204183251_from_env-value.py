
SQL_UP=[
    f"INSERT INTO schema02.mg_user VALUES(4, '{os.getenv('MSSQL_MIGRATE_DB_USER', 'ユーザーD')}', GETDATE());"
]

SQL_DOWN=[
    "DELETE FROM schema02.mg_user WHERE id = 4;"
]
