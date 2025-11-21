"""
Gerenciador de input CSV do Downloader Local PDSI.
Valida e processa multiplos arquivos CSV de entrada.
"""

import csv
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Adicionar diretorio pai ao path para importar config
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.logger import get_logger
from src.utils import sanitize_string

logger = get_logger()


class CSVInputManager:
    """
    Gerencia leitura e validacao de arquivos CSV de input.

    Formato CSV esperado (7 colunas, pipe-separated):
    ID_Grupo|Grupo_Maior|ID_Subgrupo|Subgrupo|Nome_Artista|Genero_Vocalista|Links_youtube
    """

    # Colunas obrigatorias do CSV de input
    REQUIRED_COLUMNS = [
        'ID_Grupo',
        'Grupo_Maior',
        'ID_Subgrupo',
        'Subgrupo',
        'Nome_Artista',
        'Genero_Vocalista',
        'Links_youtube'
    ]

    def __init__(self, input_dir: Optional[Path] = None):
        """
        Inicializa o gerenciador de CSV.

        Args:
            input_dir: Diretorio de input (default: input/)
        """
        if input_dir is None:
            base_dir = Path(__file__).parent.parent
            input_dir = base_dir / "input"

        self.input_dir = Path(input_dir)
        self.processed_csvs: List[Path] = []

        logger.info("CSVInputManager inicializado")

    def get_csv_files(self) -> List[Path]:
        """
        Retorna lista de arquivos CSV no diretorio de input.

        Returns:
            Lista de Paths dos arquivos CSV, ordenados por nome
        """
        if not self.input_dir.exists():
            logger.warning(f"Diretorio de input nao existe: {self.input_dir}")
            return []

        csv_files = sorted(self.input_dir.glob("*.csv"))

        if csv_files:
            logger.info(f"Encontrados {len(csv_files)} arquivos CSV em {self.input_dir}")
        else:
            logger.warning(f"Nenhum arquivo CSV encontrado em {self.input_dir}")

        return csv_files

    def validate_csv(self, csv_path: Path) -> bool:
        """
        Valida se um arquivo CSV possui todas as colunas obrigatorias.

        Args:
            csv_path: Caminho do arquivo CSV

        Returns:
            True se CSV e valido
        """
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                # Detectar delimitador (pipe ou virgula)
                first_line = f.readline()
                f.seek(0)

                if '|' in first_line:
                    delimiter = '|'
                else:
                    delimiter = ','

                reader = csv.DictReader(f, delimiter=delimiter)

                if reader.fieldnames is None:
                    logger.error(f"CSV vazio ou sem cabecalho: {csv_path}")
                    return False

                # Verificar colunas obrigatorias
                missing_columns = []
                for col in self.REQUIRED_COLUMNS:
                    if col not in reader.fieldnames:
                        missing_columns.append(col)

                if missing_columns:
                    logger.error(f"Colunas faltando em {csv_path.name}: {missing_columns}")
                    return False

                # Verificar se tem pelo menos uma linha de dados
                row_count = 0
                for row in reader:
                    row_count += 1

                    # Verificar se Links_youtube nao esta vazio
                    if not row.get('Links_youtube', '').strip():
                        logger.warning(f"Linha {row_count + 1} em {csv_path.name}: Links_youtube vazio")

                if row_count == 0:
                    logger.error(f"CSV sem dados: {csv_path}")
                    return False

                logger.info(f"CSV valido: {csv_path.name} ({row_count} linhas)")
                return True

        except Exception as e:
            logger.error(f"Erro ao validar CSV {csv_path}: {str(e)}")
            return False

    def read_csv_links(self, csv_path: Path) -> List[Dict[str, str]]:
        """
        Le um arquivo CSV e retorna lista de dicionarios com dados dos links.

        Args:
            csv_path: Caminho do arquivo CSV

        Returns:
            Lista de dicionarios com campos do CSV
        """
        links_data = []

        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                # Detectar delimitador
                first_line = f.readline()
                f.seek(0)

                if '|' in first_line:
                    delimiter = '|'
                else:
                    delimiter = ','

                reader = csv.DictReader(f, delimiter=delimiter)

                for row in reader:
                    # Extrair URL
                    url = row.get('Links_youtube', '').strip()

                    if not url:
                        continue

                    # Criar dicionario com todos os campos
                    link_data = {
                        'url': url,
                        'ID_Grupo': row.get('ID_Grupo', '').strip(),
                        'Grupo_Maior': sanitize_string(row.get('Grupo_Maior', '')),
                        'ID_Subgrupo': row.get('ID_Subgrupo', '').strip(),
                        'Subgrupo': sanitize_string(row.get('Subgrupo', '')),
                        'Nome_Artista': sanitize_string(row.get('Nome_Artista', '')),
                        'Genero_Vocalista': row.get('Genero_Vocalista', '').strip(),
                        'csv_file': csv_path.name
                    }

                    links_data.append(link_data)

                logger.info(f"Lidos {len(links_data)} links de {csv_path.name}")

        except Exception as e:
            logger.error(f"Erro ao ler CSV {csv_path}: {str(e)}")

        return links_data

    def get_all_links(self) -> List[Dict[str, str]]:
        """
        Consolida todos os links de todos os CSVs validos.

        Returns:
            Lista de dicionarios com dados de todos os links
        """
        all_links = []

        csv_files = self.get_csv_files()

        if not csv_files:
            return []

        for csv_path in csv_files:
            # Validar antes de ler
            if not self.validate_csv(csv_path):
                logger.warning(f"Pulando CSV invalido: {csv_path.name}")
                continue

            # Ler links do CSV
            links = self.read_csv_links(csv_path)

            if links:
                all_links.extend(links)
                self.processed_csvs.append(csv_path)

        logger.info(f"Total de links consolidados: {len(all_links)}")
        return all_links

    def delete_processed_csvs(self) -> bool:
        """
        Deleta os arquivos CSV que foram processados com sucesso.

        Returns:
            True se deletou com sucesso
        """
        if not self.processed_csvs:
            logger.info("Nenhum CSV para deletar")
            return True

        deleted_count = 0

        for csv_path in self.processed_csvs:
            try:
                if csv_path.exists():
                    csv_path.unlink()
                    deleted_count += 1
                    logger.info(f"CSV deletado: {csv_path.name}")
            except Exception as e:
                logger.error(f"Erro ao deletar CSV {csv_path}: {str(e)}")

        logger.info(f"CSVs deletados: {deleted_count}/{len(self.processed_csvs)}")

        # Limpar lista
        self.processed_csvs = []

        return deleted_count > 0

    def get_csv_stats(self) -> Dict[str, Any]:
        """
        Retorna estatisticas dos CSVs de input.

        Returns:
            Dicionario com estatisticas
        """
        csv_files = self.get_csv_files()

        stats = {
            'total_files': len(csv_files),
            'valid_files': 0,
            'invalid_files': 0,
            'total_links': 0,
            'files': []
        }

        for csv_path in csv_files:
            file_stats = {
                'name': csv_path.name,
                'valid': False,
                'links': 0
            }

            if self.validate_csv(csv_path):
                links = self.read_csv_links(csv_path)
                file_stats['valid'] = True
                file_stats['links'] = len(links)
                stats['valid_files'] += 1
                stats['total_links'] += len(links)
            else:
                stats['invalid_files'] += 1

            stats['files'].append(file_stats)

        return stats
