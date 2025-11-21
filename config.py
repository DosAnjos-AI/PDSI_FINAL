"""
Configuracoes centralizadas do Downloader Local PDSI.
Todos os parametros sao ajustaveis pelo usuario.
"""

# ==============================================================================
# MODO DE OPERACAO
# ==============================================================================

# Define se processa arquivo de batch ou URL unica
# True: Le arquivos CSV da pasta input/
# False: Processa URL definida abaixo
USE_BATCH_FILE = False

# ==============================================================================
# INPUT CSV (usado se USE_BATCH_FILE = True)
# ==============================================================================

# Deletar arquivos CSV apos processamento bem-sucedido
# True: Remove CSVs processados da pasta input/
# False: Mantem CSVs para referencia
DELETE_PROCESSED_CSV = False

# ==============================================================================
# INPUT - LINK UNICO (usado se USE_BATCH_FILE = False)
# ==============================================================================

# URL do YouTube (video, playlist ou canal)
# Exemplos:
#   Video:    "https://www.youtube.com/watch?v=VIDEO_ID"
#   Playlist: "https://www.youtube.com/playlist?list=PLAYLIST_ID"
#   Canal:    "https://www.youtube.com/@CHANNEL_NAME/videos"
URL = "https://www.youtube.com/watch?v=VIDEO_ID"

# ==============================================================================
# OUTPUT - NOMENCLATURA
# ==============================================================================

# Nome da pasta de saida em output/
# "default": Usa automaticamente o source_ID (playlist_ID, channel_ID ou video_ID)
# Qualquer string: Cria pasta com o nome especificado
# Exemplo: "minha_colecao" -> output/minha_colecao/
NOME_PASTA_OUTPUT = "default"

# ==============================================================================
# CONFIGURACOES DE AUDIO
# ==============================================================================

# Formato do audio final
# Opcoes: "mp3", "flac", "wav", "m4a", "ogg", "opus"
# Recomendado: "mp3" (melhor compatibilidade)
AUDIO_FORMAT = "mp3"

# Qualidade do audio em kbps
# Opcoes:
#   320: Qualidade maxima para MP3
#   256: Alta qualidade (otimo custo-beneficio)
#   192: Boa qualidade, arquivo menor
#   128: Qualidade basica
#   0 ou "best": Maxima qualidade disponivel
AUDIO_QUALITY = 320

# ==============================================================================
# FILTROS DE DURACAO
# ==============================================================================

# Duracao minima do video em segundos
# Videos com duracao menor que este valor serao pulados (skip)
# Exemplo: 150 = 2min 30s
MIN_DURATION = 150

# Duracao maxima do video em segundos
# Videos com duracao maior que este valor serao pulados (skip)
# Exemplo: 10000 = 2h 46min 40s
MAX_DURATION = 10000

# ==============================================================================
# SEGMENTACAO DE AUDIO
# ==============================================================================

# Duracao do segmento em segundos (primeiros X segundos do audio)
# O sistema cortara apenas o inicio do audio
# Restante sera descartado apos normalizacao
# Exemplo: 150 = primeiros 2min 30s
# Nota: Videos com duracao < SEGMENT_DURATION serao pulados
SEGMENT_DURATION = 150

# ==============================================================================
# NORMALIZACAO DE AUDIO (SOX)
# ==============================================================================

# Nivel alvo de normalizacao em decibeis (dB)
# Valores negativos reduzem o volume de pico
# Valores tipicos:
#   -3.0: Padrao para datasets de IA (recomendado)
#   -1.0: Quase no limite
#   0.0: Volume maximo (pode causar clipping)
NORMALIZE_TARGET = -3.0

# Converter audio de stereo para mono
# True: Converte para mono (recomendado para TTS/IA)
# False: Mantem stereo se disponivel
CONVERT_TO_MONO = True

# Taxa de amostragem alvo em Hz (sample rate)
# Valores comuns:
#   22050: Padrao para datasets de TTS
#   16000: Usado em reconhecimento de fala
#   44100: CD quality
#   48000: Professional audio
TARGET_SAMPLE_RATE = 22050

# ==============================================================================
# DELAY RANDOMICO
# ==============================================================================

# Delay minimo entre chamadas do yt-dlp em segundos
# Evita sobrecarga e possiveis bloqueios do YouTube
DELAY_MIN = 6

# Delay maximo entre chamadas do yt-dlp em segundos
# Um valor aleatorio entre MIN e MAX sera sorteado a cada download
DELAY_MAX = 14

# ==============================================================================
# FILTROS DE CONTEUDO
# ==============================================================================

# Pular YouTube Shorts (videos < 60s)
# True: Ignora Shorts automaticamente
# False: Processa normalmente (respeitando MIN_DURATION)
SKIP_SHORTS = True

# ==============================================================================
# LIMPEZA E MANUTENCAO
# ==============================================================================

# Deletar pasta temp/ apos processamento bem-sucedido
# True: Limpa automaticamente (recomendado)
# False: Mantem arquivos temporarios (util para debug)
AUTO_CLEANUP_TEMP = True

# Manter audio original nao-processado em output/
# True: Salva original.mp3 + processado.mp3
# False: Salva apenas o audio final normalizado (recomendado)
KEEP_ORIGINAL_AUDIO = False

# ==============================================================================
# RETRY E TIMEOUT
# ==============================================================================

# Numero de tentativas adicionais em caso de falha no download
# 0: Sem retry, pula imediatamente
# 1: Tenta mais uma vez antes de pular (recomendado)
# 2+: Multiplas tentativas (pode aumentar tempo total)
RETRY_ATTEMPTS = 1

# Timeout para cada download em segundos
# Apos este tempo sem resposta, o download e cancelado
# Exemplo: 300 = 5 minutos
TIMEOUT_SECONDS = 300

# ==============================================================================
# LIMITADOR DE AUDIOS POR LINK
# ==============================================================================

# Numero maximo de audios bem-sucedidos por link (playlist/canal)
# Aplica apenas em playlists e canais (nao em video unico)
# 0 = ilimitado (processa todos os videos do link)
# 25 = para apos baixar 25 sucessos (recomendado para datasets balanceados)
#
# Exemplo: Playlist tem 100 videos, MAX_AUDIOS_PER_LINK = 25
# Sistema baixa ate conseguir 25 sucessos (pode processar 30-40 videos no total
# devido a falhas/skips), depois para e vai para o proximo link
MAX_AUDIOS_PER_LINK = 25
