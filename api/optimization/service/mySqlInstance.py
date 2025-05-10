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
        print("Iniciando o container MySQL...")
        self.container = client.containers.run(
            "mysql:8",  # Imagem do MySQL 8
            name="mysql-test-instance",
            environment={
                "MYSQL_ROOT_PASSWORD": self.root_password,
                "MYSQL_DATABASE": self.db_name,  # Nome do banco de dados
            },
            ports={"3306/tcp": 3307},  # Mapear a porta 3306
            detach=True,
            remove=True,
        )
        # Espera para garantir que o MySQL esteja inicializado
        print("Aguardando MySQL iniciar...")
        self.wait_for_mysql()

    def wait_for_mysql(self):
        """Função para garantir que o MySQL esteja pronto para conexão"""
        retries = 10
        for _ in range(retries):
            try:
                # Tentativa de conectar ao MySQL
                print("Tentando conectar ao MySQL...")
                self.conn = mysql.connector.connect(
                    host="localhost",
                    port=3307,
                    user="root",
                    password=self.root_password,
                    database=self.db_name,
                )
                print("Conexão bem-sucedida!")
                return
            except mysql.connector.Error as err:
                print(f"Erro ao conectar: {err}")
                time.sleep(10)  # Espera de 5 segundos antes de tentar novamente

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
        print(self.container)
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
