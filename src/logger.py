"""
Sistema de logging centralizado do Downloader Local PDSI.
"""

import logging
from pathlib import Path
from typing import Optional
from datetime import datetime


class CustomLogger:
    """
    Logger customizado para o projeto.

    Gerencia logs em arquivo e console com formatacao adequada.
    """

    def __init__(self, name: str, log_dir: Optional[Path] = None):
        """
        Inicializa o logger.

        Args:
            name: Nome do logger
            log_dir: Diretorio para salvar logs (default: logs/)
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # Evitar duplicacao de handlers
        if self.logger.handlers:
            return

        # Definir diretorio de logs
        if log_dir is None:
            base_dir = Path(__file__).parent.parent
            log_dir = base_dir / "logs"

        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        # Formato dos logs
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Handler para arquivo processing.log
        processing_handler = logging.FileHandler(
            log_dir / "processing.log",
            encoding='utf-8'
        )
        processing_handler.setLevel(logging.INFO)
        processing_handler.setFormatter(formatter)

        # Handler para arquivo errors.log (apenas erros)
        error_handler = logging.FileHandler(
            log_dir / "errors.log",
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)

        # Handler para console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        # Adicionar handlers
        self.logger.addHandler(processing_handler)
        self.logger.addHandler(error_handler)
        self.logger.addHandler(console_handler)

    def info(self, message: str) -> None:
        """Log de informacao"""
        self.logger.info(message)

    def warning(self, message: str) -> None:
        """Log de aviso"""
        self.logger.warning(message)

    def error(self, message: str) -> None:
        """Log de erro"""
        self.logger.error(message)

    def debug(self, message: str) -> None:
        """Log de debug"""
        self.logger.debug(message)


def get_logger(name: str = "downloader_pdsi") -> CustomLogger:
    """
    Retorna instancia do logger.

    Args:
        name: Nome do logger

    Returns:
        Instancia de CustomLogger
    """
    return CustomLogger(name)
