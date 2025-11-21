# Downloader Local PDSI

Sistema local de download e processamento de audios do YouTube com segmentacao e normalizacao.

## Funcionalidades

- Download de audios do YouTube (videos, playlists, canais)
- Segmentacao automatica (primeiros X segundos configuraveis)
- Normalizacao de audio com SOX (volume, mono, sample rate)
- Extracao de metadados (CSV pipe-separated + JSON backup)
- Sistema de skip inteligente (evita reprocessamento)
- Suporte a batch de multiplos links
- Limpeza automatica de arquivos temporarios
- Interrupcao segura (Ctrl+C salva estado)

## Requisitos

### Python
- Python 3.8 ou superior

### Dependencias Python
```bash
pip install -r requirements.txt
```

### Dependencias de Sistema

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install sox libsox-fmt-all ffmpeg
```

**macOS:**
```bash
brew install sox ffmpeg
```

**Windows:**
1. SOX: Baixar de https://sourceforge.net/projects/sox/
2. ffmpeg: Baixar de https://ffmpeg.org/download.html
3. Adicionar ambos ao PATH do sistema

## Instalacao

1. Clone o repositorio:
```bash
git clone https://github.com/DosAnjos-AI/downloader_PDSI.git
cd downloader_PDSI
git checkout downloader_local
```

2. Instale dependencias Python:
```bash
pip install -r requirements.txt
```

3. Instale dependencias de sistema (SOX, ffmpeg)

4. Configure o arquivo `config.py`

## Configuracao

Edite o arquivo `config.py` na raiz do projeto:

### Modo Single URL
```python
USE_BATCH_FILE = False
URL = "https://www.youtube.com/watch?v=VIDEO_ID"
```

### Modo Batch (CSV)
```python
USE_BATCH_FILE = True
DELETE_PROCESSED_CSV = False  # True para deletar CSVs apos processamento
```

Crie arquivo(s) CSV em `input/` com 7 colunas (pipe-separated):
```
ID_Grupo|Grupo_Maior|ID_Subgrupo|Subgrupo|Nome_Artista|Genero_Vocalista|Links_youtube
1|Rock|101|Rock Classico|Led Zeppelin|M|https://www.youtube.com/watch?v=VIDEO_ID1
1|Rock|102|Hard Rock|AC/DC|M|https://www.youtube.com/playlist?list=PLAYLIST_ID
2|Pop|201|Pop Internacional|Madonna|F|https://www.youtube.com/@CHANNEL_NAME/videos
```

Os campos do CSV serao incluidos nos metadados de saida.

### Parametros Importantes
```python
# Audio
AUDIO_FORMAT = "mp3"          # Formato final
AUDIO_QUALITY = 320           # Qualidade em kbps

# Segmentacao
SEGMENT_DURATION = 150        # Primeiros 150 segundos

# Normalizacao SOX
NORMALIZE_TARGET = -3.0       # Nivel em dB (padrao IA)
CONVERT_TO_MONO = True        # Converter para mono
TARGET_SAMPLE_RATE = 22050    # Sample rate (Hz)

# Filtros
MIN_DURATION = 150            # Duracao minima (skip se menor)
MAX_DURATION = 10000          # Duracao maxima
SKIP_SHORTS = True            # Pular YouTube Shorts

# Output
NOME_PASTA_OUTPUT = "default" # "default" usa Nome_Artista do CSV

# Limitador
MAX_AUDIOS_PER_LINK = 25      # 0 = ilimitado, 25 = para apos 25 sucessos
```

## Uso

### Executar
```bash
python main.py
```

### Interromper
- Pressione `Ctrl+C` para interromper
- Estado sera salvo automaticamente
- IDs processados ate o momento ficam registrados

### Verificar Logs
```bash
# Processamento geral
cat logs/processing.log

# Apenas erros
cat logs/errors.log
```

## Estrutura de Output

```
output/
├── processed_ids.json              # Log de IDs processados (skip)
├── metadata_global.csv             # CSV consolidado de todos os artistas
├── source_mapping.json             # Mapeamento fonte-pasta
└── {Nome_Artista}/                 # Pasta com nome do artista (sanitizado)
    ├── metadados/
    │   ├── metadata.csv            # CSV consolidado (12 campos)
    │   ├── video_001.json          # Backup JSON
    │   └── video_002.json
    ├── video_001.mp3               # Audio normalizado e segmentado
    └── video_002.mp3
```

Nota: Quando NOME_PASTA_OUTPUT = "default", o sistema usa Nome_Artista do CSV para criar pastas. Se o Nome_Artista estiver vazio, usa o source_ID. Nomes duplicados recebem sufixo numerico (_2, _3, etc).

### Formato CSV de Saida

Separador: pipe `|`
Encoding: UTF-8
Campos: 12

```
id|ID_Grupo|Grupo_Maior|ID_Subgrupo|Subgrupo|Nome_Artista|title|Genero_Vocalista|duration|view_count|like_count|comment_count
```

Os campos ID_Grupo, Grupo_Maior, ID_Subgrupo, Subgrupo, Nome_Artista e Genero_Vocalista sao preenchidos automaticamente quando se usa modo batch com CSVs de input.

## Fluxo de Processamento

1. Validar config.py e dependencias (SOX, yt-dlp, pydub, ffmpeg)
2. Carregar processed_ids.json (sistema de skip)
3. Ler URL(s) do config ou arquivos CSV de input
4. Para cada URL:
   - Detectar tipo (video/playlist/canal)
   - Extrair lista de video_IDs
5. Para cada video_ID:
   - Verificar limitador (MAX_AUDIOS_PER_LINK)
   - Verificar skip (ja processado?)
   - Verificar filtros (duracao, Shorts, etc)
   - Download audio -> temp/Nome_Artista/video_ID/original.mp3
   - Segmentar primeiros X segundos -> segmented.mp3
   - Normalizar com SOX -> normalized.mp3
   - Mover para output/Nome_Artista/video_ID.mp3
   - Salvar metadados JSON
   - Adicionar ID em processed_ids.json
   - Cleanup temp/ (se AUTO_CLEANUP_TEMP=True)
   - Delay randomico
6. Consolidar metadata.csv local e global
7. Mostrar estatisticas finais

## Troubleshooting

### Erro: SOX nao encontrado
```bash
# Ubuntu/Debian
sudo apt-get install sox libsox-fmt-all

# macOS
brew install sox

# Verificar instalacao
sox --version
```

### Erro: ffmpeg nao encontrado
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Verificar instalacao
ffmpeg -version
```

### Erro: yt-dlp nao funciona
```bash
# Atualizar para ultima versao
pip install --upgrade yt-dlp
```

### Erro: Video nao disponivel
- Video pode ser privado, removido ou bloqueado geograficamente
- Sistema pula automaticamente e continua proximo video
- Verifique `logs/errors.log` para detalhes

### Erro: Memoria insuficiente
- Processar playlists menores por vez
- Ativar `AUTO_CLEANUP_TEMP = True` no config
- Desativar `KEEP_ORIGINAL_AUDIO = False`

## Exemplos de Uso

### Exemplo 1: Video Unico
```python
# config.py
USE_BATCH_FILE = False
URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
SEGMENT_DURATION = 150
NOME_PASTA_OUTPUT = "video_teste"
```

```bash
$ python main.py
[INFO] Validando dependencias...
[INFO] SOX: OK
[INFO] yt-dlp: OK
[INFO] Processando URL tipo 'video': https://...
[INFO] [1/1] Processando: dQw4w9WgXcQ
[INFO] Baixando audio: dQw4w9WgXcQ
[INFO] Segmentando audio...
[INFO] Normalizando audio...
[INFO] Video processado com sucesso
[INFO] PROCESSAMENTO CONCLUIDO
[INFO] Sucessos: 1
```

### Exemplo 2: Playlist
```python
# config.py
USE_BATCH_FILE = False
URL = "https://www.youtube.com/playlist?list=PLxxx"
NOME_PASTA_OUTPUT = "default"  # Usa playlist_ID
```

### Exemplo 3: Batch de Links (CSV)
```python
# config.py
USE_BATCH_FILE = True
DELETE_PROCESSED_CSV = False
```

input/artistas.csv:
```
ID_Grupo|Grupo_Maior|ID_Subgrupo|Subgrupo|Nome_Artista|Genero_Vocalista|Links_youtube
1|Rock|101|Rock BR|Legiao Urbana|M|https://www.youtube.com/watch?v=video1
1|Rock|102|Rock BR|Titas|M|https://www.youtube.com/playlist?list=PLxxx
2|MPB|201|MPB|Elis Regina|F|https://www.youtube.com/@canal/videos
```

```bash
$ python main.py
[INFO] Modo BATCH_FILE: lendo CSVs
[INFO] Encontrados 3 links nos CSVs
[INFO] Processando link 1/3
...
```

## Reprocessar Videos

Se quiser reprocessar videos especificos:

1. Edite `output/processed_ids.json`
2. Remova os IDs desejados da lista
3. Execute `python main.py` novamente

Ou delete o arquivo inteiro para reprocessar tudo:
```bash
rm output/processed_ids.json
```

## Contribuindo

1. Fork o projeto
2. Crie uma branch: `git checkout -b feature/nova-funcionalidade`
3. Commit suas mudancas: `git commit -m 'Adiciona nova funcionalidade'`
4. Push para a branch: `git push origin feature/nova-funcionalidade`
5. Abra um Pull Request

## Licenca

Este projeto esta sob a licenca MIT.

## Autor

**DosAnjos-AI**
GitHub: https://github.com/DosAnjos-AI

## Changelog

### v1.1.0 (2025-01-21)
- Input CSV com 7 campos (ID_Grupo, Grupo_Maior, etc)
- Metadados expandidos para 12 campos
- Nome de pastas baseado em Nome_Artista do CSV
- Limitador de audios por link (MAX_AUDIOS_PER_LINK)
- CSV global consolidado (metadata_global.csv)
- Sanitizacao e numeracao de pastas duplicadas

### v1.0.0 (2025-01-20)
- Lancamento inicial
- Download de audios do YouTube
- Segmentacao automatica
- Normalizacao com SOX
- Sistema de skip
- Suporte a batch

---

**Versao:** 1.1.0
**Data:** 2025-01-21
**Branch:** downloader_local
**Repositorio:** https://github.com/DosAnjos-AI/downloader_PDSI
