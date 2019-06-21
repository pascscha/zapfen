import sqlite3
from sqlite3 import Error


def create_connection(db_file):
    """ create a database connection to a SQLite database """
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)
    return None


def create_table(conn, create_table_sql):
    """ create a table from the create_table_sql statement
    :param conn: Connection object
    :param create_table_sql: a CREATE TABLE statement
    :return:
    """
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except Error as e:
        print(e)


def execute_command(db_file, command):
    """ create a database connection to a SQLite database """
    try:
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()
        cur.execute(command)
        conn.commit()
    except Error as e:
        print(e)
    finally:
        conn.close()
    return None


sql_delete_drinks_table = """DROP TABLE drinks;"""
sql_create_drinks_table = """ CREATE TABLE IF NOT EXISTS drinks (
                                id integer PRIMARY KEY,
                                name text NOT NULL,
                                vol number NOT NULL
                            ); """

sql_delete_users_table = """DROP TABLE users;"""
sql_create_users_table = """ CREATE TABLE IF NOT EXISTS users (
                                id integer PRIMARY KEY,
                                name text NOT NULL,
                                weight number,
                                is_female boolean
                            ); """

sql_delete_consumptions_table = """DROP TABLE consumptions;"""
sql_create_consumptions_table = """CREATE TABLE IF NOT EXISTS consumptions (
                                id integer PRIMARY KEY autoincrement,
                                user_id integer NOT NULL,
                                drink_id integer NOT NULL,
                                amount number NOT NULL,
                                ts timestamp NOT NULL,
                                command text NOT NULL,
                                precision number NOT NULL,
                                deleted boolean NOT NULL,
                                FOREIGN KEY (user_id) REFERENCES users (id),
                                FOREIGN KEY (drink_id) REFERENCES drinks (id)
                                ); """

db_file = "zapfen.db"
conn = create_connection(db_file)
create_table(conn, sql_delete_drinks_table)
create_table(conn, sql_create_drinks_table)
#create_table(conn, sql_delete_users_table)
create_table(conn, sql_create_users_table)
create_table(conn, sql_delete_consumptions_table)
create_table(conn, sql_create_consumptions_table)

execute_command(db_file, "INSERT INTO drinks (id,name,vol) VALUES (0, 'Bier',5);")
execute_command(db_file, "INSERT INTO drinks (id,name,vol) VALUES (1, 'Drink',10);")
execute_command(db_file, "INSERT INTO drinks (id,name,vol) VALUES (2, 'Shot',35);")
execute_command(db_file, "INSERT INTO drinks (id,name,vol) VALUES (3, 'Wine',15);")
