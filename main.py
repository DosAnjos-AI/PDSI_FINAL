"""
Script principal do Downloader Local PDSI.

Orquestra download, segmentacao e normalizacao de audios do YouTube.
"""

import sys
from pathlib import Path
import signal
from typing import Optional, Dict

# Adicionar src/ ao path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import config
from logger import get_logger
from utils import detect_url_type, extract_source_id, ensure_dir, format_duration, random_delay
from youtube_downloader import YouTubeDownloader
from metadata_manager import MetadataManager
from audio_segmenter import AudioSegmenter
from audio_normalizer import AudioNormalizer
from skip_manager import SkipManager
from csv_input_manager import CSVInputManager
from source_mapper import SourceMapper


logger = get_logger()


class DownloaderPDSI:
    """
    Classe principal que gerencia todo o fluxo de processamento.
    """

    def __init__(self):
        """Inicializa o downloader"""
        self.base_dir = Path(__file__).parent
        self.interrupted = False

        # Diretorios
        self.temp_dir = self.base_dir / "temp"
        self.output_dir = self.base_dir / "output"
        self.input_dir = self.base_dir / "input"

        # Componentes
        self.youtube_dl = None
        self.metadata_mgr = None
        self.segmenter = None
        self.normalizer = None
        self.skip_mgr = None
        self.csv_input_mgr = None
        self.source_mapper = None

        # Estatisticas
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0
        }

        # Handler para Ctrl+C
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, signum, frame):
        """Handler para interrupcao (Ctrl+C)"""
        logger.warning("\nInterrupcao detectada - salvando estado...")
        self.interrupted = True

    def validate_dependencies(self) -> bool:
        """
        Valida todas as dependencias obrigatorias.

        Returns:
            True se todas as dependencias estao OK
        """
        logger.info("Validando dependencias...")

        errors = []

        # Validar SOX
        if not AudioNormalizer.check_sox_available():
            errors.append(
                "SOX nao encontrado. Instale com:\n"
                "  Ubuntu/Debian: sudo apt-get install sox libsox-fmt-all\n"
                "  macOS: brew install sox"
            )
        else:
            logger.info("SOX: OK")

        # Validar yt-dlp
        try:
            import subprocess
            result = subprocess.run(
                ['yt-dlp', '--version'],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info("yt-dlp: OK")
            else:
                errors.append("yt-dlp instalado mas nao funcional")
        except FileNotFoundError:
            errors.append(
                "yt-dlp nao encontrado. Instale com:\n"
                "  pip install yt-dlp"
            )
        except Exception as e:
            errors.append(f"Erro ao validar yt-dlp: {str(e)}")

        # Validar pydub
        try:
            from pydub import AudioSegment
            logger.info("pydub: OK")
        except ImportError:
            errors.append(
                "pydub nao encontrado. Instale com:\n"
                "  pip install pydub"
            )

        # Validar ffmpeg (necessario para pydub)
        try:
            import subprocess
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info("ffmpeg: OK")
            else:
                errors.append("ffmpeg instalado mas nao funcional")
        except FileNotFoundError:
            errors.append(
                "ffmpeg nao encontrado. Instale com:\n"
                "  Ubuntu/Debian: sudo apt-get install ffmpeg\n"
                "  macOS: brew install ffmpeg"
            )

        if errors:
            logger.error("ERRO: Dependencias faltando:")
            for error in errors:
                logger.error(f"  - {error}")
            return False

        logger.info("Todas as dependencias estao OK")
        return True

    def validate_config(self) -> bool:
        """
        Valida configuracoes do config.py.

        Returns:
            True se config esta valido
        """
        logger.info("Validando configuracoes...")

        errors = []

        # Validar duracoes
        if config.MIN_DURATION > config.MAX_DURATION:
            errors.append("MIN_DURATION nao pode ser maior que MAX_DURATION")

        if config.SEGMENT_DURATION < 10:
            errors.append("SEGMENT_DURATION deve ser >= 10 segundos")

        # Validar delays
        if config.DELAY_MIN > config.DELAY_MAX:
            errors.append("DELAY_MIN nao pode ser maior que DELAY_MAX")

        # Validar URL se modo single
        if not config.USE_BATCH_FILE:
            if not config.URL or config.URL == "https://www.youtube.com/watch?v=VIDEO_ID":
                errors.append("URL nao configurada em config.py")

        # Validar batch file se modo batch
        if config.USE_BATCH_FILE:
            csv_files = list(self.input_dir.glob("*.csv"))
            if not csv_files:
                errors.append("USE_BATCH_FILE=True mas nenhum arquivo .csv encontrado em input/")

        if errors:
            logger.error("ERRO: Configuracoes invalidas:")
            for error in errors:
                logger.error(f"  - {error}")
            return False

        logger.info("Configuracoes validas")
        return True

    def initialize_components(self):
        """Inicializa todos os componentes"""
        logger.info("Inicializando componentes...")

        # Criar diretorios
        ensure_dir(self.temp_dir)
        ensure_dir(self.output_dir)
        ensure_dir(self.input_dir)

        # Inicializar componentes
        self.youtube_dl = YouTubeDownloader(self.temp_dir)
        self.metadata_mgr = MetadataManager(self.output_dir)
        self.segmenter = AudioSegmenter()
        self.normalizer = AudioNormalizer()
        self.skip_mgr = SkipManager(self.output_dir)
        self.csv_input_mgr = CSVInputManager(self.input_dir)
        self.source_mapper = SourceMapper(self.output_dir)

        logger.info("Componentes inicializados")

    def get_urls_to_process(self) -> list:
        """
        Retorna lista de URLs/dicts para processar.

        Returns:
            Lista de URLs (modo single) ou lista de dicts (modo batch)
        """
        if config.USE_BATCH_FILE:
            # Modo batch: ler arquivos CSV
            logger.info("Modo BATCH_FILE: lendo CSVs")

            links_data = self.csv_input_mgr.get_all_links()

            if not links_data:
                logger.error("Nenhum link valido encontrado nos CSVs")
                return []

            logger.info(f"Encontrados {len(links_data)} links nos CSVs")
            return links_data
        else:
            # Modo single: URL do config (retorna como dict para consistencia)
            logger.info("Modo URL UNICA")
            return [{
                'url': config.URL,
                'ID_Grupo': '',
                'Grupo_Maior': '',
                'ID_Subgrupo': '',
                'Subgrupo': '',
                'Nome_Artista': '',
                'Genero_Vocalista': '',
                'csv_file': ''
            }]

    def process_video(
        self,
        video_id: str,
        source_id: str,
        metadata: dict,
        csv_extra_fields: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Processa um video completo: download -> segment -> normalize -> save.

        Args:
            video_id: ID do video
            source_id: ID da fonte
            metadata: Metadados do video
            csv_extra_fields: Campos extras do CSV de input

        Returns:
            True se processou com sucesso
        """
        if self.interrupted:
            return False

        try:
            # Diretorios
            video_temp_dir = self.temp_dir / source_id / video_id

            # Determinar nome da pasta de output
            if config.NOME_PASTA_OUTPUT == "default":
                output_folder_name = source_id
            else:
                output_folder_name = config.NOME_PASTA_OUTPUT

            video_output_dir = self.output_dir / output_folder_name
            metadata_dir = video_output_dir / "metadados"
            ensure_dir(metadata_dir)

            # Caminhos dos arquivos
            original_audio = video_temp_dir / f"original.{config.AUDIO_FORMAT}"
            segmented_audio = video_temp_dir / f"segmented.{config.AUDIO_FORMAT}"
            normalized_audio = video_temp_dir / f"normalized.{config.AUDIO_FORMAT}"
            final_audio = video_output_dir / f"{video_id}.{config.AUDIO_FORMAT}"

            # 1. Download (ja foi feito no youtube_downloader)
            if not original_audio.exists():
                logger.error(f"Audio original nao encontrado: {original_audio}")
                return False

            # 2. Segmentar
            logger.info("Segmentando audio...")
            if not self.segmenter.segment_audio(original_audio, segmented_audio):
                logger.error("Falha na segmentacao")
                return False

            # 3. Normalizar
            logger.info("Normalizando audio...")
            if not self.normalizer.normalize_audio(segmented_audio, normalized_audio):
                logger.error("Falha na normalizacao")
                return False

            # 4. Mover para output
            logger.info("Movendo para output...")
            import shutil
            shutil.copy2(normalized_audio, final_audio)

            if not final_audio.exists():
                logger.error("Falha ao copiar para output")
                return False

            # 5. Salvar metadados JSON
            json_path = metadata_dir / f"{video_id}.json"
            self.metadata_mgr.save_json_metadata(
                metadata,
                json_path,
                csv_extra_fields=csv_extra_fields
            )

            # 6. Cleanup temp (se configurado)
            if config.AUTO_CLEANUP_TEMP:
                logger.info("Limpando temp...")
                if config.KEEP_ORIGINAL_AUDIO:
                    # Manter apenas original
                    segmented_audio.unlink(missing_ok=True)
                    normalized_audio.unlink(missing_ok=True)
                else:
                    # Deletar tudo
                    shutil.rmtree(video_temp_dir, ignore_errors=True)

            logger.info(f"Video processado com sucesso: {video_id}")
            return True

        except Exception as e:
            logger.error(f"Erro ao processar video {video_id}: {str(e)}")
            return False

    def process_url(self, link_data: Dict[str, str]):
        """
        Processa uma URL completa.

        Args:
            link_data: Dicionario com URL e campos extras do CSV
        """
        url = link_data.get('url', '')

        logger.info("="*60)
        logger.info(f"Processando URL: {url}")

        # Extrair campos extras do CSV
        csv_extra_fields = {
            'ID_Grupo': link_data.get('ID_Grupo', ''),
            'Grupo_Maior': link_data.get('Grupo_Maior', ''),
            'ID_Subgrupo': link_data.get('ID_Subgrupo', ''),
            'Subgrupo': link_data.get('Subgrupo', ''),
            'Nome_Artista': link_data.get('Nome_Artista', ''),
            'Genero_Vocalista': link_data.get('Genero_Vocalista', '')
        }

        try:
            # Extrair lista de videos
            video_ids, source_id = self.youtube_dl.get_video_ids_from_url(url)

            self.stats['total'] += len(video_ids)

            logger.info(f"Total de videos: {len(video_ids)}")

            # Processar cada video
            for idx, video_id in enumerate(video_ids, 1):
                if self.interrupted:
                    logger.warning("Processamento interrompido pelo usuario")
                    break

                logger.info("-"*60)
                logger.info(f"[{idx}/{len(video_ids)}] Processando: {video_id}")

                # Verificar skip
                if self.skip_mgr.is_processed(video_id):
                    logger.info("SKIP: Video ja processado anteriormente")
                    self.stats['skipped'] += 1
                    continue

                # Obter metadados
                metadata = self.youtube_dl.get_video_metadata(video_id)
                if not metadata:
                    logger.error("Falha ao obter metadados")
                    self.stats['failed'] += 1
                    continue

                # Verificar filtros
                should_skip, reason = self.youtube_dl.should_skip_video(metadata)
                if should_skip:
                    logger.info(f"SKIP: {reason}")
                    self.stats['skipped'] += 1
                    continue

                # Download
                audio_path = self.youtube_dl.download_audio(video_id, source_id)
                if not audio_path:
                    logger.error("Falha no download")
                    self.stats['failed'] += 1
                    continue

                # Processar (segment + normalize)
                if self.process_video(video_id, source_id, metadata, csv_extra_fields=csv_extra_fields):
                    # Adicionar aos processados
                    self.skip_mgr.add_processed(video_id)
                    self.stats['success'] += 1
                else:
                    self.stats['failed'] += 1

                # Delay entre videos
                if idx < len(video_ids):
                    delay = random_delay(config.DELAY_MIN, config.DELAY_MAX)
                    logger.info(f"Delay: {delay}s")

            # Consolidar metadados em CSV
            logger.info("Consolidando metadados em CSV...")

            # Determinar pasta de output
            if config.NOME_PASTA_OUTPUT == "default":
                output_folder_name = source_id
            else:
                output_folder_name = config.NOME_PASTA_OUTPUT

            metadata_dir = self.output_dir / output_folder_name / "metadados"
            csv_path = metadata_dir / "metadata.csv"

            self.metadata_mgr.consolidate_metadata_csv(metadata_dir, csv_path)

        except Exception as e:
            logger.error(f"Erro ao processar URL: {str(e)}")

    def show_statistics(self):
        """Mostra estatisticas finais"""
        logger.info("="*60)
        logger.info("PROCESSAMENTO CONCLUIDO")
        logger.info("="*60)
        logger.info(f"Total de videos: {self.stats['total']}")
        logger.info(f"Sucessos: {self.stats['success']}")
        logger.info(f"Falhas: {self.stats['failed']}")
        logger.info(f"Skips: {self.stats['skipped']}")
        logger.info("="*60)

    def run(self):
        """Executa o fluxo completo"""
        logger.info("="*60)
        logger.info("DOWNLOADER LOCAL PDSI - Iniciando")
        logger.info("="*60)

        # 1. Validar dependencias
        if not self.validate_dependencies():
            logger.error("Erro fatal: dependencias faltando")
            sys.exit(1)

        # 2. Validar configuracoes
        if not self.validate_config():
            logger.error("Erro fatal: configuracoes invalidas")
            sys.exit(1)

        # 3. Inicializar componentes
        self.initialize_components()

        # 4. Obter URLs/links
        links_data = self.get_urls_to_process()
        if not links_data:
            logger.error("Nenhuma URL para processar")
            sys.exit(1)

        # 5. Processar cada link
        for link_idx, link_data in enumerate(links_data, 1):
            if self.interrupted:
                break

            logger.info(f"\nProcessando link {link_idx}/{len(links_data)}")
            self.process_url(link_data)

        # 6. Mostrar estatisticas
        self.show_statistics()

        # 7. Deletar CSVs processados (se configurado)
        if config.USE_BATCH_FILE and config.DELETE_PROCESSED_CSV:
            if self.stats['success'] > 0 and not self.interrupted:
                logger.info("Deletando CSVs processados...")
                self.csv_input_mgr.delete_processed_csvs()

        if self.interrupted:
            logger.warning("Processamento foi interrompido - estado salvo")
            sys.exit(130)


def main():
    """Funcao principal"""
    try:
        downloader = DownloaderPDSI()
        downloader.run()
    except KeyboardInterrupt:
        logger.warning("Interrompido pelo usuario")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Erro fatal: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
