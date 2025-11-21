"""
Segmentador de audio usando pydub.
Corta primeiros X segundos de arquivos de audio.
"""

from pathlib import Path
from typing import Optional
from pydub import AudioSegment
import sys

# Adicionar diretorio pai ao path para importar config
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from src.logger import get_logger


logger = get_logger()


class AudioSegmenter:
    """
    Gerencia segmentacao de arquivos de audio.

    Utiliza pydub para cortar primeiros X segundos do audio.
    """

    def __init__(self):
        """Inicializa o segmentador"""
        logger.info("AudioSegmenter inicializado")

    def segment_audio(
        self,
        input_path: Path,
        output_path: Path,
        duration_seconds: Optional[int] = None
    ) -> bool:
        """
        Corta primeiros X segundos de um audio.

        Args:
            input_path: Caminho do audio original
            output_path: Caminho do audio segmentado
            duration_seconds: Duracao em segundos (default: config.SEGMENT_DURATION)

        Returns:
            True se segmentou com sucesso
        """
        if duration_seconds is None:
            duration_seconds = config.SEGMENT_DURATION

        input_path = Path(input_path)
        output_path = Path(output_path)

        if not input_path.exists():
            logger.error(f"Arquivo de entrada nao existe: {input_path}")
            return False

        logger.info(f"Segmentando audio: {input_path.name}")
        logger.info(f"Duracao alvo: {duration_seconds}s")

        try:
            # Carregar audio
            audio = AudioSegment.from_file(str(input_path))

            # Duracao original em milissegundos
            duration_ms = len(audio)
            duration_s = duration_ms / 1000

            logger.info(f"Duracao original: {duration_s:.1f}s")

            # Converter segundos para milissegundos
            target_ms = duration_seconds * 1000

            # Se audio e menor que o alvo, validar tolerancia
            if duration_ms < target_ms:
                difference = duration_seconds - duration_s

                # Tolerancia: +-20s conforme especificado
                if abs(difference) > 20:
                    logger.error(
                        f"Duracao {duration_s:.1f}s muito diferente do alvo {duration_seconds}s "
                        f"(diferenca: {difference:.1f}s, tolerancia: +-20s)"
                    )
                    return False
                else:
                    logger.warning(
                        f"Audio menor que alvo ({duration_s:.1f}s < {duration_seconds}s), "
                        f"mas dentro da tolerancia. Usando audio completo."
                    )
                    segment = audio
            else:
                # Cortar primeiros X segundos
                segment = audio[:target_ms]

            # Salvar segmento
            segment.export(
                str(output_path),
                format=config.AUDIO_FORMAT
            )

            # Validar arquivo criado
            if not output_path.exists():
                logger.error(f"Arquivo segmentado nao foi criado: {output_path}")
                return False

            final_duration_s = len(segment) / 1000
            logger.info(f"Segmento salvo: {output_path.name} ({final_duration_s:.1f}s)")

            return True

        except Exception as e:
            logger.error(f"Erro ao segmentar audio {input_path.name}: {str(e)}")
            return False

    def validate_segment(
        self,
        segment_path: Path,
        expected_duration: Optional[int] = None
    ) -> bool:
        """
        Valida integridade de um segmento de audio.

        Args:
            segment_path: Caminho do segmento
            expected_duration: Duracao esperada em segundos (default: config.SEGMENT_DURATION)

        Returns:
            True se segmento esta valido
        """
        if expected_duration is None:
            expected_duration = config.SEGMENT_DURATION

        segment_path = Path(segment_path)

        if not segment_path.exists():
            logger.error(f"Segmento nao existe: {segment_path}")
            return False

        try:
            audio = AudioSegment.from_file(str(segment_path))
            duration_s = len(audio) / 1000

            # Validar com tolerancia de +-20s
            difference = abs(duration_s - expected_duration)

            if difference > 20:
                logger.error(
                    f"Segmento invalido: duracao {duration_s:.1f}s "
                    f"muito diferente do esperado {expected_duration}s"
                )
                return False

            logger.debug(f"Segmento valido: {segment_path.name} ({duration_s:.1f}s)")
            return True

        except Exception as e:
            logger.error(f"Erro ao validar segmento {segment_path.name}: {str(e)}")
            return False
