from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


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
    root_dir: str | Path = ".",
    dataset_rel_dir: str = "PVSDL_DATASET",
    extra_rel_dir: str = "solar_panel_images",
    output_rel_path: str = "data/pvsoiling_dataframe.pkl",
) -> pd.DataFrame:
    """Construye y guarda el DataFrame con rutas relativas y metadatos."""
    root = Path(root_dir).resolve()
    dataset_dir = root / dataset_rel_dir
    extra_dir = root / extra_rel_dir
    output_path = root / output_rel_path

    rows = []

    for split in ["train", "val", "test"]:
        split_dir = dataset_dir / split
        if not split_dir.exists():
            continue

        for img_path in sorted(split_dir.iterdir()):
            if not img_path.is_file() or img_path.suffix.lower() not in VALID_EXTENSIONS:
                continue

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

    if extra_dir.exists():
        for img_path in sorted(extra_dir.iterdir()):
            if not img_path.is_file() or img_path.suffix.lower() not in VALID_EXTENSIONS:
                continue

            rel_path = img_path.relative_to(root).as_posix()
            meta = extract_image_metadata(img_path)

            rows.append(
                {
                    "split": "train",
                    "ruta_imagen": rel_path,
                    "filename": img_path.name,
                    "extension": img_path.suffix.lower(),
                    "source": "extra_clean",
                    "es_sucio": 0,
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
