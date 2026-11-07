"""Calcula energia sobre el CSV que ya contiene registros cada cinco minutos.

No crea los registros meteorologicos originales, genera la potencia y energía estimadas a partir de la radiación, temperatura y velocidad del viento
mediante formulas simplificadas. La potencia y energía estimadas se calculan con la suposición de que el factor de soiling es 1.0 (sin suciedad).
"""

import csv
import math
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"


def numero(valor):
    try:
        valor = float(valor)
        return valor if math.isfinite(valor) else None
    except (ValueError, TypeError):
        return None


def main():
    carpeta = PROJECT_ROOT
    entrada = DATA_DIR / "aruba_cruzado_5min.csv"
    salida = DATA_DIR / "aruba_cruzado_5min_con_energia.csv"
    if not entrada.exists():
        print(f"No existe el CSV de entrada en '{entrada}'.")
        return
    nuevas = [
        "wind_speed_ms", "radiacion_aproximada_wm2",
        "temperatura_celda_estimada_c", "potencia_limpia_mw",
        "energia_limpia_kwh", "soiling_factor_supuesto",
        "potencia_estimada_mw", "energia_estimada_kwh",
    ]
    filas = 0
    calculadas = 0
    with entrada.open(encoding="utf-8-sig", newline="") as origen:
        lector = csv.DictReader(origen)
        with salida.open("w", encoding="utf-8", newline="") as destino:
            escritor = csv.DictWriter(destino, fieldnames=list(lector.fieldnames) + nuevas)
            escritor.writeheader()
            for fila in lector:
                t = numero(fila["temperature_c"])
                v = numero(fila["wind_speed_kmh"])
                g = numero(fila["shortwave_radiation_instant"])
                fila.update({columna: "" for columna in nuevas})
                fila["soiling_factor_supuesto"] = 1.0
                if v is not None and v >= 0:
                    fila["wind_speed_ms"] = v / 3.6
                if g is not None and g >= 0:
                    fila["radiacion_aproximada_wm2"] = g
                if t is not None and v is not None and v >= 0 and g is not None and g >= 0:
                    tc = t + g / (25 + 6.84 * v / 3.6)
                    potencia = max(0, 7.5 * g / 1000 * (1 - 0.004 * (tc - 25)))
                    energia = potencia * 1000 * 5 / 60
                    fila["temperatura_celda_estimada_c"] = tc
                    fila["potencia_limpia_mw"] = potencia
                    fila["potencia_estimada_mw"] = potencia
                    fila["energia_limpia_kwh"] = energia
                    fila["energia_estimada_kwh"] = energia
                    calculadas += 1
                escritor.writerow(fila)
                filas += 1
    print(f"Archivo guardado: {salida.name}")
    print(f"Filas: {filas}; con energia: {calculadas}; sin energia: {filas - calculadas}")


if __name__ == "__main__":
    main()
