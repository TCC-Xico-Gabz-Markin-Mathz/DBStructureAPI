import os
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
        """Inicia o container MySQL e aguarda o MySQL estar pronto."""
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

        print("Iniciando o container MySQL...")
        self.container = client.containers.run(
            "mysql:8",
            name=self.container_name,  # Usa o nome da instância
            environment={
                "MYSQL_ROOT_PASSWORD": self.root_password,
                "MYSQL_DATABASE": self.db_name,
            },
            ports={"3306/tcp": 3307},
            volumes={
                f"{os.path.abspath('my.cnf')}": {
                    "bind": "/etc/mysql/conf.d/my.cnf",
                    "mode": "ro",
                }
            },
            detach=True,
            remove=True,
        )
        print("Aguardando MySQL iniciar...")
        self.wait_for_mysql()

    def wait_for_mysql(self):
        """Procura o container MySQL e informa onde ele está, então conecta"""
        client = docker.from_env()
        retries = 15

        print(f"Procurando container '{self.container_name}'...")

        for attempt in range(retries):
            try:
                # Procurar o container
                container = client.containers.get(self.container_name)

                # Informações sobre onde o container está
                print(f"✅ Container encontrado!")
                print(f"📍 Status: {container.status}")
                print(f"📍 ID: {container.short_id}")

                # Pegar informações de rede
                container.reload()  # Refresh das informações
                network_settings = container.attrs["NetworkSettings"]

                print(f"📍 IP interno: {network_settings.get('IPAddress', 'N/A')}")

                # Pegar mapeamento de portas
                ports = network_settings.get("Ports", {})
                mysql_port_info = ports.get("3306/tcp", [])

                if mysql_port_info:
                    for port_mapping in mysql_port_info:
                        host_ip = port_mapping.get("HostIp", "0.0.0.0")
                        host_port = port_mapping.get("HostPort")
                        print(
                            f"📍 Porta mapeada: {host_ip}:{host_port} -> container:3306"
                        )

                # Verificar se o container está rodando
                if container.status != "running":
                    print(f"⚠️ Container não está rodando (status: {container.status})")
                    time.sleep(5)
                    continue

                # Tentar conectar usando diferentes possibilidades
                connection_configs = [
                    # Tenta com localhost e porta mapeada
                    {
                        "host": "localhost",
                        "port": 3307,
                        "description": "localhost:3307 (porta mapeada)",
                    },
                    # Tenta com 127.0.0.1 e porta mapeada
                    {
                        "host": "127.0.0.1",
                        "port": 3307,
                        "description": "127.0.0.1:3307",
                    },
                    # Tenta com IP interno do container
                    {
                        "host": network_settings.get("IPAddress", "localhost"),
                        "port": 3306,
                        "description": f"IP interno {network_settings.get('IPAddress')}:3306",
                    },
                ]

                for config in connection_configs:
                    try:
                        print(
                            f"🔄 Tentativa {attempt + 1}/{retries} - Testando {config['description']}..."
                        )

                        self.conn = mysql.connector.connect(
                            host=config["host"],
                            port=config["port"],
                            user="root",
                            password=self.root_password,
                            database=self.db_name,
                            connection_timeout=10,
                        )

                        print(f"✅ Conexão bem-sucedida via {config['description']}!")
                        return

                    except mysql.connector.Error as err:
                        print(f"❌ Falha em {config['description']}: {err}")
                        continue

                print("⏳ Todas as tentativas de conexão falharam, aguardando...")
                time.sleep(10)

            except docker.errors.NotFound:
                print(f"❌ Container '{self.container_name}' não encontrado!")
                print("🔍 Containers disponíveis:")

                # Listar todos os containers
                all_containers = client.containers.list(all=True)
                for c in all_containers:
                    status_emoji = "🟢" if c.status == "running" else "🔴"
                    print(f"   {status_emoji} {c.name} ({c.status}) - {c.short_id}")

                time.sleep(5)

            except docker.errors.APIError as e:
                print(f"❌ Erro na API Docker: {e}")
                time.sleep(5)

            except Exception as e:
                print(f"❌ Erro inesperado: {e}")
                time.sleep(5)

        raise Exception(f"Não foi possível conectar ao MySQL após {retries} tentativas")

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
