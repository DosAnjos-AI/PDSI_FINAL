"""
Gerenciador de nomes de pastas de output.
Sanitiza e resolve conflitos de nomes duplicados.
"""

import re
import sys
from pathlib import Path
from typing import Optional

# Adicionar diretorio pai ao path para importar config
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.logger import get_logger
from src.utils import ensure_dir


logger = get_logger()


class FolderNameManager:
    """
    Gerencia nomes de pastas de output com sanitizacao e resolucao de duplicatas.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Inicializa o gerenciador.

        Args:
            output_dir: Diretorio de output (default: output/)
        """
        if output_dir is None:
            base_dir = Path(__file__).parent.parent
            output_dir = base_dir / "output"

        self.output_dir = Path(output_dir)
        ensure_dir(self.output_dir)

        logger.info("FolderNameManager inicializado")

    def sanitize_folder_name(self, name: str) -> str:
        """
        Sanitiza nome para uso como pasta.

        Args:
            name: Nome a ser sanitizado

        Returns:
            Nome sanitizado
        """
        if not name:
            return "unnamed"

        # Substituir espacos por underscore
        name = name.replace(' ', '_')

        # Remover caracteres invalidos para pastas (Windows + Linux)
        invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
        name = re.sub(invalid_chars, '_', name)

        # Remover underscores duplicados
        name = re.sub(r'_+', '_', name)

        # Remover underscore no inicio/fim
        name = name.strip('_')

        # Limitar comprimento
        if len(name) > 100:
            name = name[:100]

        return name

    def resolve_folder_name(
        self,
        base_name: str,
        source_id: str
    ) -> str:
        """
        Resolve nome de pasta com numeracao se ja existir.

        Args:
            base_name: Nome base da pasta
            source_id: ID da fonte (fallback se base_name vazio)

        Returns:
            Nome final da pasta (pode ter _2, _3, etc se duplicado)
        """
        # Sanitizar nome base
        sanitized = self.sanitize_folder_name(base_name)

        # Se vazio apos sanitizacao, usar source_id
        if not sanitized or sanitized == "unnamed":
            sanitized = source_id

        # Verificar se ja existe
        folder_path = self.output_dir / sanitized

        if not folder_path.exists():
            return sanitized

        # Existe, tentar com numeracao
        counter = 2
        while True:
            numbered_name = f"{sanitized}_{counter}"
            folder_path = self.output_dir / numbered_name

            if not folder_path.exists():
                logger.info(f"Nome duplicado detectado, usando: {numbered_name}")
                return numbered_name

            counter += 1

            # Seguranca: limite de 1000 duplicatas
            if counter > 1000:
                logger.error("Limite de duplicatas excedido")
                return f"{sanitized}_{counter}"

    def get_folder_name(
        self,
        link_data: dict,
        source_id: str,
        use_config_name: str
    ) -> str:
        """
        Determina nome final da pasta baseado no modo e configuracoes.

        Args:
            link_data: Dados do link (com Nome_Artista, etc)
            source_id: ID da fonte (playlist_ID, channel_ID, video_ID)
            use_config_name: Valor de NOME_PASTA_OUTPUT do config

        Returns:
            Nome final da pasta
        """
        # Modo 1: Config com nome customizado (ignora CSV)
        if use_config_name != "default":
            logger.info(f"Usando nome do config: {use_config_name}")
            return self.resolve_folder_name(use_config_name, source_id)

        # Modo 2: Default com CSV (usa Nome_Artista)
        nome_artista = link_data.get('Nome_Artista', '').strip()

        if nome_artista:
            logger.info(f"Usando Nome_Artista do CSV: {nome_artista}")
            return self.resolve_folder_name(nome_artista, source_id)

        # Modo 3: Fallback (sem CSV ou Nome_Artista vazio)
        logger.info(f"Usando source_id como fallback: {source_id}")
        return source_id
