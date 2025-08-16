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

    def check_docker_access(self):
        """Check Docker daemon access"""
        try:
            client = docker.from_env()
            client.ping()
            logger.info("✅ Docker daemon accessible")
            return True
        except docker.errors.DockerException as e:
            logger.error(f"❌ Docker access failed: {e}")

            # Try to diagnose the issue
            try:
                result = subprocess.run(
                    ["docker", "ps"], capture_output=True, text=True
                )
                if result.returncode != 0:
                    logger.error(f"Docker CLI error: {result.stderr}")
                    logger.info(
                        "💡 Try: sudo usermod -aG docker $USER && newgrp docker"
                    )
            except Exception:
                logger.error("Docker CLI not available")

            return False

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

    def get_network_config(self):
        """Get network configuration based on environment"""
        if self.is_server_environment:
            return {
                "network_mode": "bridge",  # Explicit bridge mode
                "publish_all_ports": False,
                "host_ip": "0.0.0.0",  # Bind to all interfaces
            }
        else:
            return {
                "network_mode": "bridge",
                "publish_all_ports": False,
                "host_ip": "127.0.0.1",  # Local only
            }

    def start_instance(self):
        """Start MySQL with server-optimized settings"""
        # Pre-flight checks
        if not self.check_docker_access():
            raise Exception("Docker daemon not accessible")

        # Find available port
        self.port = self.find_available_port()
        logger.info(f"Using port: {self.port}")

        # Cleanup existing containers
        self.cleanup_existing_containers()

        client = docker.from_env()
        network_config = self.get_network_config()

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

        # Configure volumes only if needed
        volumes = {}
        if os.path.exists("my.cnf"):
            volumes[f"{os.path.abspath('my.cnf')}"] = {
                "bind": "/etc/mysql/conf.d/my.cnf",
                "mode": "ro",
            }

        try:
            self.container = client.containers.run(
                "mysql:8.0",  # Specific version for consistency
                name=f"mysql-test-{int(time.time())}",  # Unique name
                environment=environment,
                ports={"3306/tcp": (network_config["host_ip"], self.port)},
                volumes=volumes,
                detach=True,
                remove=True,
                network_mode=network_config["network_mode"],
                # Server memory limits
                mem_limit="512m" if self.is_server_environment else None,
                # Restart policy
                restart_policy={"Name": "no"},
                # Security options for servers
                security_opt=["no-new-privileges"]
                if self.is_server_environment
                else None,
            )

            # Wait for container to be running
            logger.info("Waiting for container to start...")
            time.sleep(5)

            self.container.reload()
            logger.info(f"Container status: {self.container.status}")

            if self.container.status != "running":
                logs = self.container.logs().decode("utf-8")
                logger.error(f"Container failed to start. Logs:\n{logs}")
                raise Exception("Container failed to start")

            # Wait for MySQL to be ready
            self.wait_for_mysql()

        except docker.errors.APIError as e:
            logger.error(f"Docker API error: {e}")
            if "port is already allocated" in str(e):
                logger.info("Port conflict, retrying with different port...")
                self.port = self.find_available_port(self.port + 1)
                self.start_instance()  # Retry
            else:
                raise

    def wait_for_mysql(self):
        """Enhanced MySQL readiness check for servers"""
        retries = 45  # More retries for server environments
        connection_host = "localhost" if not self.is_server_environment else "127.0.0.1"

        logger.info(f"Waiting for MySQL on {connection_host}:{self.port}")

        for attempt in range(retries):
            try:
                logger.info(f"Connection attempt {attempt + 1}/{retries}")

                # Progressive connection strategy
                if attempt < 10:
                    # First attempts: basic connection without database
                    test_conn = mysql.connector.connect(
                        host=connection_host,
                        port=self.port,
                        user="root",
                        password=self.root_password,
                        connect_timeout=15,
                        autocommit=True,
                        charset="utf8mb4",
                        use_unicode=True,
                    )

                    cursor = test_conn.cursor()
                    cursor.execute("SELECT 1")
                    cursor.fetchall()
                    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{self.db_name}`")
                    cursor.execute(f"USE `{self.db_name}`")
                    cursor.close()

                    self.conn = test_conn
                else:
                    # Later attempts: direct database connection
                    self.conn = mysql.connector.connect(
                        host=connection_host,
                        port=self.port,
                        user="root",
                        password=self.root_password,
                        database=self.db_name,
                        connect_timeout=15,
                        autocommit=True,
                        charset="utf8mb4",
                        use_unicode=True,
                    )

                logger.info("✅ MySQL connection successful!")
                return

            except mysql.connector.Error as err:
                logger.debug(f"MySQL error: {err}")

                # Show container logs periodically
                if attempt in [10, 20, 30]:
                    self.show_container_diagnostics()

                if attempt < retries - 1:
                    time.sleep(3)

            except Exception as e:
                logger.debug(f"General error: {e}")
                if attempt < retries - 1:
                    time.sleep(3)

        # Final diagnostics
        logger.error("❌ Failed to connect to MySQL")
        self.show_container_diagnostics()
        raise Exception("Could not connect to MySQL after multiple attempts")

    def show_container_diagnostics(self):
        """Show detailed diagnostics for troubleshooting"""
        if not self.container:
            return

        try:
            logger.info("=== CONTAINER DIAGNOSTICS ===")
            self.container.reload()
            logger.info(f"Status: {self.container.status}")
            logger.info(f"Ports: {self.container.ports}")

            # Show logs
            logs = self.container.logs(tail=30).decode("utf-8")
            logger.info(f"Recent logs:\n{logs}")

            # Test port connectivity
            try:
                result = subprocess.run(
                    ["nc", "-zv", "127.0.0.1", str(self.port)],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                logger.info(f"Port test: {result.stderr}")
            except:
                logger.info("Could not test port connectivity")

            logger.info("=== END DIAGNOSTICS ===")
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

        # Close connections
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

        # Stop container
        if self.container:
            try:
                self.container.reload()
                if self.container.status == "running":
                    logger.info("Stopping container...")
                    self.container.stop(timeout=10)
                time.sleep(2)  # Grace period
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
                "environment": "server" if self.is_server_environment else "local",
            }
        finally:
            self.delete_instance()


# Utility functions for server deployment
def check_server_requirements():
    """Check server requirements"""
    logger.info("Checking server requirements...")

    # Check Docker
    try:
        client = docker.from_env()
        client.ping()
        logger.info("✅ Docker OK")
    except Exception as e:
        logger.error(f"❌ Docker issue: {e}")
        return False

    # Check available ports
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("0.0.0.0", 33306))
        logger.info("✅ Ports available")
    except Exception as e:
        logger.error(f"❌ Port issue: {e}")
        return False

    return True


def cleanup_all_containers():
    """Clean up all MySQL test containers"""
    try:
        client = docker.from_env()
        containers = client.containers.list(all=True, filters={"name": "mysql-test"})
        for container in containers:
            logger.info(f"Removing: {container.name}")
            if container.status == "running":
                container.stop(timeout=5)
            container.remove(force=True)
        logger.info("Cleanup completed")
    except Exception as e:
        logger.error(f"Cleanup error: {e}")


if __name__ == "__main__":
    # Check requirements first
    if not check_server_requirements():
        logger.error("Server requirements not met!")
        exit(1)

    # Clean up first
    cleanup_all_containers()

    # Test
    mysql_instance = MySQLTestInstance()
    try:
        result = mysql_instance.run_test()
        logger.info(f"✅ Test successful: {result}")
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise
