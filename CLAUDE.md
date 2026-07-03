# Projeto CHELSA V2.1 — América do Sul

## Objetivo
Baixar dados climáticos mensais do CHELSA V2.1 recortados para a América do Sul, sem baixar os rasters globais inteiros, e depois fazer análises no Google Earth Engine (GEE).

---

## Variáveis e Período
| Variável | Descrição |
|---|---|
| `pr` | Precipitação |
| `pet` | Evapotranspiração potencial |
| `tas` | Temperatura média |

- **Período:** 1991–2020 (30 anos × 12 meses = 360 arquivos por variável)
- **Total:** 1080 arquivos

---

## Bounding Box — América do Sul (WGS84)
```
xmin = -82, ymin = -56, xmax = -34, ymax = 13
```

---

## Decisões Técnicas

### Download
- Usando `rasterio` com leitura por janela (windowed read) via HTTP range requests — sem baixar o raster global
- Saída: GeoTIFF com compressão DEFLATE, tileado 512×512
- Script: `download_chelsa_sa.py`
- Arquivos salvos em: `chelsa_sa/pr/`, `chelsa_sa/pet/`, `chelsa_sa/tas/`
- Nomenclatura: `CHELSA_{var}_{MM}_{YYYY}_SA.tif`
- Script é retomável: pula arquivos já existentes

### Servidor de origem
- **Servidor antigo (descartado):** `os.zhdk.cloud.switch.ch` — não tinha `pet`, e `pr`/`tas` cortavam em meados de 2019
- **Servidor atual (em uso):** `os.unil.cloud.switch.ch` — tem todas as variáveis e todos os anos

Padrão de URL atual:
```
https://os.unil.cloud.switch.ch/chelsa02/chelsa/global/monthly/{var}/{yyyy}/CHELSA_{var}_{MM}_{yyyy}_V.2.1.tif
```

### Análise / Normais Climatológicas
- Será feita no **Google Earth Engine (GEE)**
- Formato de trabalho: **Jupyter Notebook (`.ipynb`)** para exploração e visualização; `.py` para automações futuras
- Notebook de geração das normais: `gerando_normal.ipynb`

**Fluxo do `gerando_normal.ipynb`:**
1. Lê os TIFs mensais locais de cada variável (`chelsa_sa/`)
2. Calcula a média de cada mês ao longo dos 30 anos → array (12, H, W)
3. Salva como GeoTIFF multibanda (12 bandas) em `chelsa_normals/`

> Upload para o GEE é feito **manualmente** via Code Editor ou CLI.

**Assets no GEE** (caminho real confirmado — sem a subpasta `/CHELSA/` que constava aqui antes):
- `projects/fcoliveira/assets/CHELSA_pet_1991-2020` — confirmado, visualização funcionando
- `projects/fcoliveira/assets/CHELSA_pr_1991-2020` — confirmado, visualização funcionando
- `projects/fcoliveira/assets/CHELSA_tas_1991-2020` — **não confirmado**, nome assumido por convenção (ver nota abaixo)

**Notebook de visualização:** `abrindo_mapas.ipynb`
- Usa `earthengine-api` + `folium` + `matplotlib` para visualizar os assets direto do GEE (sem baixar nada)
- Para cada variável (`pet`, `pr`, `tas`): calcula uma escala de cores comum aos 12 meses (percentil 2-98 via `reduceRegion`), gera uma grade estática 4×3 (`matplotlib`, salva como `{var}_12_meses.png`) e um mapa interativo (`folium`, com `LayerControl` para ligar/desligar cada mês — navegável como no Code Editor do GEE)
- Lógica comum extraída em funções reutilizáveis: `carregar_variavel`, `escala_de_cores`, `grade_12_mapas`, `mapa_interativo`
- **Pendências conhecidas:**
  - Asset ID de `tas` (`CHELSA_tas_1991-2020`) não foi testado — confirmar nome real no GEE
  - Valores de `tas` podem estar sem a conversão de escala/offset do CHELSA (o pipeline `download_chelsa_sa.py` → `gerando_normal.ipynb` não aplica essa transformação); conferir antes de interpretar os mapas de temperatura

**Bibliotecas instaladas:**
| Lib | Versão |
|---|---|
| `earthengine-api` | 1.7.31 |
| `geemap` | 0.38.2 |
| `jupyterlab` | 4.6.0 |
| `matplotlib` | 3.11.0 |
| `folium` | 0.20.0 |
| `rasterio` | 1.5.0 |
| `pandas` | 3.0.3 |

---

## Progresso

- [x] Script de download criado (`download_chelsa_sa.py`)
- [x] Teste com 1 arquivo confirmado (8280×5760 px, ~83 MB por arquivo)
- [x] Primeira rodada com servidor antigo: 690/1080 arquivos (390 falhas — pet ausente + pr/tas cortados em 2019)
- [x] Servidor correto identificado (`os.unil.cloud.switch.ch`)
- [x] Arquivos do servidor antigo apagados (dados não confiáveis)
- [x] Bibliotecas GEE instaladas (earthengine-api, geemap, jupyterlab, matplotlib, folium)
- [x] Notebook `gerando_normal.ipynb` criado e simplificado (apenas geração de TIFs locais; upload manual)
- [x] **Download quase completo** — arquivos presentes em `chelsa_sa/`: `pr` 359/360, `pet` 340/360, `tas` 358/360 (alguns meses faltando)
- [x] **Normais climatológicas geradas** com sucesso em `chelsa_normals/`:
  - `CHELSA_pr_1991-2020.tif` (750.8 MB, 12 bandas)
  - `CHELSA_pet_1991-2020.tif` (725.9 MB, 12 bandas)
  - `CHELSA_tas_1991-2020.tif` (583.0 MB, 12 bandas)
- [x] **Upload dos assets para GEE** — `pet` e `pr` confirmados; `tas` pendente de confirmação
- [x] Notebook `abrindo_mapas.ipynb` criado: visualização dos 12 mapas mensais (grade estática + mapa interativo `folium`) para `pet`, `pr` e `tas`

---

## Arquivos Faltando no Download
| Variável | Encontrados | Faltando |
|---|---|---|
| `pr` | 359/360 | ~1 |
| `pet` | 340/360 | ~20 |
| `tas` | 358/360 | ~2 |

As normais foram calculadas com os anos disponíveis por mês (`nanmean` ignora ausentes); re-rodar o script de download preenche os gaps.

---

## Próximos Passos
1. Re-rodar `download_chelsa_sa.py` para preencher os arquivos faltantes (especialmente `pet`)
2. Após download completo, re-executar `gerando_normal.ipynb` para regenerar as normais com 30 anos completos
3. Confirmar o nome exato do asset de temperatura no GEE e corrigir `ASSET_TAS` em `abrindo_mapas.ipynb` se necessário
4. Verificar se os valores de `tas` precisam de conversão de escala/offset do CHELSA antes de interpretar os mapas de temperatura
