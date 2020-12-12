
SQL_UP="""
CREATE TABLE schema02.mg_user
(
      id int
    , name nvarchar(30)
    , update_date datetime
    , CONSTRAINT PK_mg_user PRIMARY KEY CLUSTERED (id)
);
"""

SQL_DOWN="""
DROP TABLE schema02.mg_user
"""
