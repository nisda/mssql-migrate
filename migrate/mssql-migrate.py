# coding: utf-8

import os
import sys
import pyodbc
import json
import argparse
import types
import datetime
import pathlib
import copy
import hashlib

DEFAULT_CONFIG_PATH=os.getenv("MSSQL_MIGRATE_CONFIG", "./config.py")

HASH_SHORT_LENGTH=8

MIGRATE_TABLE_COLUMNS=[
    { "name": "id"          , "type": "nvarchar(20)"},
    { "name": "name"        , "type": "nvarchar(50)"},
    { "name": "size"        , "type": "int"},
    { "name": "hash"        , "type": "nvarchar(64)"},
    { "name": "applied_date", "type": "datetime2(7)"},
    { "name": "applied_user", "type": "nvarchar(50)"},
]
MIGRATE_SHOW_STATUS_HEADER=[
    "id",
    "name",
    "size",
    ("hash_short", "hash (sha256)"),
    "applied_date",
    "applied_user",
]


class SimpleTable:


    def __init__(self, header=[], rows=[]):
        self._header = header
        self._rows = rows


    def set_header(self, header):
        self._header = header


    def set_rows(self, rows):
        self._rows = rows


    def add_row(self, row):
        self._rows.append(row)


    def print_table(self, indent=0):
        print(self.get_table(indent))


    def get_table(self, indent=0):
        table = None
        if ( len(self._rows) > 0 ):
            obj = self._rows[0]
            if isinstance(obj, list) or isinstance(obj, tuple):
                table = self._generate_table_from_list(indent)
            if isinstance(obj, dict):
                table = self._generate_table_from_dict(indent)
        return table


    def _get_unicode_width(self, value):
        import unicodedata
        width = {'F': 2, 'W': 2, 'A': 2}
        s = self._to_str(value)
        return sum(width.get(unicodedata.east_asian_width(c), 1) for c in s)


    def _to_str(self, value):
        value = "" if value is None else str(value)
        return value


    def _padding(self, value, length, alignment="auto", spacer=" "):

        alignment = alignment.lower()
        if ( alignment == "auto" ):
            if ( isinstance(value, int) or isinstance(value, float) ):
                alignment = "right"
            else:
                alignment = "left"

        value = self._to_str(value)

        spacer = (spacer[0] * (length - self._get_unicode_width(value)))
        if ( alignment == "left" ):
            result = value + spacer
        if ( alignment == "right" ):
            result = spacer + value

        return result


    def _generate_table_from_list(self, indent=0):
        header = self._header or []
        rows   = self._rows or []

        column_count = max(max([len(v) for v in rows]), len(header))
        length_table = [ [] for x in range(0, column_count) ]

        for i in range(0, len(header)):
            length_table[i].append(self._get_unicode_width(header[i]))

        for row in rows:
            for i in range(0, len(row)):
                length_table[i].append(self._get_unicode_width(row[i]))

        column_lengths = [ max(x) for x in length_table ]

        lines = []
        border = "+" + "-".join([ ("-" * ( x + 2 )) for x in column_lengths ]) + "+"

        if ( len(header) > 0 ):
            lines.append(border)
            header = [ self._padding(header[i] if i < len(header) else "", column_lengths[i]) for i in range(0, len(column_lengths)) ]
            lines.append( "| " + " | ".join(header) + " |" )

        lines.append(border)
        for row in rows:
            row = [ self._padding(row[i] if i < len(row) else "", column_lengths[i]) for i in range(0, len(column_lengths)) ]
            lines.append( "| " + " | ".join(row) + " |" )
        lines.append(border)

        table = (" " * indent) + ("\n" + (" " * indent)).join(lines)

        return table


    def _generate_table_from_dict(self, indent=0):

        header = self._header or []
        rows   = self._rows or []

        if ( len(header) > 0):
            keys = []
            captions = {}
            for h in header:
                if ( isinstance(h, list) or isinstance(h, tuple) ):
                    key = h[0] if len(h) > 0 else ""
                    caption = h[1] if len(h) > 1 else key
                    keys.append(key)
                    captions[key] = caption
                else:
                    keys.append(h)
                    captions[h] = h
        else:
            keys = [ k for r in rows for k in r.keys() ]
            keys = sorted(set(keys), key=keys.index)
            captions = { v:v for v in keys }

        column_lengths = {}
        for key in keys:
            column_lengths[key] = max( self._get_unicode_width(row.get(key, None)) for row in rows )
            column_lengths[key] = max( column_lengths[key], self._get_unicode_width(captions[key]) )

        lines = []
        border = "+" + "-".join([ ("-" * ( x + 2 )) for x in column_lengths.values() ]) + "+"

        lines.append(border)
        header = [ self._padding(captions[key], column_lengths[key]) for key in keys ]
        lines.append( "| " + " | ".join(header) + " |" )

        lines.append(border)
        for row in rows:
            row = [ self._padding(row.get(key, None), column_lengths[key]) for key in keys ]
            lines.append( "| " + " | ".join(row) + " |" )
        lines.append(border)

        table = (" " * indent) + ("\n" + (" " * indent)).join(lines)

        return table


