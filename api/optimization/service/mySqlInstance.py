import os
import docker
import mysql.connector
import time
import socket
import subprocess
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MySQLTestInstance:
    def __init__(self, root_password="root123", db_name="testdb"):
        self.db_name = db_name
        self.root_password = root_password
        self.container = None
        self.conn = None
        self.cursor = None
        self.port = None
        self.container_ip = None

        # Check environment
        self.check_environment()

    def check_environment(self):
        """Check if we're running in a server environment like EasyPanel"""
        self.is_server_environment = self._detect_server_environment()
        logger.info(f"Server environment detected: {self.is_server_environment}")

    def _detect_server_environment(self):
        """Detect if running on server vs local"""
        indicators = [
            not os.path.exists("/Applications"),  # Not macOS
            os.path.exists("/etc/systemd"),  # Systemd (Linux server)
            os.environ.get("EASYPANEL_ENV"),  # EasyPanel specific
            os.environ.get("DOCKER_HOST"),  # Remote Docker
        ]
        return any(indicators)

    def find_available_port(self, start_port=33306):
        """Find available port, starting from higher range for servers"""
        base_port = start_port if self.is_server_environment else 3307

        for port in range(base_port, base_port + 50):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    # Try to bind to 0.0.0.0 for server environments
                    bind_host = "0.0.0.0" if self.is_server_environment else "localhost"
                    s.bind((bind_host, port))
                    logger.info(f"Found available port: {port}")
                    return port
            except OSError as e:
                logger.debug(f"Port {port} in use: {e}")
                continue

        raise Exception("No available ports found")

    def get_container_ip(self):
        """Get the internal IP of the MySQL container"""
        if not self.container:
            return None

        try:
            self.container.reload()
            networks = self.container.attrs["NetworkSettings"]["Networks"]

            # Try to get IP from any available network
            for network_name, network_info in networks.items():
                ip = network_info.get("IPAddress")
                if ip:
                    logger.info(f"Container IP from {network_name}: {ip}")
                    return ip

        except Exception as e:
            logger.error(f"Could not get container IP: {e}")

        return None

    def test_connection_methods(self):
        """Test different connection methods to find what works"""
        connection_methods = []

        # Method 1: localhost + mapped port
        if self.port:
            connection_methods.append(
                {
                    "name": "localhost_mapped_port",
                    "host": "localhost",
                    "port": self.port,
                }
            )

            connection_methods.append(
                {
                    "name": "127.0.0.1_mapped_port",
                    "host": "127.0.0.1",
                    "port": self.port,
                }
            )

        # Method 2: Container IP + internal port (3306)
        if self.container_ip:
            connection_methods.append(
                {
                    "name": "container_ip_internal_port",
                    "host": self.container_ip,
                    "port": 3306,
                }
            )

        # Method 3: Docker host internal IP + mapped port
        try:
            # Get docker0 interface IP
            result = subprocess.run(
                ["ip", "route", "show", "default"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                # Extract gateway IP which is often the docker host
                import re

                match = re.search(r"via (\d+\.\d+\.\d+\.\d+)", result.stdout)
                if match:
                    gateway_ip = match.group(1)
                    connection_methods.append(
                        {
                            "name": "gateway_ip_mapped_port",
                            "host": gateway_ip,
                            "port": self.port,
                        }
                    )
        except:
            pass

        # Method 4: Try 0.0.0.0 (sometimes works in containers)
        if self.port:
            connection_methods.append(
                {
                    "name": "all_interfaces_mapped_port",
                    "host": "0.0.0.0",
                    "port": self.port,
                }
            )

        return connection_methods

    def try_connection_method(self, method):
        """Try a specific connection method"""
        try:
            logger.info(f"Trying {method['name']}: {method['host']}:{method['port']}")

            conn = mysql.connector.connect(
                host=method["host"],
                port=method["port"],
                user="root",
                password=self.root_password,
                connect_timeout=10,
                autocommit=True,
                charset="utf8mb4",
                use_unicode=True,
            )

            # Test the connection
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchall()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{self.db_name}`")
            cursor.execute(f"USE `{self.db_name}`")
            cursor.close()

            logger.info(f"✅ SUCCESS with {method['name']}")
            return conn

        except Exception as e:
            logger.debug(f"❌ {method['name']} failed: {e}")
            return None

    def cleanup_existing_containers(self, force=True):
        """Enhanced cleanup for server environments"""
        try:
            client = docker.from_env()

            # Find containers by name pattern
            containers = client.containers.list(
                all=True, filters={"name": "mysql-test"}
            )

            for container in containers:
                logger.info(f"Cleaning up container: {container.name}")
                try:
                    if container.status == "running":
                        container.stop(timeout=5)
                    container.remove(force=force)
                except Exception as e:
                    logger.warning(f"Error removing {container.name}: {e}")

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

    def start_instance(self):
        """Start MySQL with multiple network strategies"""
        # Find available port
        self.port = self.find_available_port()
        logger.info(f"Using port: {self.port}")

        # Cleanup existing containers
        self.cleanup_existing_containers()

        client = docker.from_env()
        logger.info("Starting MySQL container...")

        # Server-optimized MySQL configuration
        environment = {
            "MYSQL_ROOT_PASSWORD": self.root_password,
            "MYSQL_DATABASE": self.db_name,
            "MYSQL_ROOT_HOST": "%",
            "MYSQL_INITDB_SKIP_TZINFO": "1",
            # Server optimizations
            "MYSQL_INNODB_BUFFER_POOL_SIZE": "128M",
            "MYSQL_INNODB_LOG_FILE_SIZE": "32M",
            "MYSQL_INNODB_FLUSH_LOG_AT_TRX_COMMIT": "2",
            "MYSQL_SYNC_BINLOG": "0",
        }

        try:
            self.container = client.containers.run(
                "mysql:8.0",
                name=f"mysql-test-{int(time.time())}",
                environment=environment,
                ports={
                    "3306/tcp": ("0.0.0.0", self.port)  # Bind to all interfaces
                },
                detach=True,
                remove=True,
                network_mode="bridge",  # Use bridge network
                # Server memory limits
                mem_limit="512m" if self.is_server_environment else None,
                restart_policy={"Name": "no"},
            )

            # Wait for container to be running
            logger.info("Waiting for container to start...")
            time.sleep(8)  # Give more time for MySQL initialization

            self.container.reload()
            logger.info(f"Container status: {self.container.status}")

            if self.container.status != "running":
                logs = self.container.logs().decode("utf-8")
                logger.error(f"Container failed to start. Logs:\n{logs}")
                raise Exception("Container failed to start")

            # Get container IP for alternative connection methods
            self.container_ip = self.get_container_ip()

            # Wait for MySQL to be ready with multiple connection strategies
            self.wait_for_mysql_smart()

        except docker.errors.APIError as e:
            logger.error(f"Docker API error: {e}")
            if "port is already allocated" in str(e):
                logger.info("Port conflict, retrying with different port...")
                self.port = self.find_available_port(self.port + 1)
                self.start_instance()
            else:
                raise

    def wait_for_mysql_smart(self):
        """Smart MySQL connection with multiple strategies"""
        max_attempts = 15

        for attempt in range(max_attempts):
            logger.info(f"Connection attempt {attempt + 1}/{max_attempts}")

            # Check if container is still running
            try:
                self.container.reload()
                if self.container.status != "running":
                    raise Exception(
                        f"Container stopped. Status: {self.container.status}"
                    )
            except Exception as e:
                logger.error(f"Container check failed: {e}")
                break

            # Wait a bit more for MySQL to be fully ready
            if attempt < 3:
                logger.info("Waiting for MySQL initialization...")
                time.sleep(10)  # Longer wait for first few attempts
                continue

            # Try different connection methods
            connection_methods = self.test_connection_methods()

            for method in connection_methods:
                conn = self.try_connection_method(method)
                if conn:
                    self.conn = conn
                    logger.info("✅ MySQL connection established!")
                    return

            logger.info(f"All connection methods failed, waiting before retry...")
            time.sleep(5)

        # If we get here, show diagnostics
        logger.error("❌ Failed to connect with any method")
        self.show_container_diagnostics()
        raise Exception("Could not connect to MySQL after trying multiple methods")

    def show_container_diagnostics(self):
        """Show detailed diagnostics"""
        if not self.container:
            return

        try:
            logger.info("=== ENHANCED DIAGNOSTICS ===")
            self.container.reload()
            logger.info(f"Status: {self.container.status}")
            logger.info(f"Ports: {self.container.ports}")
            logger.info(f"Container IP: {self.container_ip}")

            # Show network info
            networks = self.container.attrs["NetworkSettings"]["Networks"]
            for net_name, net_info in networks.items():
                logger.info(f"Network {net_name}: {net_info.get('IPAddress', 'No IP')}")

            # Show logs
            logs = self.container.logs(tail=20).decode("utf-8")
            logger.info(f"Recent logs:\n{logs}")

            # Test all connection methods
            logger.info("Testing connection methods:")
            methods = self.test_connection_methods()
            for method in methods:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    result = sock.connect_ex((method["host"], method["port"]))
                    sock.close()
                    status = "✅ OPEN" if result == 0 else "❌ CLOSED"
                    logger.info(f"  {method['name']}: {status}")
                except Exception as e:
                    logger.info(f"  {method['name']}: ❌ ERROR ({e})")

            logger.info("=== END ENHANCED DIAGNOSTICS ===")
        except Exception as e:
            logger.error(f"Diagnostics failed: {e}")

    def test_connection(self):
        if not self.conn:
            raise Exception("No database connection!")

        logger.info("Testing database connection...")
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchall()
        cursor.close()
        return result

    def delete_instance(self):
        """Enhanced cleanup"""
        logger.info("Cleaning up MySQL instance...")

        if self.cursor:
            try:
                self.cursor.close()
            except:
                pass
            self.cursor = None

        if self.conn:
            try:
                self.conn.close()
            except:
                pass
            self.conn = None

        if self.container:
            try:
                self.container.reload()
                if self.container.status == "running":
                    logger.info("Stopping container...")
                    self.container.stop(timeout=10)
                time.sleep(2)
            except Exception as e:
                logger.warning(f"Error stopping container: {e}")
                try:
                    self.container.remove(force=True)
                except:
                    pass

            self.container = None

    def execute_sql_statements(self, statements):
        if not self.conn:
            raise Exception("No database connection!")

        cursor = self.conn.cursor()
        try:
            for stmt in statements:
                logger.info(f"Executing: {stmt[:100]}...")
                cursor.execute(stmt)
                if cursor.with_rows:
                    cursor.fetchall()
            self.conn.commit()
        finally:
            cursor.close()

    def execute_raw_query(self, query):
        logger.info(f"Executing query: {query[:100]}...")
        if not self.conn:
            raise Exception("No database connection!")

        cursor = self.conn.cursor()
        try:
            cursor.execute(query)
            try:
                result = cursor.fetchall()
                self.conn.commit()
                return result
            except mysql.connector.InterfaceError:
                self.conn.commit()
                return "Query executed successfully (no return data)"
        finally:
            cursor.close()

    def run_test(self):
        """Run complete test cycle"""
        try:
            self.start_instance()
            result = self.test_connection()
            return {
                "connection_test_result": result,
                "port": self.port,
                "container_ip": self.container_ip,
                "environment": "server" if self.is_server_environment else "local",
            }
        finally:
            self.delete_instance()


# Quick test function
def quick_network_test():
    """Quick test to diagnose network issues"""
    logger.info("=== QUICK NETWORK TEST ===")

    try:
        client = docker.from_env()

        # Start a simple test container
        container = client.containers.run(
            "mysql:8.0",
            name=f"mysql-network-test-{int(time.time())}",
            environment={"MYSQL_ROOT_PASSWORD": "test123", "MYSQL_DATABASE": "testdb"},
            ports={"3306/tcp": ("0.0.0.0", 33399)},
            detach=True,
            remove=True,
        )

        logger.info("Test container started, waiting...")
        time.sleep(15)

        # Get container IP
        container.reload()
        networks = container.attrs["NetworkSettings"]["Networks"]
        container_ip = None
        for net_name, net_info in networks.items():
            container_ip = net_info.get("IPAddress")
            if container_ip:
                break

        logger.info(f"Container IP: {container_ip}")
        logger.info(f"Host port: 33399")

        # Test connections
        test_hosts = ["localhost", "127.0.0.1", "0.0.0.0"]
        if container_ip:
            test_hosts.append(container_ip)

        for host in test_hosts:
            port = 33399 if host != container_ip else 3306
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                result = sock.connect_ex((host, port))
                sock.close()
                status = "✅ REACHABLE" if result == 0 else "❌ UNREACHABLE"
                logger.info(f"{host}:{port} - {status}")
            except Exception as e:
                logger.info(f"{host}:{port} - ❌ ERROR: {e}")

        # Cleanup
        container.stop(timeout=5)

    except Exception as e:
        logger.error(f"Network test failed: {e}")

    logger.info("=== END NETWORK TEST ===")
