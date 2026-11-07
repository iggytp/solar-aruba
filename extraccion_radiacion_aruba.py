import json
import os
import time
import pandas as pd
import requests

# 1. Configuración de parámetros y fechas (ajustadas al dataset de Aruba)
START_DATE = "2025-09-01"
END_DATE = "2026-09-18"
STATIONS_FILE = "aruba_stations.json"  # Ruta a vuestro archivo de estaciones
OUTPUT_CSV = "data/aruba_solar_radiation.csv"

# Endpoint del archivo histórico de radiación solar de Open-Meteo
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Variables solares horarias a extraer (W/m² y factores fotovoltaicos)
HOURLY_VARIABLES = [
    "shortwave_radiation_instant",  # Radiación solar total incidente (GHI) en W/m²
    "direct_normal_irradiance_instant",  # Radiación solar directa (DNI) en W/m²
    "diffuse_radiation_instant",  # Radiación difusa en W/m²
    "direct_radiation_instant",  # Radiación solar directa horizontal en W/m²
    "cloud_cover",  # Cobertura total de nubes (%)
    "is_day",  # Indicador día/noche (1/0)
    "sunshine_duration",  # Segundos de sol en la hora
]


def load_stations(filepath: str):
  """Carga las estaciones meteorológicas con sus coordenadas."""
  if not os.path.exists(filepath):
    # Estaciones por defecto si el archivo no está en la raíz
    return [
        {
            "id": "de2ee07b-de63-49db-a669-64177a688bbf",
            "name": "Queen Beatrix Airport",
            "latitude": 12.5042,
            "longitude": -70.0031,
        },
        {
            "id": "963fdb57-b257-472d-b56e-892b265c2524",
            "name": "San Nicolaas",
            "latitude": 12.4364,
            "longitude": -69.909,
        },
    ]

  with open(filepath, "r", encoding="utf-8") as f:
    return json.load(f)


def fetch_station_solar_data(station: dict, start_date: str, end_date: str):
  """Descarga la serie horaria de radiación solar para una estación concreta."""
  params = {
      "latitude": station["latitude"],
      "longitude": station["longitude"],
      "start_date": start_date,
      "end_date": end_date,
      "hourly": ",".join(HOURLY_VARIABLES),
      "timezone": "UTC",  # Formato UTC coherente con aruba_lecturas.json
  }

  print(
      f"Descargando radiación solar para: {station['name']} "
      f"({station['latitude']}, {station['longitude']})..."
  )

  response = requests.get(OPEN_METEO_ARCHIVE_URL, params=params, timeout=20)

  if response.status_code != 200:
    print(f"Error {response.status_code} al consultar {station['name']}")
    return None

  data = response.json()
  hourly = data.get("hourly", {})

  if not hourly or "time" not in hourly:
    print(f"Respuesta vacía para {station['name']}")
    return None

  # Construir DataFrame tabular
  df_station = pd.DataFrame(hourly)

  # Convertir fecha a formato ISO 8601 UTC idéntico a aruba_lecturas.json
  df_station["timestamp"] = (
      pd.to_datetime(df_station["time"]).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
  )
  df_station.drop(columns=["time"], inplace=True)

  # Añadir identificadores de la estación
  df_station["station_id"] = station["id"]
  df_station["station_name"] = station["name"]

  return df_station


def main():
  os.makedirs("data", exist_ok=True)
  stations = load_stations(STATIONS_FILE)

  all_records = []

  for station in stations:
    df_st = fetch_station_solar_data(station, START_DATE, END_DATE)
    if df_st is not None and not df_st.empty:
      all_records.append(df_st)
    time.sleep(0.5)  # Pausa de cortesía para respetar el rate limit de la API

  if all_records:
    df_final = pd.concat(all_records, ignore_index=True)

    # Reordenar columnas poniendo los identificadores primero
    cols_order = [
        "station_id",
        "station_name",
        "timestamp",
        "shortwave_radiation_instant",
        "direct_normal_irradiance_instant",
        "diffuse_radiation_instant",
        "cloud_cover",
        "is_day",
    ]
    df_final = df_final[
        cols_order
        + [c for c in df_final.columns if c not in cols_order]
    ]

    df_final.to_csv(OUTPUT_CSV, index=False)
    print(f"\n[OK] Datos solares exportados con éxito a: {OUTPUT_CSV}")
    print(f"Total registros obtenidos: {len(df_final)}")
    print(df_final.head(3))
  else:
    print("No se pudieron recuperar datos.")


if __name__ == "__main__":
  main()