class DatabaseManager():

    def __init__(self, host, port, database, uid, pwd):
        self._connection_string = 'DRIVER={ODBC Driver 17 for SQL Server};' +\
            f'SERVER={host},{port};' + \
            f'DATABASE={database};' + \
            f'UID={uid};' + \
            f'PWD={pwd}'

    def connect_test(self):
        try:
            cnxn = pyodbc.connect(self._connection_string)
            cnxn.close()
            return True
        except pyodbc.DatabaseError as err:
            print(err, file=sys.stderr)
            return False

    def execute(self, sqls):
        if ( type(sqls) is str ):
            sqls = [sqls]

        try:
            cnxn = pyodbc.connect(self._connection_string)
            cursor = cnxn.cursor()
            for sql in sqls:
                if ( len(sql.strip()) == 0 ): continue
                cursor.execute(sql)
            cnxn.commit()
            return True
        except pyodbc.DatabaseError as err:
            print(err, file=sys.stderr)
            cnxn.rollback()
            return False

    def query(self, sql):
        try:

            cnxn = pyodbc.connect(self._connection_string)
            cursor = cnxn.cursor()
            rc = cursor.execute(sql)
            records = cursor.fetchall()
            cnxn.commit()

            import types
            result = types.SimpleNamespace(
                Columns = [ c[0] for c in rc.description ],
                Records = [ [ v for v in r ] for r in records  ]
            )
            return result

        except pyodbc.DatabaseError as err:
            print(err, file=sys.stderr)
            cnxn.rollback()
            return None


def log_info(message, is_silent=False):
    if ( is_silent ): return True
    print(message)

def log_error(message):
    print(f"Error: {message}", file=sys.stderr)

def generate_dbm(config):
    dbm = DatabaseManager(
        host    = config.MSSQL_MIGRATE_DB_HOST,
        port    = config.MSSQL_MIGRATE_DB_PORT,
        database= config.MSSQL_MIGRATE_DB_NAME,
        uid     = config.MSSQL_MIGRATE_DB_USER,
        pwd     = config.MSSQL_MIGRATE_DB_PASS
    )
    return dbm

def import_py_vars(path):
    try:
        import copy
        import types

        fp = open(path, "r")
        py_contents = fp.read()
        fp.close()

        # 読み込み前後の変数リストを保存
        before_vars = copy.copy(vars())
        exec(py_contents)
        after_vars  = copy.copy(vars())

        # 追加・変更された変数のみ抽出
        diff_vars = { k:v for k,v in after_vars.items() if ( k not in before_vars.keys() or  v != before_vars[k] )}
        diff_vars = { k:v for k,v in diff_vars.items() if not isinstance(v, types.ModuleType) }
        del diff_vars["before_vars"]

        result = types.SimpleNamespace()
        for k,v in diff_vars.items():
            setattr(result, k, v)

        return result

    except Exception as e:
        raise e

def get_migration_files(config):

    # パラメータから使用するものを変数に格納
    script_dir = config.MSSQL_MIGRATE_FILE_DIR
    config_path = config.CONFIG_PATH
    config_path_abs = pathlib.Path(config_path).resolve()

    # SCRIPT_DIR の絶対パス
    script_dir_abs = script_dir
    if ( not os.path.isabs(script_dir_abs) ):
        script_dir_abs = os.path.join(os.path.dirname(config_path_abs), script_dir_abs)

    # ファイル一覧を取得。configファイルが含まれていたら除外
    script_paths = list(pathlib.Path(script_dir_abs).glob("*.py"))
    result = [ x for x in script_paths if x.resolve() != config_path_abs ]

    # ファイル一覧を返却
    return result

def get_migration_file_info(path: pathlib.Path):
    file_name = os.path.splitext(path.name)[0]
    id = file_name.split("_")[0:1][0]
    name = "_".join(file_name.split("_")[1:])
    
    hash = None
    if ( path.is_file() ):
        with open(path,'rb') as f:
            hash = hashlib.sha256(f.read()).hexdigest()

    return {
        "file": path,
        "id": id,
        "name" : name,
        "hash": hash,
        "size": path.stat().st_size
    }


