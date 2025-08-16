import os
import docker
import mysql.connector
import time
import socket


class MySQLTestInstance:
    def __init__(self, root_password="root123", db_name="testdb"):
        self.db_name = db_name
        self.root_password = root_password
        self.container = None
        self.conn = None
        self.cursor = None
        self.assigned_port = 3307  # Porta padrão, pode ser alterada dinamicamente

    def start_instance(self):
        """Inicia o container MySQL e aguarda o MySQL estar pronto - Adaptado para EasyPanel."""
        try:
            client = docker.from_env()
            print("Iniciando o container MySQL no EasyPanel...")

            # Verificar se Docker está acessível
            try:
                client.ping()
                print("Docker daemon acessível.")
            except Exception as e:
                print(f"ERRO: Docker daemon não acessível: {e}")
                print(
                    "Certifique-se de que /var/run/docker.sock está montado no container."
                )
                raise

            # Limpar container existente
            try:
                existing_container = client.containers.get("mysql-test-instance")
                print("Container existente encontrado, removendo...")
                existing_container.stop(timeout=10)
                existing_container.remove()
                time.sleep(3)
            except docker.errors.NotFound:
                print("Nenhum container existente encontrado.")
            except Exception as e:
                print(f"Aviso ao remover container: {e}")

            # Verificar se a porta está disponível
            if self._is_port_available(3307):
                self.assigned_port = 3307
            elif self._is_port_available(3308):
                self.assigned_port = 3308
            else:
                # Deixar Docker escolher uma porta aleatória
                self.assigned_port = None

            print(f"Usando porta: {self.assigned_port or 'automática'}")

            # Configurar volumes apenas se my.cnf existir
            volumes = {}
            config_path = os.path.abspath("my.cnf")
            if os.path.exists(config_path):
                print(f"Usando configuração personalizada: {config_path}")
                volumes = {
                    config_path: {
                        "bind": "/etc/mysql/conf.d/my.cnf",
                        "mode": "ro",
                    }
                }
            else:
                print("Arquivo my.cnf não encontrado, usando configuração padrão.")

            # Criar container com configurações adaptadas para EasyPanel
            self.container = client.containers.run(
                "mysql:8",
                name="mysql-test-instance",
                environment={
                    "MYSQL_ROOT_PASSWORD": self.root_password,
                    "MYSQL_DATABASE": self.db_name,
                    "MYSQL_ROOT_HOST": "%",  # Permitir conexões de qualquer host
                    "MYSQL_INITDB_SKIP_TZINFO": "1",  # Evitar problemas de timezone
                },
                ports={"3306/tcp": self.assigned_port},
                volumes=volumes,
                detach=True,
                remove=True,
                network_mode="bridge",
                # Configurações adicionais para estabilidade
                mem_limit="512m",  # Limitar memória
                restart_policy={"Name": "no"},
            )

            # Se porta foi automática, descobrir qual foi atribuída
            if self.assigned_port is None:
                self.container.reload()
                port_info = self.container.attrs["NetworkSettings"]["Ports"]["3306/tcp"]
                if port_info and len(port_info) > 0:
                    self.assigned_port = int(port_info[0]["HostPort"])
                    print(f"Porta automática atribuída: {self.assigned_port}")

            print(f"Container MySQL criado com ID: {self.container.id}")
            print("Aguardando MySQL iniciar...")
            self.wait_for_mysql()

        except docker.errors.APIError as e:
            print(f"Erro da API Docker: {e}")
            if "Cannot connect to the Docker daemon" in str(e):
                print("SOLUÇÃO: Monte o Docker socket no EasyPanel:")
                print("Advanced → Mounts → /var/run/docker.sock:/var/run/docker.sock")
            elif "port is already allocated" in str(e):
                print("SOLUÇÃO: Porta em uso, tentando porta alternativa...")
                self.assigned_port = None
                return self.start_instance()  # Tentar novamente
            raise
        except Exception as e:
            print(f"Erro geral: {e}")
            raise

    def _is_port_available(self, port):
        """Verifica se uma porta está disponível."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(("localhost", port))
            sock.close()
            return result != 0
        except:
            return False

    def wait_for_mysql(self):
        """Função para garantir que o MySQL esteja pronto para conexão - Versão melhorada."""
        max_retries = 30  # Aumentar tentativas para ambientes mais lentos
        retry_delay = 5

        print(f"Aguardando MySQL na porta {self.assigned_port}...")

        for attempt in range(max_retries):
            try:
                # Verificar se container ainda está rodando
                self.container.reload()
                if self.container.status != "running":
                    print(
                        f"Container não está rodando. Status: {self.container.status}"
                    )
                    # Mostrar logs para debug
                    self._show_container_logs()
                    raise Exception("Container MySQL parou de funcionar")

                # Verificar se porta está respondendo
                if not self._check_port_connection():
                    raise Exception("Porta MySQL não está respondendo")

                # Tentar conectar ao MySQL
                print(f"Tentativa {attempt + 1}: Conectando ao MySQL...")
                self.conn = mysql.connector.connect(
                    host="localhost",
                    port=self.assigned_port,
                    user="root",
                    password=self.root_password,
                    database=self.db_name,
                    connect_timeout=10,
                    autocommit=True,
                )
                print("Conexão MySQL bem-sucedida!")
                return

            except mysql.connector.Error as err:
                print(f"Erro MySQL (tentativa {attempt + 1}): {err}")
            except Exception as e:
                print(f"Erro geral (tentativa {attempt + 1}): {e}")

            if attempt < max_retries - 1:
                print(f"Aguardando {retry_delay}s antes da próxima tentativa...")
                time.sleep(retry_delay)

        # Se chegou aqui, falhou
        self._show_container_logs()
        raise Exception("Não foi possível conectar ao MySQL após várias tentativas")

    def _check_port_connection(self):
        """Verifica se a porta MySQL está respondendo."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex(("localhost", self.assigned_port))
            sock.close()
            return result == 0
        except:
            return False

    def _show_container_logs(self):
        """Mostra logs do container para debug."""
        try:
            if self.container:
                logs = self.container.logs(tail=30).decode("utf-8", errors="ignore")
                print("=== LOGS DO MYSQL ===")
                print(logs)
                print("=== FIM DOS LOGS ===")
        except Exception as e:
            print(f"Não foi possível obter logs: {e}")

    def test_connection(self):
        if not self.conn:
            raise Exception("Não há conexão com o banco de dados!")

        print("Testando conexão ao banco de dados...")
        self.cursor = self.conn.cursor()
        self.cursor.execute("SELECT 1;")
        result = self.cursor.fetchall()
        return result

    def delete_instance(self):
        print("Finalizando instância MySQL...")

        if self.cursor:
            try:
                self.cursor.close()
                print("Cursor fechado.")
            except:
                pass
            self.cursor = None

        if self.conn:
            try:
                self.conn.close()
                print("Conexão MySQL fechada.")
            except:
                pass
            self.conn = None

        if self.container:
            try:
                print("Parando container MySQL...")
                self.container.reload()
                if self.container.status == "running":
                    self.container.stop(timeout=10)
                    print("Container parado.")

                # Container será removido automaticamente (remove=True)
            except Exception as e:
                print(f"Aviso ao parar container: {e}")

            self.container = None

    def execute_sql_statements(self, statements: list[str]):
        if not self.conn:
            raise Exception("Não há conexão com o banco de dados!")

        self.cursor = self.conn.cursor()
        for stmt in statements:
            try:
                print(f"Executando: {stmt[:50]}...")
                self.cursor.execute(stmt)

                if self.cursor.with_rows:
                    self.cursor.fetchall()

            except mysql.connector.Error as err:
                print(f"Erro ao executar comando: {err}")
                raise

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
        print(f"Executando: {query[:50]}...")
        if not self.conn:
            raise Exception("Sem conexão com o banco.")

        self.cursor = self.conn.cursor()
        self.cursor.execute(query)
        try:
            result = self.cursor.fetchall()
            self.conn.commit()
            return result
        except mysql.connector.InterfaceError:
            self.conn.commit()
            return "Query executada com sucesso (sem retorno)"

    # Métodos auxiliares para EasyPanel
    def start_instance_fallback(self):
        """Método alternativo caso o principal falhe."""
        try:
            client = docker.from_env()
            print("Tentando método alternativo...")

            # Usar configuração mínima
            self.container = client.containers.run(
                "mysql:8",
                name=f"mysql-test-{int(time.time())}",  # Nome único
                environment={
                    "MYSQL_ROOT_PASSWORD": self.root_password,
                    "MYSQL_DATABASE": self.db_name,
                    "MYSQL_ROOT_HOST": "%",
                },
                ports={"3306/tcp": None},  # Porta automática
                detach=True,
                remove=True,
            )

            # Descobrir porta atribuída
            self.container.reload()
            port_info = self.container.attrs["NetworkSettings"]["Ports"]["3306/tcp"]
            self.assigned_port = int(port_info[0]["HostPort"])

            print(f"MySQL iniciado na porta {self.assigned_port} (método alternativo)")
            self.wait_for_mysql()

        except Exception as e:
            print(f"Método alternativo também falhou: {e}")
            raise

    def get_container_info(self):
        """Retorna informações do container para debug."""
        if not self.container:
            return "Nenhum container ativo"

        try:
            self.container.reload()
            return {
                "id": self.container.id,
                "status": self.container.status,
                "ports": self.container.ports,
                "name": self.container.name,
            }
        except Exception as e:
            return f"Erro ao obter info: {e}"
