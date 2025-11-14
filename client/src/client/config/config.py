"""Configuration loader"""

import logging, os
from pathlib import Path
from typing import Optional, Dict, Any
from client.constants import PATHS

logger = logging.getLogger(__name__)


class ClientConfig:
    """Configuration for CAD API Client."""

    def __init__(self, host: Optional[str] = None, converter_url: Optional[str] = None,
                 embedding_url: Optional[str] = None, analyser_url: Optional[str] = None,
                 rendering_url: Optional[str] = None, timeout: Optional[int] = None,
                 config_file: Optional[str] = None):
        """Load configuration from config file"""
        config_data = self._load_config_file(config_file)
        self._load_env_variables()

        self.host = host or self._env_host or config_data.get("host", "localhost")
        self.timeout = timeout or self._env_timeout or config_data.get("timeout", 300)

        ports = config_data.get("ports", {})
        urls = config_data.get("urls", {})

        # Build URLs with priority: param > env > config > default
        services = [
            ("converter", converter_url, self._env_converter_url, urls.get("converter"), ports.get("converter", 8001)),
            ("embedding", embedding_url, self._env_embedding_url, urls.get("embedding"), ports.get("embedding", 8003)),
            ("analyser", analyser_url, self._env_analyser_url, urls.get("analyser"), ports.get("analyser", 8002)),
            ("rendering", rendering_url, self._env_rendering_url, urls.get("rendering"), ports.get("rendering", 8004))
        ]

        for name, param_url, env_url, config_url, port in services:
            url = param_url or env_url or config_url or self._build_url(self.host, port)
            setattr(self, f"{name}_url", url.rstrip("/") if url else None)

        logger.info(f"Config: host={self.host}, timeout={self.timeout}s")
        logger.info(f"  Converter={self.converter_url}, Embedding={self.embedding_url}")
        logger.info(f"  Analyser={self.analyser_url}, Rendering={self.rendering_url}")

    def _load_env_variables(self):
        """Load configuration from environment variables."""
        self._env_host = os.getenv("CAD_API_HOST")
        self._env_converter_url = os.getenv("CAD_CONVERTER_URL")
        self._env_embedding_url = os.getenv("CAD_EMBEDDING_URL")
        self._env_analyser_url = os.getenv("CAD_ANALYSER_URL")
        self._env_rendering_url = os.getenv("CAD_RENDERING_URL")

        timeout_str = os.getenv("CAD_API_TIMEOUT")
        self._env_timeout = int(timeout_str) if timeout_str else None

    def _load_config_file(self, config_file: Optional[str] = None) -> Dict[str, Any]:
        """Load YAML config file from specified path or default locations."""
        if config_file:
            config_path = Path(config_file)
        else:
            config_path = PATHS.CONFIG / "client.yaml"
            logger.debug("No config file found!")
            assert config_path.exists(), f"Config file not found in: {config_path}"


        try:
            import yaml
            with open(config_path, "r") as f:
                config_data = yaml.safe_load(f) or {}
            logger.info(f"Config loaded: {config_path}")
            return config_data
        except Exception as e:
            logger.warning(f"Failed to load config {config_path}: {e}")
            return {}

    def _build_url(self, host: str, port: int) -> str:
        """Build URL from host and port."""
        if not host.startswith(("http://", "https://")):
            host = f"http://{host}"  # TODO use https by default in future
        return f"{host}:{port}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "host": self.host,
            "converter_url": self.converter_url,
            "embedding_url": self.embedding_url,
            "analyser_url": self.analyser_url,
            "rendering_url": self.rendering_url,
            "timeout": self.timeout
        }
