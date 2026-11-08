# Solar Aruba

Proyecto para detectar suciedad en placas solares a partir de imágenes. El objetivo es clasificar si una imagen de panel fotovoltaico está limpia o sucia usando aprendizaje automático, análisis de datos y preprocesamiento de imágenes. Además, realizar predicciones a futuro sobre el consumo/generación eléctrica a partir de los registros meteorológicos y el histórico reciente de consumo

## Qué contienen los datos

- Meteorología del archivo original del equipo y catálogo de estaciones de Aruba.
- Segunda fuente: [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api), para radiación y nubosidad horarias. La integración usa estación e instante UTC; la radiación se repite dentro de cada hora. Son valores del recurso solar procedentes de una API histórica, sin acreditar medición directa en una planta.
- Rama visual independiente: [asdmd/PVSDL_DATASET](https://huggingface.co/datasets/asdmd/PVSDL_DATASET), versión `adb5be58b27d58f3631496df187817380b0b75de`. El inventario contiene 1.700 imágenes; la fuente documenta 0 limpia y 1 sucia en el nombre. No existen claves verificadas para unir esas fotos con las estaciones o fechas de Aruba.

La energía es un escenario calculado con 7,5 MW nominales y factor de suciedad 1, no generación real. Los parámetros y las fórmulas están documentados. UV presenta una discrepancia entre su perfil horario y el solar: se conserva como dato de referencia y se excluye de los predictores.

## Descripción del proyecto

Este repositorio permite:

- preparar y explorar un dataset de placas solares,
- construir un DataFrame con rutas relativas, etiquetas y metadatos,
- generar loaders para entrenamiento con PyTorch,
- complementar el dataset con imágenes extra descargadas desde fuentes públicas,
- analizar la calidad del conjunto y visualizar la distribución de imágenes.

La lógica principal está repartida en:

- [src/solar_dataset.py](src/solar_dataset.py): genera el DataFrame y extrae metadatos de cada imagen.
- [src/preprocessing.py](src/preprocessing.py): define el `Dataset` de PyTorch y los `DataLoader`.
- [src/pixabay_scraper.py](src/pixabay_scraper.py): descarga imágenes extra desde Pixabay.
- [notebooks/EDA_Solar_Aruba.ipynb](notebooks/EDA_Solar_Aruba.ipynb): análisis exploratorio inicial.
- [notebooks/etl_eda_preprocesamiento_imagenes.ipynb](notebooks/etl_eda_preprocesamiento_imagenes.ipynb): pipeline completo de ETL + EDA + preprocesamiento.

## Estructura del repositorio

```text
solar-aruba/
├── README.md
├── requirements.txt
├── .gitignore
├── .venv/                     
├── src/
│   ├── eda.py
│   ├── extraccion_radiacion_aruba.py
│   ├── generar_csv_con_energia.py
│   ├── pixabay_scraper.py
│   ├── preprocessing.py
│   ├── solar_dataset.py
│   └── __init__.py
├── notebooks/
│   ├── EDA_Solar_Aruba.ipynb
│   └── etl_eda_preprocesamiento_imagenes.ipynb
├── data/
│   ├── aruba_cruzado_5min_con_energia.csv
│   ├── aruba_solar_radiation.csv
│   ├── aruba_stations.json
│   └── pvsoiling_dataframe.pkl
├── solar_panel_images/
│   ├── PVSDL_DATASET/         # dataset principal del proyecto
│   │   ├── train/
│   │   ├── val/
│   │   └── test/
│   └── scraped/               # imágenes extra descargadas por el scraper
├── LICENSE
└── .DS_Store
```

> Todas las imágenes se gestionan dentro de `solar_panel_images/`, separadas en `PVSDL_DATASET/` para el dataset principal y `scraped/` para las imágenes descargadas.

## Requisitos del sistema

- Python 3.10+
- `pip`
- Un entorno virtual `.venv`
- Opcional: navegador Chrome/Chromium si quieres ejecutar el scraper de Pixabay

## 1) Crear el entorno virtual

Desde la raíz del proyecto:

```bash
cd /ruta/al/proyecto/solar-aruba
python3 -m venv .venv
source .venv/bin/activate
```

En Windows PowerShell:

```powershell
cd C:\ruta\al\proyecto\solar-aruba
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## 2) Instalar dependencias

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

El fichero [requirements.txt](requirements.txt) incluye las librerías necesarias para:

- carga y análisis de datos,
- visualización,
- modelos con PyTorch,
- scraping con Selenium,
- descarga de datasets desde Hugging Face.

## 3) Descargar el dataset principal dentro de `solar_panel_images`

El dataset principal del proyecto debe descargarse dentro de la carpeta `solar_panel_images` con este nombre exacto:

```text
solar_panel_images/PVSDL_DATASET/
```

La estructura esperada es:

```text
solar_panel_images/PVSDL_DATASET/
├── train/
├── val/
├── test/
```

Una forma sencilla es usar `huggingface_hub`:

```bash
python - <<'PY'
from huggingface_hub import snapshot_download

repo_id = "asdmd/PVSDL_DATASET"
snapshot_download(
    repo_id=repo_id,
    repo_type="dataset",
    local_dir="./solar_panel_images/PVSDL_DATASET",
)
PY
```

También puedes usar `datasets` si el dataset está publicado con ese formato:

```python
from datasets import load_dataset

ds = load_dataset("asdmd/PVSDL_DATASET")
print(ds)
```

> Importante: no lo pongas dentro de `data/`; el código espera que esté en la raíz del proyecto como `PVSDL_DATASET/`.

## 4) Ejecutar el proyecto

### A. Generar el DataFrame de imágenes

```bash
python - <<'PY'
from src.solar_dataset import build_solar_dataframe

build_solar_dataframe(root_dir=".")
PY
```

Esto crea el archivo:

```text
data/pvsoiling_dataframe.pkl
```


### B. Ejecutar notebooks

Abre los cuadernos desde la carpeta `notebooks/` y ejecuta las celdas en orden:

- [notebooks/etl_eda_preprocesamiento_imagenes.ipynb](notebooks/etl_eda_preprocesamiento_imagenes.ipynb)
- [notebooks/EDA_Solar_Aruba.ipynb](notebooks/EDA_Solar_Aruba.ipynb)

## 5) Scraper de imágenes extra

El scraper opcional de Pixabay descarga imágenes adicionales para enriquecer el conjunto. Requiere navegador Chrome/Chromium y las dependencias instaladas desde `requirements.txt`.

```bash
python - <<'PY'
from src.pixabay_scraper import scrape_extra_solar_images

scrape_extra_solar_images(output_dir="./solar_panel_images/scraped", max_images=20, scrolls=4)
PY
```

Si tu navegador y el driver no coinciden, la celda del notebook puede fallar con un error de ChromeDriver. Ese fallo es externo al proyecto y no bloquea el resto del pipeline.

## 6) Datos meteorológicos y energía

También hay scripts para descargar y transformar datos meteorológicos/energéticos de Aruba:

```bash
python src/extraccion_radiacion_aruba.py
python src/generar_csv_con_energia.py
```

Los CSVs resultantes se guardan en la carpeta `data/`.

## Notas importantes

- El dataset principal no se incluye en el repositorio por tamaño y licencias de distribución.
- La estructura del proyecto es importante para que el código encuentre archivos correctamente.
- La lógica de etiquetas usa el sufijo del nombre del archivo: por ejemplo, `_0` se interpreta como limpio y `_1` como sucio.
- Se recomienda usar siempre un entorno virtual `.venv` en lugar de depender de un entorno Conda.

## Licencia

Este proyecto se distribuye con la licencia que aparece en [LICENSE](LICENSE).

## Créditos

- Dataset PVSL: obtenido desde Hugging Face, según la publicación del conjunto de imágenes de paneles solares.
- Imágenes complementarias: descargadas desde Pixabay mediante [src/pixabay_scraper.py](src/pixabay_scraper.py).
