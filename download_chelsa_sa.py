"""
Download CHELSA V2.1 monthly data clipped to South America bounding box.
Uses rasterio windowed read via HTTPS (GDAL vsicurl) — no global download.
"""

import sys
import os
import time
import traceback

# ---------------------------------------------------------------------------
# Dependency check
# ---------------------------------------------------------------------------
def check_deps():
    try:
        import rasterio
    except ImportError:
        print("Dependência faltando: rasterio")
        print("Instale com:  pip install rasterio  ou  conda install -c conda-forge rasterio")
        sys.exit(1)

check_deps()

import rasterio
from rasterio.windows import from_bounds

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
VARIABLES = ["pr", "pet", "tas"]
YEARS     = range(1991, 2021)   # 1991–2020
MONTHS    = range(1, 13)        # 01–12

# South America bounding box (WGS84)
XMIN, YMIN, XMAX, YMAX = -82, -56, -34, 13

BASE_URL = (
    "https://os.unil.cloud.switch.ch/chelsa02/chelsa/global/monthly"
    "/{var}/{yyyy}/CHELSA_{var}_{mm:02d}_{yyyy}_V.2.1.tif"
)

OUT_ROOT    = "chelsa_sa"
MAX_RETRY   = 3
RETRY_DELAY = 10  # seconds between retries

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def remote_url(var, mm, yyyy):
    # rasterio 1.3+ opens HTTPS URLs directly; GDAL handles vsicurl internally
    return BASE_URL.format(var=var, mm=mm, yyyy=yyyy)


def out_path(var, mm, yyyy):
    return os.path.join(OUT_ROOT, var, f"CHELSA_{var}_{mm:02d}_{yyyy}_SA.tif")


def setup_dirs():
    for var in VARIABLES:
        os.makedirs(os.path.join(OUT_ROOT, var), exist_ok=True)


def clip_and_save(url, dst_path):
    """Read bounding-box window from remote COG; write as COG GeoTIFF."""
    env = rasterio.Env(
        GDAL_HTTP_UNSAFESSL=False,
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
        GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES",
        GDAL_HTTP_MULTIPLEX="YES",
        GDAL_HTTP_VERSION=2,
    )
    with env:
        with rasterio.open(url) as src:
            window  = from_bounds(XMIN, YMIN, XMAX, YMAX, src.transform)
            data    = src.read(window=window)
            win_tf  = src.window_transform(window)
            profile = src.profile.copy()

        profile.update(
            driver="GTiff",
            height=data.shape[1],
            width=data.shape[2],
            transform=win_tf,
            compress="deflate",
            tiled=True,
            blockxsize=512,
            blockysize=512,
            interleave="band",
            bigtiff="IF_SAFER",
        )

        with rasterio.open(dst_path, "w", **profile) as dst:
            dst.write(data)

    size_kb = os.path.getsize(dst_path) / 1024
    return data.shape, size_kb


# ---------------------------------------------------------------------------
# Single-file download with retry
# ---------------------------------------------------------------------------
def download_one(var, mm, yyyy, index, total):
    url  = remote_url(var, mm, yyyy)
    path = out_path(var, mm, yyyy)

    if os.path.exists(path):
        print(f"  [skip] {os.path.basename(path)} já existe")
        return "skip"

    label = f"{var} {mm:02d}/{yyyy}"
    print(f"Baixando {label}... [{index}/{total}]", end="", flush=True)

    for attempt in range(1, MAX_RETRY + 1):
        try:
            shape, size_kb = clip_and_save(url, path)
            print(f"  OK  {shape[1]}x{shape[2]}px  {size_kb:.0f} KB")
            return "ok"
        except Exception as exc:
            if attempt < MAX_RETRY:
                print(f"\n  tentativa {attempt} falhou ({exc}), aguardando {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
            else:
                print(f"\n  FALHA definitiva: {exc}")
                return url   # caller records the failed URL


# ---------------------------------------------------------------------------
# Test run — single file
# ---------------------------------------------------------------------------
def run_test():
    print("=" * 60)
    print("TESTE: CHELSA_pr_01_1991_V.2.1.tif")
    print("=" * 60)
    setup_dirs()

    test_path = out_path("pr", 1, 1991)
    if os.path.exists(test_path):
        os.remove(test_path)

    url = remote_url("pr", 1, 1991)
    print(f"URL: {url}\n")
    try:
        shape, size_kb = clip_and_save(url, test_path)
        print(f"Resultado:")
        print(f"  Arquivo  : {test_path}")
        print(f"  Dimensões: {shape[1]} linhas x {shape[2]} colunas")
        print(f"  Bandas   : {shape[0]}")
        print(f"  Tamanho  : {size_kb:.1f} KB  ({size_kb/1024:.2f} MB)")
        print("\nTeste bem-sucedido!")
        return True
    except Exception:
        print("\nTeste FALHOU — traceback completo:")
        traceback.print_exc()
        return False


# ---------------------------------------------------------------------------
# Full run — 1080 files
# ---------------------------------------------------------------------------
def run_all():
    setup_dirs()
    tasks    = [(var, mm, yyyy) for var in VARIABLES for yyyy in YEARS for mm in MONTHS]
    total    = len(tasks)
    failures = []
    success  = 0
    skipped  = 0

    for i, (var, mm, yyyy) in enumerate(tasks, start=1):
        result = download_one(var, mm, yyyy, i, total)
        if result == "ok":
            success += 1
        elif result == "skip":
            skipped += 1
        else:
            failures.append(result)

    print("\n" + "=" * 60)
    print(f"Concluído: {success} baixados, {skipped} pulados, {len(failures)} falhas")
    if failures:
        with open("falhas.txt", "w") as f:
            f.write("\n".join(failures))
        print("URLs com falha salvas em: falhas.txt")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download CHELSA V2.1 recortado para a América do Sul")
    parser.add_argument(
        "--all", action="store_true",
        help="Roda o download completo (1080 arquivos). Sem este flag só faz o teste.",
    )
    args = parser.parse_args()

    if args.all:
        ok = run_test()
        if not ok:
            print("\nAbortando — corrija o erro acima antes de rodar --all.")
            sys.exit(1)
        print("\nIniciando download completo...\n")
        run_all()
    else:
        ok = run_test()
        if ok:
            print("\nPara baixar todos os 1080 arquivos, rode:")
            print("  python download_chelsa_sa.py --all")
