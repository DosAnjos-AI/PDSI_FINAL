"""
Normalizador de audio usando SOX.
Normaliza volume, converte para mono e ajusta sample rate.
"""

import subprocess
from pathlib import Path
from typing import Optional
import sys

# Adicionar diretorio pai ao path para importar config
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from src.logger import get_logger


logger = get_logger()


class AudioNormalizer:
    """
    Gerencia normalizacao de audio usando SOX.

    Aplica:
    - Normalizacao de volume (norm)
    - Conversao stereo -> mono
    - Ajuste de sample rate
    """

    def __init__(self):
        """
        Inicializa o normalizador.

        Raises:
            RuntimeError: Se SOX nao estiver instalado
        """
        if not self.check_sox_available():
            raise RuntimeError(
                "SOX nao esta instalado no sistema. "
                "Instale com: sudo apt-get install sox libsox-fmt-all"
            )

        logger.info("AudioNormalizer inicializado")

    @staticmethod
    def check_sox_available() -> bool:
        """
        Verifica se SOX esta disponivel no sistema.

        Returns:
            True se SOX esta instalado
        """
        try:
            result = subprocess.run(
                ['sox', '--version'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def normalize_audio(
        self,
        input_path: Path,
        output_path: Path,
        target_db: Optional[float] = None,
        to_mono: Optional[bool] = None,
        sample_rate: Optional[int] = None
    ) -> bool:
        """
        Normaliza audio usando SOX.

        Args:
            input_path: Caminho do audio original
            output_path: Caminho do audio normalizado
            target_db: Nivel de normalizacao em dB (default: config.NORMALIZE_TARGET)
            to_mono: Converter para mono (default: config.CONVERT_TO_MONO)
            sample_rate: Sample rate alvo (default: config.TARGET_SAMPLE_RATE)

        Returns:
            True se normalizou com sucesso
        """
        if target_db is None:
            target_db = config.NORMALIZE_TARGET

        if to_mono is None:
            to_mono = config.CONVERT_TO_MONO

        if sample_rate is None:
            sample_rate = config.TARGET_SAMPLE_RATE

        input_path = Path(input_path)
        output_path = Path(output_path)

        if not input_path.exists():
            logger.error(f"Arquivo de entrada nao existe: {input_path}")
            return False

        logger.info(f"Normalizando audio: {input_path.name}")
        logger.info(f"Target: {target_db}dB, Mono: {to_mono}, Sample Rate: {sample_rate}Hz")

        # Construir comando SOX
        # sox input.mp3 output.mp3 norm TARGET channels 1 rate SAMPLE_RATE
        cmd = ['sox', str(input_path), str(output_path)]

        # Normalizacao
        cmd.extend(['norm', str(target_db)])

        # Conversao para mono
        if to_mono:
            cmd.extend(['channels', '1'])

        # Sample rate
        cmd.extend(['rate', str(sample_rate)])

        logger.debug(f"Comando SOX: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=config.TIMEOUT_SECONDS,
                check=True
            )

            # Verificar se arquivo foi criado
            if not output_path.exists():
                logger.error(f"Arquivo normalizado nao foi criado: {output_path}")
                return False

            logger.info(f"Audio normalizado salvo: {output_path.name}")
            return True

        except subprocess.TimeoutExpired:
            logger.error(f"Timeout ao normalizar audio: {input_path.name}")
            return False

        except subprocess.CalledProcessError as e:
            logger.error(f"Erro no SOX ao normalizar {input_path.name}: {e.stderr}")
            return False

        except Exception as e:
            logger.error(f"Erro inesperado ao normalizar {input_path.name}: {str(e)}")
            return False

    def get_audio_info(self, audio_path: Path) -> Optional[dict]:
        """
        Extrai informacoes de um arquivo de audio usando SOX.

        Args:
            audio_path: Caminho do arquivo de audio

        Returns:
            Dicionario com informacoes (channels, sample_rate, duration) ou None
        """
        audio_path = Path(audio_path)

        if not audio_path.exists():
            logger.error(f"Arquivo nao existe: {audio_path}")
            return None

        try:
            # sox --info audio.mp3
            result = subprocess.run(
                ['sox', '--info', str(audio_path)],
                capture_output=True,
                text=True,
                timeout=10,
                check=True
            )

            # Parsear output
            info = {}
            for line in result.stdout.split('\n'):
                if 'Channels' in line:
                    info['channels'] = int(line.split(':')[1].strip())
                elif 'Sample Rate' in line:
                    info['sample_rate'] = int(line.split(':')[1].strip())
                elif 'Duration' in line:
                    # Formato: \"Duration : 00:02:30.00 = 3750000 samples\"
                    duration_str = line.split('=')[0].split(':')[1].strip()
                    info['duration'] = duration_str

            return info

        except Exception as e:
            logger.error(f"Erro ao obter info do audio {audio_path.name}: {str(e)}")
            return None
