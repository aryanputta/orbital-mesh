from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    node_count: int = 10
    simulation_tick_ms: int = 500
    failure_injection_enabled: bool = True

    redis_url: str = "redis://localhost:6379"
    postgres_dsn: str = "postgresql://orbital:orbital@localhost:5432/orbital"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    quic_cert_path: str = "./certs/cert.pem"
    quic_key_path: str = "./certs/key.pem"

    anomaly_threshold: float = 0.7
    protocol_switch_interval_s: float = 5.0
    heartbeat_interval_s: float = 5.0
    heartbeat_timeout_s: float = 3.0
    node_offline_timeout_s: float = 30.0

    log_level: str = "INFO"
    log_format: str = "json"

    base_tcp_port: int = 9000
    base_udp_port: int = 9100
    base_quic_port: int = 9200
    control_port_offset: int = 500


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
