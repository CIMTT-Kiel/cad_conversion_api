"""
Configuration loader for CAD API Client

Loads configuration from multiple sources with priority:
1. Explicit parameters
2. Environment variables
3. Config file (config.yaml or config.local.yaml)
4. Defaults
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
import logging


logger = logging.getLogger(__name__)


class ClientConfig:
    """Configuration for CAD API Client."""

    def __init__(
        self,
        host: Optional[str] = None,
        converter_url: Optional[str] = None,
        embedding_url: Optional[str] = None,
        analyser_url: Optional[str] = None,
        rendering_url: Optional[str] = None,
        timeout: Optional[int] = None,
        config_file: Optional[str] = None
    ):
        """
        Load configuration from multiple sources.

        Priority (highest to lowest):
        1. Explicit parameters
        2. Environment variables
        3. Config file
        4. Defaults

        Args:
            host: Server IP or hostname
            converter_url: Full converter service URL
            embedding_url: Full embedding service URL
            analyser_url: Full analyser service URL
            rendering_url: Full rendering service URL
            timeout: Request timeout in seconds
            config_file: Path to config file (yaml)
        """
        # Try to load config file
        config_data = self._load_config_file(config_file)

        # Load environment variables
        self._load_env_variables()

        # Build configuration with priority
        self.host = host or self._env_host or config_data.get("host", "localhost")
        self.timeout = timeout or self._env_timeout or config_data.get("timeout", 300)

        # Get ports from config
        ports = config_data.get("ports", {})
        converter_port = ports.get("converter", 8001)
        embedding_port = ports.get("embedding", 8002)
        analyser_port = ports.get("analyser", 8003)
        rendering_port = ports.get("rendering", 8004)

        # Get URLs from config
        urls = config_data.get("urls", {})

        # Build final URLs with priority
        if converter_url:
            self.converter_url = converter_url
        elif self._env_converter_url:
            self.converter_url = self._env_converter_url
        elif urls.get("converter"):
            self.converter_url = urls["converter"]
        else:
            self.converter_url = self._build_url(self.host, converter_port)

        if embedding_url:
            self.embedding_url = embedding_url
        elif self._env_embedding_url:
            self.embedding_url = self._env_embedding_url
        elif urls.get("embedding"):
            self.embedding_url = urls["embedding"]
        else:
            self.embedding_url = self._build_url(self.host, embedding_port)

        if analyser_url:
            self.analyser_url = analyser_url
        elif self._env_analyser_url:
            self.analyser_url = self._env_analyser_url
        elif urls.get("analyser"):
            self.analyser_url = urls["analyser"]
        else:
            self.analyser_url = self._build_url(self.host, analyser_port)

        if rendering_url:
            self.rendering_url = rendering_url
        elif self._env_rendering_url:
            self.rendering_url = self._env_rendering_url
        elif urls.get("rendering"):
            self.rendering_url = urls["rendering"]
        else:
            self.rendering_url = self._build_url(self.host, rendering_port)

        # Clean up URLs
        self.converter_url = self.converter_url.rstrip("/") if self.converter_url else None
        self.embedding_url = self.embedding_url.rstrip("/") if self.embedding_url else None
        self.analyser_url = self.analyser_url.rstrip("/") if self.analyser_url else None
        self.rendering_url = self.rendering_url.rstrip("/") if self.rendering_url else None

        logger.info("Configuration loaded:")
        logger.info(f"  Host: {self.host}")
        logger.info(f"  Converter: {self.converter_url}")
        logger.info(f"  Embedding: {self.embedding_url}")
        logger.info(f"  Analyser: {self.analyser_url}")
        logger.info(f"  Rendering: {self.rendering_url}")
        logger.info(f"  Timeout: {self.timeout}s")

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
        """
        Load configuration from YAML file.

        Args:
            config_file: Path to config file

        Returns:
            Configuration dictionary
        """
        # Determine config file path
        if config_file:
            config_path = Path(config_file)
        else:
            # Try multiple default locations
            client_dir = Path(__file__).parent
            possible_paths = [
                client_dir / "config.local.yaml",  # Local override
                client_dir / "config.yaml",        # Default
                Path.cwd() / "config.yaml",        # Current directory
            ]

            config_path = None
            for path in possible_paths:
                if path.exists():
                    config_path = path
                    break

        if not config_path or not config_path.exists():
            logger.debug("No config file found, using defaults")
            return {}

        # Try to load YAML
        try:
            import yaml
            with open(config_path, "r") as f:
                config_data = yaml.safe_load(f) or {}
            logger.info(f"Config loaded from: {config_path}")
            return config_data
        except ImportError:
            logger.warning("PyYAML not installed, cannot load config file. Install with: pip install pyyaml")
            return {}
        except Exception as e:
            logger.warning(f"Failed to load config file {config_path}: {e}")
            return {}

    def _build_url(self, host: str, port: int) -> str:
        """
        Build URL from host and port.

        Args:
            host: Hostname or IP
            port: Port number

        Returns:
            Full URL
        """
        # Add protocol if missing
        if not host.startswith(("http://", "https://")):
            host = f"http://{host}"

        return f"{host}:{port}"

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Configuration as dict
        """
        return {
            "host": self.host,
            "converter_url": self.converter_url,
            "embedding_url": self.embedding_url,
            "analyser_url": self.analyser_url,
            "rendering_url": self.rendering_url,
            "timeout": self.timeout
        }
