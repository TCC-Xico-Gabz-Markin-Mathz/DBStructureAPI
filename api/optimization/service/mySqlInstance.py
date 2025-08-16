import docker
import mysql.connector
import time


class MySQLTestInstance:
    def __init__(
        self,
        root_password="root123",
        db_name="testdb",
        container_name="mysql-test-instance",
    ):
        self.db_name = db_name
        self.root_password = root_password
        self.container_name = container_name
        self.container = None
        self.conn = None
        self.cursor = None

    def start_instance(self):
        """Inicia o container MySQL na porta 33060."""
        client = docker.from_env()
        print("Verificando se o container de teste já existe...")
        try:
            # Tenta encontrar e remover um container com o mesmo nome
            existing_container = client.containers.get(self.container_name)
            print(f"Container '{self.container_name}' encontrado. Removendo...")
            existing_container.remove(force=True)
            time.sleep(2)  # Pequena pausa para garantir a remoção
        except docker.errors.NotFound:
            print(
                f"Nenhum container com o nome '{self.container_name}' encontrado. Prosseguindo..."
            )
        except docker.errors.APIError as e:
            print(
                f"Erro ao tentar remover o container: {e}. Prosseguindo com a criação..."
            )

        print("Iniciando o container MySQL na porta 33060...")
        self.container = client.containers.run(
            "mysql:5.7",  # MySQL 5.7 é mais rápido que 8.0
            name=self.container_name,
            environment={
                "MYSQL_ROOT_PASSWORD": self.root_password,
                "MYSQL_DATABASE": self.db_name,
            },
            ports={"3306/tcp": 33060},  # ← Mapeia para porta 33060
            detach=True,
            remove=True,
        )
        print("Container MySQL iniciado. Aguardando inicialização...")
        self.wait_for_mysql()

    def wait_for_mysql(self):
        """Aguarda MySQL estar pronto na porta 33060"""
        print("Aguardando MySQL inicializar...")
        time.sleep(30)  # MySQL 5.7 ainda precisa de tempo para inicializar

        retries = 15
        for i in range(retries):
            try:
                print(f"Tentativa {i + 1}/{retries} - Conectando em localhost:33060...")
                self.conn = mysql.connector.connect(
                    host="localhost",
                    port=33060,  # ← Usa porta 33060
                    user="root",
                    password=self.root_password,
                    database=self.db_name,
                    connect_timeout=30,
                    autocommit=True,
                )
                print("✅ Conexão MySQL estabelecida na porta 33060!")
                return
            except mysql.connector.Error as err:
                print(f"❌ Erro: {err}")
                time.sleep(10)  # Aguarda 10 segundos entre tentativas

        raise Exception(
            "Não foi possível conectar ao MySQL na porta 33060 após várias tentativas"
        )

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
