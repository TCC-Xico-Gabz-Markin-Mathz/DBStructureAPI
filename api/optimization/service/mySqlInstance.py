import os
import docker
import mysql.connector
import time


class MySQLTestInstance:
    def __init__(self, root_password="root123", db_name="testdb"):
        self.db_name = db_name
        self.root_password = root_password
        self.container = None
        self.conn = None
        self.cursor = None

    def start_instance(self):
        """Inicia o container MySQL e aguarda o MySQL estar pronto."""
        client = docker.from_env()

        try:
            old = client.containers.get("mysql-test-instance")
            print("Container antigo encontrado. Removendo...")
            old.stop()
            old.remove(force=True)
        except docker.errors.NotFound:
            pass  # não existia, segue tranquilo

        print("Iniciando o container MySQL...")
        self.container = client.containers.run(
            "mysql:8",  # Imagem do MySQL 8
            name="mysql-test-instance",
            environment={
                "MYSQL_ROOT_PASSWORD": self.root_password,
                "MYSQL_DATABASE": self.db_name,  # Nome do banco de dados
            },
            ports={"3306/tcp": 3307},  # Mapear a porta 3306
            volumes={
                f"{os.path.abspath('my.cnf')}": {
                    "bind": "/etc/mysql/conf.d/my.cnf",
                    "mode": "ro",
                }
            },
            detach=True,
            remove=True,
            network="easypanel-tcc",
        )
        # Espera para garantir que o MySQL esteja inicializado
        print("Aguardando MySQL iniciar...")
        self.wait_for_mysql()

    def wait_for_mysql(self):
        """Função para garantir que o MySQL esteja pronto para conexão"""
        retries = 5
        for _ in range(retries):
            try:
                # Tentativa de conectar ao MySQL
                print("Tentando conectar ao MySQL...")
                self.conn = mysql.connector.connect(
                    host="mysql-test-instance",
                    port=3306,
                    user="root",
                    password=self.root_password,
                    database=self.db_name,
                )
                print("Conexão bem-sucedida!")
                return
            except mysql.connector.Error as err:
                print(f"Erro ao conectar: {err}")
                time.sleep(25)  # Espera de 5 segundos antes de tentar novamente

        raise Exception("Não foi possível conectar ao MySQL após várias tentativas")

    def test_connection(self):
        if not self.conn:
            raise Exception("Não há conexão com o banco de dados!")

        print("Testando conexão ao banco de dados...")
        self.cursor = self.conn.cursor()
        self.cursor.execute("SELECT 1;")
        result = self.cursor.fetchall()
        return result

    def delete_instance(self):
        if self.container:
            print("Verificando o status do container...")
            try:
                self.container.reload()  # Atualiza o status real
                if self.container.status == "running":
                    print("Parando o container MySQL...")
                    self.container.stop(timeout=5)
            except Exception as e:
                print(f"Erro ao tentar parar o container: {e}")

            self.container = None

        if self.cursor:
            self.cursor.close()
            self.cursor = None

        if self.conn:
            self.conn.close()
            self.conn = None

    def execute_sql_statements(self, statements: list[str]):
        if not self.conn:
            raise Exception("Não há conexão com o banco de dados!")

        self.cursor = self.conn.cursor()
        for stmt in statements:
            try:
                print(f"Executando: {stmt}...")
                self.cursor.execute(stmt)

                if self.cursor.with_rows:
                    self.cursor.fetchall()

            except mysql.connector.Error as err:
                print(f"Erro ao executar comando: {err}")

        self.conn.commit()

    def run_test(self):
        """Executa o teste de criação, conexão e deleção da instância do MySQL."""
        try:
            # Iniciar a instância do MySQL
            self.start_instance()
            # Testar a conexão
            connection_test_result = self.test_connection()
            return {"connection_test_result": connection_test_result}
        finally:
            # Deletar a instância após o teste
            self.delete_instance()

    def execute_raw_query(self, query: str):
        print(f"Executando: {query}...")
        if not self.conn:
            raise Exception("Sem conexão com o banco.")

        self.cursor = self.conn.cursor()
        self.cursor.execute(query)
        try:
            result = self.cursor.fetchall()
            self.conn.commit()
            return result
        except mysql.connector.InterfaceError:
            return "Query executada com sucesso (sem retorno)"
