"""
Mapeador de fontes do Downloader Local PDSI.
Gerencia mapeamento entre source_IDs e pastas de output.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Optional

# Adicionar diretorio pai ao path para importar config
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.logger import get_logger
from src.utils import ensure_dir

logger = get_logger()


class SourceMapper:
    """
    Gerencia mapeamento entre fontes (source_ID) e pastas de output.

    Mantém registro de qual source_ID foi mapeado para qual pasta,
    permitindo consistência quando múltiplos CSVs são processados.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Inicializa o mapeador de fontes.

        Args:
            output_dir: Diretorio de output (default: output/)
        """
        if output_dir is None:
            base_dir = Path(__file__).parent.parent
            output_dir = base_dir / "output"

        self.output_dir = Path(output_dir)
        ensure_dir(self.output_dir)

        # Arquivo de mapeamento
        self.mapping_file = self.output_dir / "source_mapping.json"

        # Carregar mapeamento existente
        self.mapping: Dict[str, str] = self._load_mapping()

        logger.info("SourceMapper inicializado")

    def _load_mapping(self) -> Dict[str, str]:
        """
        Carrega mapeamento do arquivo JSON.

        Returns:
            Dicionario com mapeamentos source_id -> folder_name
        """
        if not self.mapping_file.exists():
            return {}

        try:
            with open(self.mapping_file, 'r', encoding='utf-8') as f:
                mapping = json.load(f)
                logger.debug(f"Mapeamento carregado: {len(mapping)} fontes")
                return mapping
        except Exception as e:
            logger.error(f"Erro ao carregar mapeamento: {str(e)}")
            return {}

    def _save_mapping(self) -> bool:
        """
        Salva mapeamento no arquivo JSON.

        Returns:
            True se salvou com sucesso
        """
        try:
            with open(self.mapping_file, 'w', encoding='utf-8') as f:
                json.dump(self.mapping, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar mapeamento: {str(e)}")
            return False

    def get_folder_name(
        self,
        source_id: str,
        custom_name: Optional[str] = None
    ) -> str:
        """
        Retorna nome da pasta para um source_id.

        Se ja existe mapeamento, usa o existente.
        Se nao existe, cria novo mapeamento.

        Args:
            source_id: ID da fonte (playlist, channel, video)
            custom_name: Nome customizado (opcional)

        Returns:
            Nome da pasta de output
        """
        # Verificar se ja tem mapeamento
        if source_id in self.mapping:
            return self.mapping[source_id]

        # Criar novo mapeamento
        if custom_name and custom_name != "default":
            folder_name = custom_name
        else:
            folder_name = source_id

        # Salvar mapeamento
        self.mapping[source_id] = folder_name
        self._save_mapping()

        logger.debug(f"Mapeamento criado: {source_id} -> {folder_name}")
        return folder_name

    def set_folder_name(self, source_id: str, folder_name: str) -> bool:
        """
        Define nome da pasta para um source_id.

        Args:
            source_id: ID da fonte
            folder_name: Nome da pasta

        Returns:
            True se definiu com sucesso
        """
        self.mapping[source_id] = folder_name
        return self._save_mapping()

    def get_output_path(
        self,
        source_id: str,
        custom_name: Optional[str] = None
    ) -> Path:
        """
        Retorna caminho completo da pasta de output para um source_id.

        Args:
            source_id: ID da fonte
            custom_name: Nome customizado (opcional)

        Returns:
            Path completo da pasta de output
        """
        folder_name = self.get_folder_name(source_id, custom_name)
        output_path = self.output_dir / folder_name
        ensure_dir(output_path)
        return output_path

    def has_mapping(self, source_id: str) -> bool:
        """
        Verifica se ja existe mapeamento para um source_id.

        Args:
            source_id: ID da fonte

        Returns:
            True se existe mapeamento
        """
        return source_id in self.mapping

    def get_all_mappings(self) -> Dict[str, str]:
        """
        Retorna todos os mapeamentos.

        Returns:
            Dicionario com todos os mapeamentos
        """
        return self.mapping.copy()

    def remove_mapping(self, source_id: str) -> bool:
        """
        Remove mapeamento de um source_id.

        Args:
            source_id: ID da fonte

        Returns:
            True se removeu com sucesso
        """
        if source_id in self.mapping:
            del self.mapping[source_id]
            self._save_mapping()
            logger.debug(f"Mapeamento removido: {source_id}")
            return True
        return False

    def clear_all_mappings(self) -> bool:
        """
        Limpa todos os mapeamentos.

        Returns:
            True se limpou com sucesso
        """
        self.mapping = {}
        return self._save_mapping()

    def get_stats(self) -> Dict[str, int]:
        """
        Retorna estatisticas dos mapeamentos.

        Returns:
            Dicionario com estatisticas
        """
        return {
            'total_mappings': len(self.mapping),
            'unique_folders': len(set(self.mapping.values()))
        }
