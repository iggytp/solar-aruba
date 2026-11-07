from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def _candidate_dataset_names(dataset_rel_dir: str) -> set[str]:
    """Soporta tanto PVSDL_DATASET como PVSL_DATASET y ubicaciones dentro de solar_panel_images."""
    names = {dataset_rel_dir}
    lower = dataset_rel_dir.lower()
    if "pvsl" in lower:
        names.add(dataset_rel_dir.replace("PVSL", "PVSDL"))
        names.add(dataset_rel_dir.replace("PVSL", "PVSDL_"))
    if "pvdl" in lower:
        names.add(dataset_rel_dir.replace("PVSDL", "PVSL"))
        names.add(dataset_rel_dir.replace("PVSDL", "PVSL_"))
    names.update({"PVSDL_DATASET", "PVSL_DATASET"})
    return {name for name in names if name}


def _iter_valid_images(folder: Path):
    if not folder.exists():
        return []

    files = []
    for path in sorted(folder.iterdir()):
        if path.is_dir():
            files.extend(_iter_valid_images(path))
        elif path.is_file() and path.suffix.lower() in VALID_EXTENSIONS:
            files.append(path)
    return files


def parse_label_from_filename(path: Path) -> int:
    """Devuelve 0 para limpia y 1 para sucia según el sufijo del nombre del archivo."""
    suffix = path.stem.lower().rsplit("_", 1)[-1]
    return int(suffix) if suffix in {"0", "1"} else 0


def extract_image_metadata(image_path: Path) -> dict:
    """Extrae dimensiones y modo leyendo solo la cabecera del archivo (sin cargar píxeles en RAM)."""
    try:
        with Image.open(image_path) as img:
            w, h = img.size
            mode = img.mode
        return {
            "width": w,
            "height": h,
            "aspect_ratio": round(w / h, 4) if h > 0 else np.nan,
            "n_pixels": w * h,
            "image_mode": mode,
            "is_corrupted": False,
        }
    except Exception:
        return {
            "width": np.nan,
            "height": np.nan,
            "aspect_ratio": np.nan,
            "n_pixels": np.nan,
            "image_mode": "unknown",
            "is_corrupted": True,
        }


def build_solar_dataframe(
    root_dir: str | Path = PROJECT_ROOT,
    dataset_rel_dir: str = "solar_panel_images/PVSDL_DATASET",
    extra_rel_dir: str = "solar_panel_images/scraped",
    output_rel_path: str = "data/pvsoiling_dataframe.pkl",
) -> pd.DataFrame:
    """Construye y guarda el DataFrame con rutas relativas y metadatos."""
    root = Path(root_dir).resolve()
    extra_dir = root / extra_rel_dir

    dataset_dirs = [
        root / name for name in _candidate_dataset_names(dataset_rel_dir)
    ] + [
        root / extra_rel_dir / name for name in _candidate_dataset_names(dataset_rel_dir)
    ]
    dataset_dirs = [p for p in dict.fromkeys(dataset_dirs)]
    dataset_dir = next((p for p in dataset_dirs if p.exists()), root / dataset_rel_dir)
    output_path = root / output_rel_path

    rows = []

    for split in ["train", "val", "test"]:
        split_dir = dataset_dir / split
        if not split_dir.exists():
            continue

        for img_path in _iter_valid_images(split_dir):
            rel_path = img_path.relative_to(root).as_posix()
            meta = extract_image_metadata(img_path)

            rows.append(
                {
                    "split": split,
                    "ruta_imagen": rel_path,
                    "filename": img_path.name,
                    "extension": img_path.suffix.lower(),
                    "source": "pvdl_dataset",
                    "es_sucio": parse_label_from_filename(img_path),
                    **meta,
                }
            )

    if extra_dir.exists() and dataset_dir != extra_dir:
        excluded_prefix = dataset_dir.relative_to(root).as_posix()
        for img_path in _iter_valid_images(extra_dir):
            rel_path = img_path.relative_to(root).as_posix()
            rel_prefix = img_path.relative_to(root).parent.as_posix()
            if rel_path.startswith(excluded_prefix + "/") or rel_path == excluded_prefix:
                continue
            if rel_prefix == extra_rel_dir:
                source = "extra_clean"
                split = "train"
                es_sucio = 0
            else:
                source = "extra_clean"
                split = "train"
                es_sucio = 0
            meta = extract_image_metadata(img_path)

            rows.append(
                {
                    "split": split,
                    "ruta_imagen": rel_path,
                    "filename": img_path.name,
                    "extension": img_path.suffix.lower(),
                    "source": source,
                    "es_sucio": es_sucio,
                    **meta,
                }
            )

    df = pd.DataFrame(rows)

    if df["is_corrupted"].any():
        n_corrupt = df["is_corrupted"].sum()
        print(f"Advertencia: Se descartaron {n_corrupt} imágenes corruptas.")
        df = df[~df["is_corrupted"]].reset_index(drop=True)
    df = df.drop(columns=["is_corrupted"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_pickle(output_path)
    print(f"DataFrame creado y guardado en '{output_rel_path}' con {len(df)} filas.")
    return df


__all__ = ["parse_label_from_filename", "extract_image_metadata", "build_solar_dataframe"]
