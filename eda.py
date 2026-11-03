import hashlib
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from PIL import Image


def eda_data_quality(df: pd.DataFrame) -> None:
    """Verifica dimensiones, tipos, nulos, duplicados y distribución por split y fuente."""
    print("=== 1. DIMENSIONES, TIPOS Y VALORES NULOS ===")
    print(f"Filas: {df.shape[0]} | Columnas: {df.shape[1]}\n")
    info_df = pd.DataFrame({"Tipo": df.dtypes, "Nulos": df.isna().sum()})
    print(info_df)

    print(f"\nDuplicados completos: {df.duplicated().sum()}")
    print(f"Duplicados en 'ruta_imagen': {df['ruta_imagen'].duplicated().sum()}")
    print(f"Extensiones: {df['extension'].value_counts().to_dict()}")
    print(f"Modos de imagen: {df['image_mode'].value_counts().to_dict()}")

    print("\n=== 2. DISTRIBUCIÓN GLOBAL DE LA CLASE OBJETIVO ===")
    conteo = df["es_sucio"].value_counts().sort_index()
    porcentaje = (df["es_sucio"].value_counts(normalize=True).sort_index() * 100).round(2)
    print(pd.DataFrame({"Cantidad": conteo, "Porcentaje (%)": porcentaje}))

    print("\n=== 3. DISTRIBUCIÓN POR SPLIT Y CLASE ===")
    tabla_splits = (
        df.groupby(["split", "es_sucio"])
        .size()
        .unstack(fill_value=0)
        .rename(columns={0: "Limpio (0)", 1: "Sucio (1)"})
    )
    tabla_splits["Total"] = tabla_splits.sum(axis=1)
    tabla_splits["% Sucio"] = (tabla_splits["Sucio (1)"] / tabla_splits["Total"] * 100).round(2)
    print(tabla_splits)

    print("\n=== 4. DISTRIBUCIÓN POR FUENTE ===")
    tabla_fuente = (
        df.groupby(["source", "es_sucio"])
        .size()
        .unstack(fill_value=0)
        .rename(columns={0: "Limpio (0)", 1: "Sucio (1)"})
    )
    print(tabla_fuente)


def eda_plot_distributions(df: pd.DataFrame) -> None:
    """Genera los gráficos de distribución de clases y dimensiones de imagen."""
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))

    sns.countplot(data=df, x="es_sucio", hue="es_sucio", palette="Set2", legend=False, ax=axes[0, 0])
    axes[0, 0].set_title("Distribución Global de 'es_sucio'")
    axes[0, 0].set_xticks([0, 1])
    axes[0, 0].set_xticklabels(["Limpio (0)", "Sucio (1)"])

    sns.countplot(data=df, x="split", hue="es_sucio", palette="Set2", ax=axes[0, 1])
    axes[0, 1].set_title("Distribución de Clases por Split")

    sns.scatterplot(
        data=df,
        x="width",
        y="height",
        hue="es_sucio",
        style="source",
        palette="Set2",
        alpha=0.7,
        ax=axes[0, 2],
    )
    axes[0, 2].set_title("Mapa de Resoluciones (Width vs Height)")

    sns.histplot(df["width"], bins=30, kde=True, color="steelblue", ax=axes[1, 0])
    axes[1, 0].set_title("Distribución de Width (px)")

    sns.histplot(df["height"], bins=30, kde=True, color="darkorange", ax=axes[1, 1])
    axes[1, 1].set_title("Distribución de Height (px)")

    sns.histplot(df["aspect_ratio"], bins=30, kde=True, color="forestgreen", ax=axes[1, 2])
    axes[1, 2].set_title("Distribución de Aspect Ratio (W/H)")

    plt.tight_layout()
    plt.show()


def eda_outliers_and_correlations(df: pd.DataFrame) -> pd.DataFrame:
    """Analiza outliers con el criterio IQR y muestra boxplots y matriz de correlación."""
    numeric_cols = ["width", "height", "aspect_ratio", "n_pixels"]
    outlier_rows = []

    for col in numeric_cols:
        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        n_outliers = ((df[col] < lower) | (df[col] > upper)).sum()
        outlier_rows.append(
            {
                "Variable": col,
                "Min": df[col].min(),
                "Q1": q1,
                "Mediana": df[col].median(),
                "Q3": q3,
                "Max": df[col].max(),
                "Outliers_IQR": n_outliers,
                "%_Outliers": round(n_outliers / len(df) * 100, 2),
            }
        )

    report_df = pd.DataFrame(outlier_rows)
    print("=== ESTADÍSTICOS DE TAMAÑO Y OUTLIERS (IQR) ===")
    print(report_df.to_string(index=False))

    fig, axes = plt.subplots(1, 4, figsize=(20, 5))
    for ax, col in zip(axes[:3], ["width", "height", "aspect_ratio"]):
        sns.boxplot(data=df, x="es_sucio", y=col, hue="es_sucio", palette="Set2", legend=False, ax=ax)
        ax.set_title(f"{col} por clase")

    corr = df[["es_sucio", "width", "height", "aspect_ratio", "n_pixels"]].corr()
    sns.heatmap(corr, annot=True, cmap="coolwarm", fmt=".2f", vmin=-1, vmax=1, ax=axes[3])
    axes[3].set_title("Correlación Metadatos vs Target")

    plt.tight_layout()
    plt.show()
    return report_df


def eda_plot_sample_images(df: pd.DataFrame, root_dir: str | Path = ".", n_per_class: int = 4) -> None:
    """Visualiza una muestra de imágenes limpias y sucias cargándolas desde rutas relativas."""
    root = Path(root_dir).resolve()
    fig, axes = plt.subplots(2, n_per_class, figsize=(4 * n_per_class, 7))

    for row_idx, (label, clase_str) in enumerate([(0, "Limpio"), (1, "Sucio")]):
        subset = df[df["es_sucio"] == label].sample(n=n_per_class, random_state=42)
        for col_idx, (_, fila) in enumerate(subset.iterrows()):
            img_path = root / fila["ruta_imagen"]
            with Image.open(img_path) as img:
                axes[row_idx, col_idx].imshow(img.convert("RGB"))
            axes[row_idx, col_idx].set_title(
                f"{clase_str} ({fila['split']})\n{fila['width']}x{fila['height']}px",
                fontsize=10,
            )
            axes[row_idx, col_idx].axis("off")

    plt.suptitle("Muestra Visual de Placas Solares (Limpio vs Sucio)", fontsize=14, y=1.02)
    plt.tight_layout()
    plt.show()


def check_duplicate_images(df: pd.DataFrame, root_dir: str | Path = ".") -> None:
    """Detecta duplicados por fila y por contenido exacto del archivo (hash MD5)."""
    root = Path(root_dir).resolve()

    dup_filas = df.duplicated().sum()
    dup_rutas = df["ruta_imagen"].duplicated().sum()
    hashes = df["ruta_imagen"].apply(lambda rel_path: hashlib.md5((root / rel_path).read_bytes()).hexdigest())
    dup_contenido = hashes.duplicated().sum()

    print(f"Duplicados de fila en DataFrame: {dup_filas}")
    print(f"Duplicados en 'ruta_imagen':     {dup_rutas}")
    print(f"Imágenes idénticas (Hash MD5):   {dup_contenido}")

    if dup_contenido > 0:
        print("\nArchivos con contenido duplicado:")
        print(df[hashes.duplicated(keep=False)].sort_values(by="n_pixels"))


__all__ = [
    "eda_data_quality",
    "eda_plot_distributions",
    "eda_outliers_and_correlations",
    "eda_plot_sample_images",
    "check_duplicate_images",
]
