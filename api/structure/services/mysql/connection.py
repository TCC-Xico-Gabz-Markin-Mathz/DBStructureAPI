import os
import mysql.connector
from mysql.connector import Error
from mysql.connector.abstracts import MySQLConnectionAbstract
from mysql.connector.pooling import PooledMySQLConnection
from starlette import status
from starlette.exceptions import HTTPException


class MySQL:
    def __init__(self):
        self.connection: PooledMySQLConnection | MySQLConnectionAbstract | None = None

    def database_exists(self, database: str) -> bool:
        try:
            temp_connection = mysql.connector.connect(
                host=os.getenv("MYSQL_HOST"),
                user=os.getenv("MYSQL_USER"),
                password=os.getenv("MYSQL_PASSWORD"),
            )
            cursor = temp_connection.cursor()
            cursor.execute("SHOW DATABASES")
            databases = [db[0] for db in cursor.fetchall()]
            cursor.close()
            temp_connection.close()
            return database in databases
        except Error as e:
            print(f"Error while checking database existence: {e}")
            return False

    def connect(self, database: str):
        if not self.database_exists(database):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Database '{database}' does not exist."
            )

        try:
            self.connection = mysql.connector.connect(
                host=os.getenv("MYSQL_HOST"),
                user=os.getenv("MYSQL_USER"),
                password=os.getenv("MYSQL_PASSWORD"),
                database=database,
            )

            if self.connection.is_connected():
                print("Successfully connected to the database")
                return None
        except Error as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error while connecting to MySQL: {e}"
            )

    def close_connection(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
            self.connection = None
            print("MySQL connection closed")
