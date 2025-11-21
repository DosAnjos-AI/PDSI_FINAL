"""
Gerenciador de IDs processados para sistema de skip.
Mantem registro persistente em JSON.
"""

import json
import sys
from pathlib import Path
from typing import Set, Optional

# Adicionar diretorio pai ao path para importar config
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.logger import get_logger
from src.utils import ensure_dir


logger = get_logger()


class SkipManager:
    """
    Gerencia registro de videos ja processados.

    Mantem arquivo processed_ids.json na raiz de output/
    para evitar reprocessamento de videos.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Inicializa o gerenciador.

        Args:
            output_dir: Diretorio de saida (default: output/)
        """
        if output_dir is None:
            base_dir = Path(__file__).parent.parent
            output_dir = base_dir / "output"

        self.output_dir = Path(output_dir)
        ensure_dir(self.output_dir)

        self.log_file = self.output_dir / "processed_ids.json"
        self.processed_ids: Set[str] = self.load_processed_ids()

        logger.info(f"SkipManager inicializado - {len(self.processed_ids)} IDs carregados")

    def load_processed_ids(self) -> Set[str]:
        """
        Carrega IDs processados do arquivo JSON.

        Returns:
            Set com IDs processados
        """
        if not self.log_file.exists():
            logger.info("Arquivo processed_ids.json nao existe - criando novo")
            self.save_processed_ids(set())
            return set()

        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

                # Suportar tanto lista quanto dict com timestamp
                if isinstance(data, list):
                    ids = set(data)
                elif isinstance(data, dict):
                    ids = set(data.keys())
                else:
                    logger.warning("Formato invalido em processed_ids.json - criando novo")
                    ids = set()

                logger.info(f"Carregados {len(ids)} IDs processados")
                return ids

        except json.JSONDecodeError as e:
            logger.error(f"Erro ao carregar processed_ids.json: {str(e)}")
            logger.warning("Criando novo arquivo de IDs")
            return set()

    def save_processed_ids(self, ids: Optional[Set[str]] = None) -> bool:
        """
        Salva IDs processados no arquivo JSON.

        Args:
            ids: Set de IDs (default: usa self.processed_ids)

        Returns:
            True se salvou com sucesso
        """
        if ids is None:
            ids = self.processed_ids

        try:
            # Salvar como lista ordenada para facilitar leitura
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(sorted(list(ids)), f, indent=2, ensure_ascii=False)

            logger.debug(f"IDs processados salvos: {len(ids)} registros")
            return True

        except Exception as e:
            logger.error(f"Erro ao salvar processed_ids.json: {str(e)}")
            return False

    def is_processed(self, video_id: str) -> bool:
        """
        Verifica se video ja foi processado.

        Args:
            video_id: ID do video

        Returns:
            True se ja foi processado
        """
        return video_id in self.processed_ids

    def add_processed(self, video_id: str) -> bool:
        """
        Adiciona ID a lista de processados.

        Args:
            video_id: ID do video processado

        Returns:
            True se adicionou com sucesso
        """
        if video_id in self.processed_ids:
            logger.warning(f"ID ja estava na lista de processados: {video_id}")
            return True

        self.processed_ids.add(video_id)

        # Salvar imediatamente para persistir estado
        if self.save_processed_ids():
            logger.info(f"ID adicionado aos processados: {video_id}")
            return True
        else:
            # Reverter se falhou ao salvar
            self.processed_ids.remove(video_id)
            return False

    def add_batch(self, video_ids: list) -> int:
        """
        Adiciona multiplos IDs de uma vez.

        Args:
            video_ids: Lista de IDs

        Returns:
            Numero de IDs adicionados
        """
        before_count = len(self.processed_ids)

        self.processed_ids.update(video_ids)

        if self.save_processed_ids():
            added_count = len(self.processed_ids) - before_count
            logger.info(f"{added_count} novos IDs adicionados aos processados")
            return added_count
        else:
            return 0

    def remove_id(self, video_id: str) -> bool:
        """
        Remove ID da lista de processados.

        Util para reprocessar video especifico.

        Args:
            video_id: ID do video

        Returns:
            True se removeu com sucesso
        """
        if video_id not in self.processed_ids:
            logger.warning(f"ID nao esta na lista de processados: {video_id}")
            return False

        self.processed_ids.remove(video_id)

        if self.save_processed_ids():
            logger.info(f"ID removido dos processados: {video_id}")
            return True
        else:
            # Reverter se falhou ao salvar
            self.processed_ids.add(video_id)
            return False

    def get_stats(self) -> dict:
        """
        Retorna estatisticas dos IDs processados.

        Returns:
            Dicionario com estatisticas
        """
        return {
            'total_processed': len(self.processed_ids),
            'log_file': str(self.log_file),
            'log_exists': self.log_file.exists()
        }
