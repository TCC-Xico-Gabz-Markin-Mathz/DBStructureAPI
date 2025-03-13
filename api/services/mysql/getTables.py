from mysql.connector.abstracts import MySQLCursorAbstract
from api.models.columnModels import ColumnModel
from api.models.tableModels import TableModel
from api.services.mysql.connection import MySQL

def getTables(database: str) -> None | list[TableModel]:
    mysql = MySQL()
    cursor: MySQLCursorAbstract | None = None
    result: list[TableModel] = []

    try:
        mysql.connect(database=database)
        cursor = mysql.connection.cursor(dictionary=True)

        cursor.execute("SHOW TABLES;")
        tables = cursor.fetchall()

        for table in tables:
            table_name = table[f"Tables_in_{database}"]
            query = f"""
                    SELECT 
                        COLUMN_NAME, 
                        COLUMN_KEY, 
                        IS_NULLABLE, 
                        COLUMN_TYPE, 
                        COLUMN_DEFAULT, 
                        EXTRA
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = '{database}' AND TABLE_NAME = '{table_name}';
                """
            cursor.execute(query)
            columns = cursor.fetchall()

            table_info = TableModel(
                table_name=table_name,
                columns=[]
            )

            for col in columns:
                col['IS_PRIMARY'] = col['COLUMN_KEY'] == 'PRI'

                cursor.execute(f"""
                        SELECT REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME 
                        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
                        WHERE TABLE_SCHEMA = '{database}' AND TABLE_NAME = '{table_name}' AND COLUMN_NAME = '{col['COLUMN_NAME']}' 
                        AND REFERENCED_TABLE_NAME IS NOT NULL;
                    """)
                foreign_key = cursor.fetchone()

                if foreign_key:
                    col['IS_FOREIGN'] = True
                    col['REFERENCED_TABLE'] = foreign_key['REFERENCED_TABLE_NAME']
                    col['REFERENCED_COLUMN'] = foreign_key['REFERENCED_COLUMN_NAME']
                else:
                    col['IS_FOREIGN'] = False
                    col['REFERENCED_TABLE'] = None
                    col['REFERENCED_COLUMN'] = None

                new_column_info = ColumnModel(
                    name=col['COLUMN_NAME'],
                    is_nullable=col['IS_NULLABLE'],
                    type=col['COLUMN_TYPE'],
                    default=col['COLUMN_DEFAULT'],
                    extra=col['EXTRA'],
                    is_primary_key=col['IS_PRIMARY'],
                    is_foreign_key=col['IS_FOREIGN'],
                    referenced_table=col['REFERENCED_TABLE'],
                    referenced_column=col['REFERENCED_COLUMN'],
                )

                table_info.columns.append(new_column_info)

            result.append(table_info)

        return result

    except Exception as e:
        raise e

    finally:
        if cursor:
            cursor.close()
        mysql.close_connection()
