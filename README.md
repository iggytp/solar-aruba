# Solar Aruba

Proyecto para detectar suciedad en paneles solares a partir de imágenes. El objetivo es clasificar si una imagen de panel fotovoltaico se encuentra limpia o sucia, usando aprendizaje automático y procesamiento de imágenes.

## Descripción del proyecto

Este repositorio reúne las piezas principales para:

- preparar y explorar un dataset de paneles solares,
- construir un DataFrame con rutas, etiquetas y metadatos de las imágenes,
- generar cargadores de datos para entrenar un modelo,
- complementar el dataset con imágenes adicionales descargadas desde fuentes públicas,
- analizar la distribución de imágenes y la calidad del conjunto.

La lógica principal del pipeline está en los siguientes archivos:

- `solar_dataset.py`: genera el DataFrame desde el dataset y extrae metadatos de cada imagen.
- `preprocessing.py`: define el `Dataset` de PyTorch y los `DataLoader` para entrenamiento y validación.
- `pixabay_scraper.py`: descarga imágenes adicionales de paneles solares desde Pixabay.
- `EDA_Solar_Aruba.ipynb`: notebook de exploración y análisis inicial.

## Estructura del repositorio

```text
solar-aruba/
├── README.md
├── EDA_Solar_Aruba.ipynb
├── eda.py
├── preprocessing.py
├── solar_dataset.py
├── pixabay_scraper.py
├── PVSDL_DATASET/        # dataset principal (descargar por separado)
├── solar_panel_images/   # imágenes extra descargadas desde Pixabay
├── data/
├── aruba_cruzado_5min_con_energia.csv
├── aruba_stations.json
└── LICENSE
```

## Fuente de datos

### 1) Dataset principal: PVSL Dataset

Las imágenes principales del proyecto provienen del dataset PVSL (PV Soiling / solar panel soiling dataset). Es un conjunto de imágenes de paneles solares con etiquetas que permiten diferenciar entre paneles limpios y paneles sucios.

Este tipo de dataset suele publicarse en Hugging Face, y la forma más directa de descargar las imágenes es usando la librería `datasets` o `huggingface_hub`.

Ejemplo de descarga directa desde Hugging Face:

```bash
pip install datasets huggingface_hub
```

```bash
python - <<'PY'
from huggingface_hub import snapshot_download

# Sustituir por el identificador real del dataset PVSL en Hugging Face
repo_id = "<asdmd/PVSDL_DATASET>"

snapshot_download(
    repo_id=repo_id,
    repo_type="dataset",
    local_dir="./PVSDL_DATASET",
)
PY
```

También se puede usar `datasets.load_dataset(...)` si el dataset está publicado como dataset compatible con la librería `datasets`:

```python
from datasets import load_dataset

ds = load_dataset("<ID_DEL_DATASET_PVSL>")
print(ds)
```

> Importante: el proyecto espera una estructura tipo `PVSDL_DATASET/train`, `PVSDL_DATASET/val` y `PVSDL_DATASET/test` para que `solar_dataset.py` pueda construir el DataFrame correctamente.

### 2) Imágenes complementarias

Además del dataset principal, el repositorio incluye la opción de descargar imágenes adicionales de paneles solares desde Pixabay para enriquecer el conjunto. El script `pixabay_scraper.py` hace esta descarga automáticamente.

```bash
python pixabay_scraper.py
```

Esto crea la carpeta `solar_panel_images/` y guarda archivos adicionales que luego pueden añadirse al conjunto de entrenamiento.

## Requisitos

Se requiere Python 3.10+ y las librerías siguientes:

```bash
pip install numpy pandas pillow torch scikit-learn matplotlib
```

En caso de usar Hugging Face para la descarga directa del dataset, también será necesario instalar:

```bash
pip install datasets huggingface_hub
```

## Cómo ejecutar el proyecto

1. Clona el repositorio.
2. Descarga el dataset PVSL desde Hugging Face y colócalo en la carpeta `PVSDL_DATASET/`.
3. Si quieres, descarga más imágenes complementarias:

```bash
python pixabay_scraper.py
```

4. Genera el DataFrame con rutas y metadatos:

```bash
python - <<'PY'
from solar_dataset import build_solar_dataframe

build_solar_dataframe(root_dir=".")
PY
```

5. Usa `preprocessing.py` para crear los `DataLoader` del modelo.

## Notas importantes

- El dataset no se incluye en este repositorio por tamaño o licencias de distribución.
- La estructura de carpetas es importante para que el código funcione correctamente.
- El script `solar_dataset.py` identifica las etiquetas según el sufijo del nombre del archivo. Por ejemplo, nombres con `_0` se interpretan como "limpio" y `_1` como "sucio".

## Licencia

Este proyecto se distribuye con la licencia que aparece en `LICENSE`.

## Créditos

- Dataset PVSL: obtenido desde Hugging Face, según la publicación del conjunto de imágenes de paneles solares.
- Imágenes complementarias: descargadas desde Pixabay mediante `pixabay_scraper.py`.
