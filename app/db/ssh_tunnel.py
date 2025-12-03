import logging
import os
from typing import Dict, Tuple, Optional
from sshtunnel import SSHTunnelForwarder

logger = logging.getLogger(__name__)


class SSHTunnelManager:
    """
    SSH 터널을 관리하는 싱글톤 클래스.
    여러 개의 터널을 이름(key)으로 구분하여 관리합니다.
    """

    _instance = None
    _tunnels: Dict[str, SSHTunnelForwarder] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SSHTunnelManager, cls).__new__(cls)
        return cls._instance

    def create_tunnel(
        self,
        name: str,
        ssh_host: str,
        ssh_port: int,
        ssh_user: str,
        ssh_pkey: str,
        remote_bind_address: Tuple[str, int],
        local_bind_port: int,
    ) -> SSHTunnelForwarder:
        """
        SSH 터널을 생성하고 시작합니다.
        
        Args:
            name: 터널 식별자 (예: 'mongo', 'postgres')
            ssh_host: SSH 접속 호스트
            ssh_port: SSH 접속 포트
            ssh_user: SSH 접속 사용자
            ssh_pkey: PEM 키 파일 경로
            remote_bind_address: 터널링할 원격 주소 (호스트, 포트)
            local_bind_port: 로컬 바인딩 포트
            
        Returns:
            SSHTunnelForwarder: 생성된 터널 객체
        """
        if name in self._tunnels:
            logger.info(f"SSH tunnel '{name}' already exists. Reusing it.")
            return self._tunnels[name]

        if not os.path.exists(ssh_pkey):
            raise FileNotFoundError(f"SSH key file not found: {ssh_pkey}")

        try:
            tunnel = SSHTunnelForwarder(
                (ssh_host, ssh_port),
                ssh_username=ssh_user,
                ssh_pkey=ssh_pkey,
                remote_bind_address=remote_bind_address,
                local_bind_address=("127.0.0.1", local_bind_port),
                set_keepalive=30.0,
            )
            tunnel.start()
            self._tunnels[name] = tunnel
            logger.info(
                f"SSH tunnel '{name}' started: "
                f"localhost:{local_bind_port} -> {remote_bind_address[0]}:{remote_bind_address[1]} "
                f"via {ssh_user}@{ssh_host}:{ssh_port}"
            )
            return tunnel
        except Exception as e:
            logger.error(f"Failed to create SSH tunnel '{name}': {e}")
            raise

    def get_tunnel(self, name: str) -> Optional[SSHTunnelForwarder]:
        """이름으로 터널 객체를 반환합니다."""
        return self._tunnels.get(name)

    def close_tunnel(self, name: str) -> None:
        """특정 터널을 종료합니다."""
        tunnel = self._tunnels.pop(name, None)
        if tunnel:
            try:
                tunnel.stop()
                logger.info(f"SSH tunnel '{name}' closed.")
            except Exception as e:
                logger.error(f"Error closing SSH tunnel '{name}': {e}")

    def close_all_tunnels(self) -> None:
        """모든 터널을 종료합니다."""
        for name in list(self._tunnels.keys()):
            self.close_tunnel(name)


# 전역 인스턴스
ssh_tunnel_manager = SSHTunnelManager()