def is_schema_exists(config, schema_name):
    ret = generate_dbm(config).query(f"""
        IF EXISTS ( SELECT 'x' FROM sys.schemas WHERE name = N'{schema_name}' )
            SELECT null
        ELSE
            SELECT null WHERE 0=1
    """)
    return ( len(ret.Records) > 0 )

def is_table_exists(config, table_name):

    sql = f"""
        SELECT schemas.name + '.' + tables.name
        FROM sys.objects tables
            INNER JOIN sys.schemas schemas
                ON  tables.schema_id = schemas.schema_id
        WHERE schemas.name + '.' + tables.name = '{table_name}'
    """
    ret = generate_dbm(config).query(sql)

    return ( len(ret.Records) > 0 )

def create_schemas(config, is_dry_run, is_silent):

    dbm =  generate_dbm(config)
    for schema_name in config.MSSQL_MIGRATE_SCHEMA:
        if ( is_schema_exists(config, schema_name) ): continue

        ret = create_schema(config, schema_name, is_dry_run, is_silent)
        if ( not ret ): return False

    return True

def create_schema(config, schema_name, is_dry_run, is_silent):
    if ( is_dry_run ): is_silent = False

    dry_run_caption = " (dry-run)" if is_dry_run else ""
    log_info(f"\n[create schema{dry_run_caption}] `{schema_name}`", is_silent)
    if ( is_dry_run ): return True

    dbm =  generate_dbm(config)
    # ret = dbm.execute(f"""
    #     EXEC('CREATE SCHEMA {schema_name}')
    # """)
    ret = dbm.execute(f"""
        CREATE SCHEMA [{schema_name}]
    """)
    return ret

def create_migrate_table(config, is_dry_run, is_silent):
    if ( is_dry_run ): is_silent = False

    table_name = config.MSSQL_MIGRATE_TABLE
    if ( is_table_exists(config, table_name) ): return True

    dry_run_caption = " (dry-run)" if is_dry_run else ""
    log_info(f"\n[create table{dry_run_caption}] `{table_name}`", is_silent)
    if ( is_dry_run ): return True

    columns = ", ".join([ "[" + x.get("name") + "] " + x.get("type") for x in MIGRATE_TABLE_COLUMNS])
    sql = f"""
        CREATE TABLE {table_name}
        (
            {columns}
            , CONSTRAINT PK_{table_name.replace(".", "_")} PRIMARY KEY CLUSTERED (id)
        )
    """
    ret = generate_dbm(config).execute(sql)
    return ret

def get_migrate_status(config):

    # 管理テーブルのデータを取得
    table_data = []
    if ( is_table_exists(config, config.MSSQL_MIGRATE_TABLE) ):
        dbm = generate_dbm(config)
        table_data = dbm.query(f"""
            SELECT *
            FROM {config.MSSQL_MIGRATE_TABLE}
            ORDER BY
                    id ASC
        """)
        table_data = [ dict(zip(table_data.Columns, r)) for r in table_data.Records ]


    # マイグレーションファイル一覧を取得
    files = get_migration_files(config)
    files = [ get_migration_file_info(p) for p in files ]

    # データを統合＆編集
    migrations_by_id = { r["id"]:r for r in table_data }
    for file_info in files:
        id = file_info["id"]
        if ( id in migrations_by_id.keys() ):
            migrations_by_id[id] = { **migrations_by_id[id] , **file_info }
        else:
            migrations_by_id[id] = file_info
        migrations_by_id[id]["hash_short"] = migrations_by_id[id]["hash"][0:8] + "..."

    # リスト化してソート
    migration_status = [ v for k,v in migrations_by_id.items() ]
    migration_status = sorted(migration_status, key=lambda x:x['id'])

    return migration_status

def apply_migration(config, migration_info, ip_down, is_dry_run, is_silent):
    if ( is_dry_run ): is_silent = False

    migrate_table_name  = config.MSSQL_MIGRATE_TABLE
    user_name           = config.MSSQL_MIGRATE_DB_USER
    dbm                 = generate_dbm(config)

    # print command
    dry_run_caption = " (dry-run)" if is_dry_run else ""
    operation_type  = "down" if ip_down else "up"

    log_info(f"\n[migrate {operation_type}{dry_run_caption}] id=`{migration_info.get('id')}`", is_silent)

    # get migration sql
    path = migration_info.get("file", None)
    if ( path is None ):
        log_error(f"migration-file is not exists.")

    log_info(f"@ {path.relative_to(pathlib.Path().cwd())}", is_silent)

    if ( not path.is_file() ):
        log_error(f"`{path.relative_to(pathlib.Path().cwd())}` is not exists.")
        return False

    migration_vars = import_py_vars(str(path))
    if ( ip_down ):
        migrate_sqls = migration_vars.SQL_DOWN
    else:
        migrate_sqls = migration_vars.SQL_UP

    if ( type(migrate_sqls) is str ): migrate_sqls = [migrate_sqls]
    migrate_sqls = [ x.strip() for x in migrate_sqls ]

    log_info("```", is_silent)
    for sql in migrate_sqls:
        log_info(sql, is_silent)
    log_info("```", is_silent)

    # exit process if dry-run
    if ( args.is_dry_run ):
        return True

    # prepare migrate state
    if ( not ip_down ):
        status_sql = f"""
            DELETE FROM {migrate_table_name} WHERE id = '{migration_info.get('id')}';
        """
        ret = dbm.execute(status_sql)
        if ( not ret ): return False

        status_sql = f"""
            INSERT INTO {migrate_table_name} (id, name, size, hash)
            VALUES ('{migration_info.get('id')}', '{migration_info.get('name')}', {migration_info.get('size')},'{migration_info.get('hash')}');
        """
        ret = dbm.execute(status_sql)
        if ( not ret ): return False

    # execute migration sql
    ret = dbm.execute(migrate_sqls)
    if ( not ret ): return False

    # update migrate state
    if ( ip_down ):
        status_sql = f"""
            UPDATE {migrate_table_name}
            SET
                    applied_date = null
                ,   applied_user = null
            WHERE
                id = '{migration_info.get('id')}';
        """
    else:
        status_sql = f"""
            UPDATE {migrate_table_name}
            SET
                    applied_date = SYSDATETIMEOFFSET()
                ,   applied_user = '{user_name}'
            WHERE
                id = '{migration_info.get('id')}';
        """
    ret = dbm.execute(status_sql)
    if ( not ret ): return False

    return True

def print_migrate_status(config):
    migration_status = get_migrate_status(config)

    table = SimpleTable()
    table.set_header(MIGRATE_SHOW_STATUS_HEADER)
    table.set_rows(migration_status)
    table.print_table()


def subcmd_migrate_status(args, config):
    print_migrate_status(config)
    return 0

def subcmd_migrate_new(args, config):
    now = datetime.datetime.now()
    dt_str = now.strftime('%Y%m%d%H%M%S')
    output_path = f"{config.MSSQL_MIGRATE_FILE_DIR.rstrip('/')}/{dt_str}_{args.name}.py"
    log_info(output_path)

    lines = []
    lines.append('')
    lines.append('SQL_UP=[')
    lines.append('  "Write SQL here;",')
    lines.append('  "Write SQL here;",')
    lines.append('  "Write SQL here;"')
    lines.append(']')
    lines.append('')
    lines.append('SQL_DOWN=[')
    lines.append('  "Write SQL here;",')
    lines.append('  "Write SQL here;",')
    lines.append('  "Write SQL here;"')
    lines.append(']')
    lines.append('')

    with open(output_path, mode='w') as f:
        f.write("\n".join(lines))

    return 0

def subcmd_migrate_up(args, config):

    ret = create_schemas(config, args.is_dry_run, args.is_silent)
    if ( not ret ): return 1

    if ( args.is_schema_only ):
        return 0

    ret = create_migrate_table(config, args.is_dry_run, args.is_silent)
    if ( not ret ): return 1

    migrate_status = get_migrate_status(config)

    apply_limit = args.limit if args.limit > 0 else -1
    for migration_info in migrate_status:
        id = migration_info['id']
        if ( migration_info.get("applied_date", None) is not None ):
            continue

        ret = apply_migration(config, migration_info, False, args.is_dry_run, args.is_silent)
        if ( not ret ):
            return 1

        apply_limit = apply_limit - 1
        if ( apply_limit == 0 ):
            break

    if ( not ( args.is_silent and not args.is_dry_run) ):
        print("\n[result]")
        print_migrate_status(config)

    return 0

