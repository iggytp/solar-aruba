from pathlib import Path
import random

import numpy as np
import pandas as pd
import torch
from PIL import Image, ImageEnhance
from sklearn.utils.class_weight import compute_class_weight
from torch.utils.data import DataLoader, Dataset


def transform_image(
    img: Image.Image,
    is_train: bool = True,
    image_size: tuple[int, int] = (224, 224),
) -> torch.Tensor:
    """Aplica redimensionado, augmentación y normalización a una imagen."""
    img = img.resize(image_size, Image.Resampling.BILINEAR)

    if is_train:
        if random.random() > 0.5:
            img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if random.random() > 0.8:
            img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

        angle = random.uniform(-15, 15)
        img = img.rotate(angle, resample=Image.Resampling.BILINEAR)
        img = ImageEnhance.Brightness(img).enhance(random.uniform(0.9, 1.1))
        img = ImageEnhance.Contrast(img).enhance(random.uniform(0.9, 1.1))

    arr = np.asarray(img, dtype=np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    arr = (arr - mean) / std

    tensor = torch.from_numpy(arr).permute(2, 0, 1).contiguous()
    return tensor


class SolarImageDataset(Dataset):
    """Dataset que carga imágenes desde rutas relativas y devuelve tensor + etiqueta."""

    def __init__(
        self,
        df_split: pd.DataFrame,
        root_dir: str | Path = ".",
        is_train: bool = False,
        image_size: tuple[int, int] = (224, 224),
    ):
        self.df = df_split.reset_index(drop=True)
        self.root = Path(root_dir).resolve()
        self.is_train = is_train
        self.image_size = image_size

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        rel_path = self.df.loc[idx, "ruta_imagen"]
        label = int(self.df.loc[idx, "es_sucio"])

        full_path = self.root / rel_path
        with Image.open(full_path) as img:
            image = img.convert("RGB")
            tensor_img = transform_image(image, is_train=self.is_train, image_size=self.image_size)

        return tensor_img, torch.tensor(label, dtype=torch.long)


def build_dataloaders(
    df: pd.DataFrame,
    root_dir: str | Path = ".",
    image_size: tuple[int, int] = (224, 224),
    batch_size: int = 32,
    num_workers: int = 0,
) -> dict:
    """Construye DataLoaders para train, validation y test."""
    df_train = df[df["split"] == "train"]
    df_val = df[df["split"] == "val"]
    df_test = df[df["split"] == "test"]

    train_ds = SolarImageDataset(df_train, root_dir=root_dir, is_train=True, image_size=image_size)
    val_ds = SolarImageDataset(df_val, root_dir=root_dir, is_train=False, image_size=image_size)
    test_ds = SolarImageDataset(df_test, root_dir=root_dir, is_train=False, image_size=image_size)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=num_workers)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers)

    y_train = df_train["es_sucio"].to_numpy()
    weights = compute_class_weight(class_weight="balanced", classes=np.array([0, 1]), y=y_train)
    class_weights_tensor = torch.tensor(weights, dtype=torch.float32)

    print(f"=== DATALOADERS LISTOS (Resolución: {image_size}, Batch: {batch_size}) ===")
    print(f" - Train: {len(train_ds)} muestras ({len(train_loader)} batches)")
    print(f" - Val:   {len(val_ds)} muestras ({len(val_loader)} batches)")
    print(f" - Test:  {len(test_ds)} muestras ({len(test_loader)} batches)")

    return {
        "train_loader": train_loader,
        "val_loader": val_loader,
        "test_loader": test_loader,
        "class_weights": class_weights_tensor,
    }


def denormalize_image(tensor: torch.Tensor) -> np.ndarray:
    """Deshace la normalización para visualizar la imagen con Matplotlib."""
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)

    img = tensor.permute(1, 2, 0).numpy()
    img = std * img + mean
    return np.clip(img, 0, 1)


__all__ = [
    "transform_image",
    "SolarImageDataset",
    "build_dataloaders",
    "denormalize_image",
]
