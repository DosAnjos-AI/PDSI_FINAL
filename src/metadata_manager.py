"""
Gerenciador de metadados do Downloader Local PDSI.
Consolida metadados em CSV pipe-separated.
"""

import csv
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Adicionar diretorio pai ao path para importar config
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.logger import get_logger
from src.utils import sanitize_string, ensure_dir


logger = get_logger()


class MetadataManager:
    """
    Gerencia extracao e consolidacao de metadados.

    Formato CSV: 12 campos pipe-separated
    id|ID_Grupo|Grupo_Maior|ID_Subgrupo|Subgrupo|Nome_Artista|title|Genero_Vocalista|duration|view_count|like_count|comment_count
    """

    # Campos obrigatorios do CSV (ATUALIZADOS - 12 campos)
    CSV_FIELDS = [
        'id',
        'ID_Grupo',
        'Grupo_Maior',
        'ID_Subgrupo',
        'Subgrupo',
        'Nome_Artista',
        'title',
        'Genero_Vocalista',
        'duration',
        'view_count',
        'like_count',
        'comment_count'
    ]

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

        logger.info("MetadataManager inicializado")

    def extract_csv_fields(
        self,
        metadata: Dict[str, Any],
        csv_extra_fields: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Extrai os 12 campos necessarios para o CSV.

        Args:
            metadata: Dicionario com metadados do yt-dlp
            csv_extra_fields: Campos extras do CSV de input (ID_Grupo, Nome_Artista, etc)

        Returns:
            Dicionario com os 12 campos do CSV
        """
        # Campos do yt-dlp (reduzidos - removidos upload_date, uploader, uploader_id)
        csv_data = {
            'id': metadata.get('id', ''),
            'title': sanitize_string(metadata.get('title', '')),
            'duration': metadata.get('duration', 0),
            'view_count': metadata.get('view_count', 0),
            'like_count': metadata.get('like_count', 0),
            'comment_count': metadata.get('comment_count', 0)
        }

        # Adicionar campos do CSV de input (se fornecidos)
        if csv_extra_fields:
            csv_data['ID_Grupo'] = csv_extra_fields.get('ID_Grupo', '')
            csv_data['Grupo_Maior'] = sanitize_string(csv_extra_fields.get('Grupo_Maior', ''))
            csv_data['ID_Subgrupo'] = csv_extra_fields.get('ID_Subgrupo', '')
            csv_data['Subgrupo'] = sanitize_string(csv_extra_fields.get('Subgrupo', ''))
            csv_data['Nome_Artista'] = sanitize_string(csv_extra_fields.get('Nome_Artista', ''))
            csv_data['Genero_Vocalista'] = csv_extra_fields.get('Genero_Vocalista', '')
        else:
            # Valores vazios se nao fornecidos (modo single URL sem CSV)
            csv_data['ID_Grupo'] = ''
            csv_data['Grupo_Maior'] = ''
            csv_data['ID_Subgrupo'] = ''
            csv_data['Subgrupo'] = ''
            csv_data['Nome_Artista'] = ''
            csv_data['Genero_Vocalista'] = ''

        # Garantir tipos corretos
        csv_data['duration'] = int(csv_data['duration']) if csv_data['duration'] else 0
        csv_data['view_count'] = int(csv_data['view_count']) if csv_data['view_count'] else 0
        csv_data['like_count'] = int(csv_data['like_count']) if csv_data['like_count'] else 0
        csv_data['comment_count'] = int(csv_data['comment_count']) if csv_data['comment_count'] else 0

        return csv_data

    def save_json_metadata(
        self,
        metadata: Dict[str, Any],
        output_path: Path,
        csv_extra_fields: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Salva metadados completos em JSON (backup).

        Args:
            metadata: Dicionario com metadados completos
            output_path: Caminho do arquivo JSON
            csv_extra_fields: Campos extras do CSV de input

        Returns:
            True se salvou com sucesso
        """
        try:
            # Extrair os 12 campos do CSV para o JSON
            csv_fields = self.extract_csv_fields(metadata, csv_extra_fields)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(csv_fields, f, ensure_ascii=False, indent=2)

            logger.debug(f"JSON salvo: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Erro ao salvar JSON {output_path}: {str(e)}")
            return False

    def load_json_metadata(self, json_path: Path) -> Optional[Dict[str, Any]]:
        """
        Carrega metadados de um arquivo JSON.

        Args:
            json_path: Caminho do arquivo JSON

        Returns:
            Dicionario com metadados ou None se falhar
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Erro ao carregar JSON {json_path}: {str(e)}")
            return None

    def consolidate_metadata_csv(
        self,
        metadata_dir: Path,
        output_csv_path: Path
    ) -> bool:
        """
        Consolida todos os JSONs de um diretorio em um CSV.

        Args:
            metadata_dir: Diretorio com arquivos .json
            output_csv_path: Caminho do CSV de saida

        Returns:
            True se consolidou com sucesso
        """
        json_files = list(metadata_dir.glob("*.json"))

        if not json_files:
            logger.warning(f"Nenhum arquivo JSON encontrado em {metadata_dir}")
            return False

        logger.info(f"Consolidando {len(json_files)} metadados em CSV")

        rows = []

        for json_file in json_files:
            metadata = self.load_json_metadata(json_file)
            if metadata:
                rows.append(metadata)

        if not rows:
            logger.error("Nenhum metadado valido para consolidar")
            return False

        try:
            # Escrever CSV com pipe separator
            with open(output_csv_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=self.CSV_FIELDS,
                    delimiter='|'
                )
                writer.writeheader()
                writer.writerows(rows)

            logger.info(f"CSV consolidado salvo: {output_csv_path}")
            logger.info(f"Total de registros: {len(rows)}")
            return True

        except Exception as e:
            logger.error(f"Erro ao salvar CSV {output_csv_path}: {str(e)}")
            return False

    def append_to_global_csv(
        self,
        local_csv_path: Path,
        global_csv_path: Path
    ) -> bool:
        """
        Adiciona registros de um CSV local ao CSV global (metadata_global.csv).

        Args:
            local_csv_path: Caminho do CSV local (metadata.csv de uma pasta)
            global_csv_path: Caminho do CSV global (metadata_global.csv)

        Returns:
            True se adicionou com sucesso
        """
        if not local_csv_path.exists():
            logger.error(f"CSV local nao existe: {local_csv_path}")
            return False

        try:
            # Ler CSV local
            with open(local_csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter='|')
                rows = list(reader)

            if not rows:
                logger.warning(f"CSV local esta vazio: {local_csv_path}")
                return False

            # Criar header se global nao existe
            file_exists = global_csv_path.exists()

            # Append ao CSV global
            with open(global_csv_path, 'a', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=self.CSV_FIELDS,
                    delimiter='|'
                )

                # Escrever header apenas se arquivo novo
                if not file_exists:
                    writer.writeheader()

                writer.writerows(rows)

            logger.info(f"Adicionados {len(rows)} registros ao CSV global")
            return True

        except Exception as e:
            logger.error(f"Erro ao adicionar ao CSV global: {str(e)}")
            return False

    def validate_csv(self, csv_path: Path) -> bool:
        """
        Valida integridade de um arquivo CSV.

        Args:
            csv_path: Caminho do arquivo CSV

        Returns:
            True se CSV esta valido
        """
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter='|')

                # Verificar cabecalho
                if reader.fieldnames != self.CSV_FIELDS:
                    logger.error(f"Cabecalho invalido no CSV: {csv_path}")
                    logger.error(f"Esperado: {self.CSV_FIELDS}")
                    logger.error(f"Encontrado: {reader.fieldnames}")
                    return False

                # Verificar linhas
                row_count = 0
                for row in reader:
                    row_count += 1

                    # Verificar campos obrigatorios
                    if not row.get('id'):
                        logger.error(f"Linha {row_count}: campo 'id' vazio")
                        return False

                logger.info(f"CSV valido: {row_count} registros")
                return True

        except Exception as e:
            logger.error(f"Erro ao validar CSV {csv_path}: {str(e)}")
            return False
