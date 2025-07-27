from fastapi import HTTPException
from api.common.services.mysql.connection import MySQL
from mysql.connector.abstracts import MySQLCursorAbstract


def execute_sql_query(database: str, query: str):
    mysql = MySQL()
    cursor: MySQLCursorAbstract | None = None

    try:
        mysql.connect(database=database)
        cursor = mysql.connection.cursor(dictionary=True)

        cursor.execute(query)
        result = cursor.fetchall()  # Recupera todos os resultados

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao executar a query: {e}")

    finally:
        if cursor:
            cursor.close()
        mysql.close_connection()
