sleep 10s

/opt/mssql-tools/bin/sqlcmd -S "127.0.0.1" -U "SA" -P "${MSSQL_SA_PASSWORD}" -d "master" -i ./init.sql