def subcmd_migrate_down(args, config):

    migrate_status = get_migrate_status(config)
    migrate_status = reversed(migrate_status)

    apply_limit = args.limit if args.limit > 0 else -1
    for migration_info in migrate_status:
        id = migration_info['id']
        if ( migration_info.get("applied_date", None) is None ):
            continue

        ret = apply_migration(config, migration_info, True, args.is_dry_run, args.is_silent)
        if ( not ret ):
            return 1

        apply_limit = apply_limit - 1
        if ( apply_limit == 0 ):
            break

    if ( not ( args.is_silent and not args.is_dry_run) ):
        print("\n[result]")
        print_migrate_status(config)

    return 0


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Database migration tool for MSSQL")
    subparsers = parser.add_subparsers(required=True)

    args_limit_up  = {
        "args"   : ['limit'],
        "kwargs" : {
            "type"    : int,
            "nargs"   : "?",
            "default" : 0,
            "help"    : 'Limit the number of migrations (0 = unlimited). [default = 0]'
        }
    }

    args_limit_down = copy.deepcopy(args_limit_up)
    args_limit_down["kwargs"]["default"] = 1
    args_limit_down["kwargs"]["help"] = 'Limit the number of migrations (0 = unlimited). [default = 1]'
    
    args_config = {
        "args"   : ['-c', '--config'],
        "kwargs" : {
            "dest"    : "config",
            "metavar" : "PATH",
            "type"    : str,
            "required": False,
            "default" : DEFAULT_CONFIG_PATH,
            "help"    : f'configuration file to use. (default: `{DEFAULT_CONFIG_PATH}`)'
        }
    }
    args_dryrun = {
        "args"   : ['--dry-run'],
        "kwargs" : {
            "dest"    : "is_dry_run",
            "required": False,
            "default" : False,
            "action"  : "store_true",
            "help"    : 'do not apply. SQL display only.'
        }
    }
    args_silent = {
        "args"   : ['-s', '--silent'],
        "kwargs" : {
            "dest"    : "is_silent",
            "required": False,
            "default" : False,
            "action"  : "store_true",
            "help"    : 'do not display execution log.'
        }
    }

    parser_status = subparsers.add_parser('status', help='show migrate history')
    parser_status.set_defaults(func=subcmd_migrate_status)
    parser_status.add_argument(*args_config['args'], **args_config['kwargs'])

    parser_new = subparsers.add_parser('new', help='creates a new empty migration template')
    parser_new.set_defaults(func=subcmd_migrate_new)
    parser_new.add_argument('name', metavar="NAME", type=str, help='migration-name')
    parser_new.add_argument(*args_config['args'], **args_config['kwargs'])

    parser_up = subparsers.add_parser('up', help='migration up')
    parser_up.set_defaults(func=subcmd_migrate_up)
    parser_up.add_argument(*args_limit_up['args'], **args_limit_up['kwargs'])
    parser_up.add_argument(*args_config['args'], **args_config['kwargs'])
    parser_up.add_argument(*args_dryrun['args'], **args_dryrun['kwargs'])
    parser_up.add_argument(*args_silent['args'], **args_silent['kwargs'])
    parser_up.add_argument(
        '--schema-only',
        dest        = "is_schema_only",
        required    = False,
        default     = False,
        action      = "store_true",
        help        = 'schema creation only. do not apply migrations.'
    )

    parser_down = subparsers.add_parser('down', help='migration down')
    parser_down.set_defaults(func=subcmd_migrate_down)
    parser_down.add_argument(*args_limit_down['args'], **args_limit_down['kwargs'])
    parser_down.add_argument(*args_config['args'], **args_config['kwargs'])
    parser_down.add_argument(*args_dryrun['args'], **args_dryrun['kwargs'])
    parser_down.add_argument(*args_silent['args'], **args_silent['kwargs'])


    # Show help if there are no subcommands
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    # parse & Call a subcommand function
    args = parser.parse_args()

    # import config
    if ( not os.path.isfile(args.config) ):
        log_error(f"config-file `{args.config}` is not found.")
        sys.exit(1)

    config = import_py_vars(args.config)
    config.CONFIG_PATH  = args.config
    config.MSSQL_MIGRATE_SCHEMA = getattr(config, "MSSQL_MIGRATE_SCHEMA", [])
    if ( isinstance(config.MSSQL_MIGRATE_SCHEMA, str)):
        config.MSSQL_MIGRATE_SCHEMA = config.MSSQL_MIGRATE_SCHEMA.split(",")
    config.MSSQL_MIGRATE_SCHEMA = list(map(str.strip, config.MSSQL_MIGRATE_SCHEMA))
    config.MSSQL_MIGRATE_SCHEMA = list(filter(lambda a: a != "", config.MSSQL_MIGRATE_SCHEMA))


    # call subcommand function
    ret = args.func(args, config)

    sys.exit(ret)
