"""
Modulo de download de audios do YouTube usando yt-dlp.
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
import sys

# Adicionar diretorio pai ao path para importar config
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from src.logger import get_logger
from src.utils import detect_url_type, extract_source_id, ensure_dir, random_delay


logger = get_logger()


class YouTubeDownloader:
    """
    Gerenciador de downloads de audios do YouTube.

    Utiliza yt-dlp para download de videos, playlists e canais.
    """

    def __init__(self, temp_dir: Optional[Path] = None):
        """
        Inicializa o downloader.

        Args:
            temp_dir: Diretorio temporario para downloads (default: temp/)
        """
        if temp_dir is None:
            base_dir = Path(__file__).parent.parent
            temp_dir = base_dir / "temp"

        self.temp_dir = Path(temp_dir)
        ensure_dir(self.temp_dir)

        logger.info("YouTubeDownloader inicializado")

    def get_video_ids_from_url(self, url: str) -> tuple[List[str], str]:
        """
        Extrai lista de IDs de videos de uma URL.

        Args:
            url: URL do YouTube (video, playlist ou canal)

        Returns:
            Tupla (lista de video_ids, source_id)

        Raises:
            RuntimeError: Se falhar ao extrair IDs
        """
        url_type = detect_url_type(url)
        source_id = extract_source_id(url, url_type)

        logger.info(f"Processando URL tipo '{url_type}': {url}")
        logger.info(f"Source ID: {source_id}")

        # Comando yt-dlp para extrair IDs (sem baixar)
        cmd = [
            "yt-dlp",
            "--flat-playlist",
            "--print", "id",
            "--no-warnings",
            url
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=config.TIMEOUT_SECONDS,
                check=True
            )

            video_ids = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]

            if not video_ids:
                raise RuntimeError(f"Nenhum video encontrado na URL: {url}")

            logger.info(f"Encontrados {len(video_ids)} videos")
            return video_ids, source_id

        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Timeout ao processar URL: {url}")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Erro ao extrair IDs: {e.stderr}")

    def get_video_metadata(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Extrai metadados completos de um video.

        Args:
            video_id: ID do video do YouTube

        Returns:
            Dicionario com metadados ou None se falhar
        """
        url = f"https://www.youtube.com/watch?v={video_id}"

        cmd = [
            "yt-dlp",
            "--dump-json",
            "--no-warnings",
            url
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=config.TIMEOUT_SECONDS,
                check=True
            )

            metadata = json.loads(result.stdout)
            return metadata

        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, json.JSONDecodeError) as e:
            logger.error(f"Erro ao extrair metadados do video {video_id}: {str(e)}")
            return None

    def should_skip_video(self, metadata: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Verifica se video deve ser pulado baseado nos filtros do config.

        Args:
            metadata: Metadados do video

        Returns:
            Tupla (deve_pular, razao)
        """
        duration = metadata.get('duration', 0)

        # Verificar duracao minima
        if duration < config.MIN_DURATION:
            return True, f"Duracao {duration}s < minimo {config.MIN_DURATION}s"

        # Verificar duracao maxima
        if duration > config.MAX_DURATION:
            return True, f"Duracao {duration}s > maximo {config.MAX_DURATION}s"

        # Verificar se e menor que segmento desejado
        if duration < config.SEGMENT_DURATION:
            return True, f"Duracao {duration}s < segmento {config.SEGMENT_DURATION}s"

        # Verificar Shorts
        if config.SKIP_SHORTS and duration < 60:
            return True, "YouTube Short detectado"

        return False, None

    def download_audio(
        self,
        video_id: str,
        source_id: str,
        output_filename: str = "original"
    ) -> Optional[Path]:
        """
        Baixa audio de um video.

        Args:
            video_id: ID do video
            source_id: ID da fonte (playlist/canal/video)
            output_filename: Nome do arquivo de saida (sem extensao)

        Returns:
            Path do arquivo baixado ou None se falhar
        """
        # Criar diretorio de destino: temp/source_id/video_id/
        video_dir = self.temp_dir / source_id / video_id
        ensure_dir(video_dir)

        output_path = video_dir / f"{output_filename}.{config.AUDIO_FORMAT}"

        # Se ja existe, nao baixar novamente
        if output_path.exists():
            logger.info(f"Audio ja existe: {output_path}")
            return output_path

        url = f"https://www.youtube.com/watch?v={video_id}"

        # Comando yt-dlp para download de audio
        cmd = [
            "yt-dlp",
            "-f", "bestaudio",
            "-x",  # Extrair audio
            "--audio-format", config.AUDIO_FORMAT,
            "--audio-quality", str(config.AUDIO_QUALITY),
            "--output", str(output_path),
            "--no-warnings",
            "--no-playlist",
            url
        ]

        logger.info(f"Baixando audio: {video_id}")

        for attempt in range(config.RETRY_ATTEMPTS + 1):
            try:
                subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=config.TIMEOUT_SECONDS,
                    check=True
                )

                if output_path.exists():
                    logger.info(f"Download concluido: {video_id}")
                    return output_path
                else:
                    raise RuntimeError("Arquivo nao foi criado")

            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, RuntimeError) as e:
                if attempt < config.RETRY_ATTEMPTS:
                    logger.warning(f"Tentativa {attempt + 1} falhou, tentando novamente...")
                else:
                    logger.error(f"Falha no download apos {attempt + 1} tentativas: {video_id}")
                    return None

        return None

    def process_url(
        self,
        url: str,
        skip_ids: set
    ) -> tuple[List[str], List[str], List[str]]:
        """
        Processa uma URL completa (video, playlist ou canal).

        Args:
            url: URL do YouTube
            skip_ids: Set de IDs ja processados (para skip)

        Returns:
            Tupla (sucessos, falhas, skips) com listas de video_ids
        """
        try:
            # Extrair lista de IDs
            video_ids, source_id = self.get_video_ids_from_url(url)
        except RuntimeError as e:
            logger.error(f"Erro ao processar URL: {str(e)}")
            return [], [url], []

        sucessos = []
        falhas = []
        skips = []

        total = len(video_ids)

        for idx, video_id in enumerate(video_ids, 1):
            logger.info(f"Processando [{idx}/{total}]: {video_id}")

            # Verificar se ja foi processado
            if video_id in skip_ids:
                logger.info(f"SKIP: Video ja processado anteriormente")
                skips.append(video_id)
                continue

            # Extrair metadados
            metadata = self.get_video_metadata(video_id)
            if not metadata:
                logger.error(f"Falha ao obter metadados: {video_id}")
                falhas.append(video_id)
                continue

            # Verificar filtros
            should_skip, reason = self.should_skip_video(metadata)
            if should_skip:
                logger.info(f"SKIP: {reason}")
                skips.append(video_id)
                continue

            # Baixar audio
            audio_path = self.download_audio(video_id, source_id)

            if audio_path:
                # Salvar metadados JSON
                json_path = audio_path.parent / f"{video_id}.json"
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)

                sucessos.append(video_id)

                # Delay randomico antes do proximo
                if idx < total:
                    delay = random_delay(config.DELAY_MIN, config.DELAY_MAX)
                    logger.info(f"Delay: {delay}s")
            else:
                falhas.append(video_id)

        logger.info(f"Processamento concluido - Sucessos: {len(sucessos)}, Falhas: {len(falhas)}, Skips: {len(skips)}")

        return sucessos, falhas, skips
