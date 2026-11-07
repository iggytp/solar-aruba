#!/usr/bin/env python3
"""Une las tres fuentes de Aruba en un dataset a 5 minutos para dos estaciones solares.

Solo usa la biblioteca estandar de Python 3.10+. Lee el JSON grande por bloques.
Guardar este archivo en src/cruzar_aruba.py dentro del repositorio solar-aruba.

Por defecto lee los archivos de data/ y guarda alli aruba_cruzado_5min.csv e
informe_cruce.json. Las rutas se calculan desde este archivo, no desde la
carpeta desde la que se ejecuta el comando.

Entradas predeterminadas:
    data/aruba_stations.json
    data/aruba_readings_20260924.json (JSON local de lecturas)
    data/aruba_solar_radiation.csv

Desde la raiz del repositorio:
    python src/cruzar_aruba.py

Si el JSON de lecturas esta fuera de data/:
    python src/cruzar_aruba.py --readings /ruta/al/aruba_readings_20260924.json

Los argumentos permiten indicar otras rutas. Las rutas relativas escritas
explicitamente como argumentos se interpretan desde la carpeta de ejecucion.
"""

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


# La misma estructura que el resto de scripts de src/: los datos estan en
# la carpeta data/ de la raiz del repositorio, un nivel por encima de src/.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

PASO = timedelta(minutes=5)
HORA = timedelta(hours=1)
METEO = (
    "temperature_c", "humidity_pct", "wind_speed_kmh", "wind_direction_deg",
    "pressure_hpa", "precipitation_mm", "visibility_km", "uv_index",
)
RADIACION = (
    "shortwave_radiation_instant", "direct_normal_irradiance_instant",
    "diffuse_radiation_instant", "direct_radiation_instant", "cloud_cover",
)


def fecha(valor):
    """Exige zona horaria y normaliza a UTC; no redondea lecturas meteorologicas."""
    dt = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError(f"Fecha sin zona horaria: {valor!r}")
    return dt.astimezone(timezone.utc)


def iso(dt):
    return dt.isoformat(timespec="seconds").replace("+00:00", "Z")


def numero(valor, campo):
    if valor is None or valor == "":
        return None
    n = float(valor)
    if not math.isfinite(n):
        raise ValueError(f"Valor no finito en {campo}: {valor!r}")
    return n


def objetos_json(ruta, bloque=1024 * 1024):
    """Itera un array JSON sin cargar los 500 MB de lecturas en memoria."""
    decoder = json.JSONDecoder()
    with ruta.open(encoding="utf-8-sig") as archivo:
        buffer, pos, eof = "", 0, False

        def rellenar():
            nonlocal buffer, pos, eof
            nuevo = archivo.read(bloque)
            buffer = buffer[pos:] + nuevo
            pos = 0
            eof = not nuevo

        def siguiente():
            nonlocal pos
            while True:
                while pos < len(buffer) and buffer[pos].isspace():
                    pos += 1
                if pos < len(buffer) or eof:
                    return buffer[pos:pos + 1]
                rellenar()

        if siguiente() != "[":
            raise ValueError(f"{ruta.name}: se esperaba un array JSON.")
        pos += 1
        primero = True
        while True:
            caracter = siguiente()
            if caracter == "]":
                pos += 1
                if siguiente():
                    raise ValueError("Contenido despues del array JSON.")
                return
            if not primero:
                if caracter != ",":
                    raise ValueError("Se esperaba una coma entre lecturas.")
                pos += 1
                if siguiente() == "]":
                    raise ValueError("Coma final no valida en JSON.")
            while True:
                try:
                    obj, fin = decoder.raw_decode(buffer, pos)
                    pos = fin
                    break
                except json.JSONDecodeError:
                    if eof:
                        raise
                    rellenar()
            if not isinstance(obj, dict):
                raise ValueError("Cada lectura debe ser un objeto JSON.")
            yield obj
            primero = False


def argumentos():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--stations", type=Path, default=DATA_DIR / "aruba_stations.json",
                   help="Catalogo de estaciones (por defecto: data/aruba_stations.json).")
    p.add_argument("--readings", type=Path, default=DATA_DIR / "aruba_readings_20260924.json",
                   help="JSON de lecturas locales (por defecto: data/aruba_readings_20260924.json).")
    p.add_argument("--radiation", type=Path, default=DATA_DIR / "aruba_solar_radiation.csv",
                   help="CSV de radiacion (por defecto: data/aruba_solar_radiation.csv).")
    seleccion = p.add_mutually_exclusive_group()
    seleccion.add_argument("--solar-stations", nargs="+", metavar="ID_CODIGO_O_NOMBRE",
                           help="Lista confirmada de estaciones con paneles solares.")
    seleccion.add_argument("--usar-estaciones-del-csv", action="store_true",
                           help="Usar las dos estaciones del CSV (comportamiento predeterminado).")
    p.add_argument("--metodo", choices=("repetir", "interpolar"), default="repetir",
                   help="Repetir cada valor horario 12 veces (predeterminado), o interpolar instantes.")
    p.add_argument("--output-dir", type=Path, default=DATA_DIR,
                   help="Carpeta de salida del CSV y del informe (por defecto: data/).")
    return p.parse_args()


def cargar_estaciones(ruta):
    with ruta.open(encoding="utf-8-sig") as archivo:
        datos = json.load(archivo)
    if not isinstance(datos, list):
        raise ValueError("stations debe contener un array JSON.")
    estaciones = {}
    for original in datos:
        s = dict(original)
        sid = str(s["id"])
        if sid in estaciones:
            raise ValueError(f"ID de estacion duplicado: {sid}")
        s["latitude"] = numero(s["latitude"], "latitude")
        s["longitude"] = numero(s["longitude"], "longitude")
        if s["latitude"] is None or s["longitude"] is None:
            raise ValueError(f"Coordenadas ausentes: {sid}")
        if not (-90 <= s["latitude"] <= 90 and -180 <= s["longitude"] <= 180):
            raise ValueError(f"Coordenadas fuera de rango: {sid}")
        estaciones[sid] = s
    return estaciones


def seleccionar(args, estaciones, ids_csv):
    if args.solar_stations:
        ids = set()
        for token in args.solar_stations:
            candidatos = [sid for sid, s in estaciones.items() if token.casefold() in
                          {str(s.get(c, "")).casefold() for c in ("id", "code", "name")}]
            if len(candidatos) != 1:
                raise ValueError(f"Estacion desconocida o ambigua: {token!r}")
            ids.add(candidatos[0])
        criterio = "lista_confirmada_por_usuario"
    else:
        ids = set(ids_csv)
        criterio = "dos_estaciones_solares_del_csv_confirmadas_por_usuario"
    if len(ids) != 2:
        raise ValueError(f"Se requieren exactamente dos estaciones solares; se encontraron {len(ids)}. "
                         "Utiliza el CSV actualizado o selecciona dos con --solar-stations.")
    desconocidas = ids - set(estaciones)
    if desconocidas:
        raise ValueError(f"Estaciones solares sin datos en el catalogo: {sorted(desconocidas)}")
    faltantes = ids - ids_csv
    if faltantes:
        raise ValueError(f"Estaciones seleccionadas sin radiacion: {sorted(faltantes)}")
    return ids, criterio


def comprobar_coordenadas(registro, estacion):
    for campo in ("latitude", "longitude"):
        if registro.get(campo) not in (None, ""):
            n = numero(registro[campo], campo)
            if not math.isclose(n, estacion[campo], abs_tol=1e-6, rel_tol=0):
                raise ValueError(f"Coordenadas incompatibles para {estacion['id']}: {campo}")


def ampliar_radiacion(filas, seleccion, estaciones, metodo):
    por_estacion = defaultdict(list)
    for fila in filas:
        sid = fila["station_id"]
        if sid not in seleccion:
            continue
        comprobar_coordenadas(fila, estaciones[sid])
        t = fecha(fila["timestamp"])
        if t.minute or t.second or t.microsecond:
            raise ValueError(f"Radiacion no horaria: {sid}, {t}")
        valores = {c: numero(fila.get(c), c) for c in RADIACION}
        valores["is_day"] = numero(fila.get("is_day"), "is_day")
        valores["sunshine_duration"] = numero(fila.get("sunshine_duration"), "sunshine_duration")
        por_estacion[sid].append((t, valores))
    ampliadas = {}
    for sid, datos in por_estacion.items():
        datos.sort(key=lambda x: x[0])
        if len({t for t, _ in datos}) != len(datos):
            raise ValueError(f"Radiacion duplicada para {sid}.")
        for i, (t, valores) in enumerate(datos):
            siguiente = datos[i + 1] if i + 1 < len(datos) else None
            for j in range(12):
                resultado = dict(valores)
                estado = "repetido_desde_hora"
                if metodo == "interpolar":
                    if j == 0:
                        estado = "instante_original"
                    elif siguiente is not None and siguiente[0] - t == HORA:
                        for campo in RADIACION:
                            a, b = valores[campo], siguiente[1][campo]
                            resultado[campo] = None if a is None or b is None else round(a + (b - a) * j / 12, 6)
                        estado = "interpolado_lineal"
                    else:
                        # Conserva la rejilla, pero no inventa valores fuera del soporte.
                        resultado = {campo: None for campo in valores}
                        estado = "sin_siguiente_hora_no_extrapolado"
                resultado["sunshine_duration_source_s"] = resultado.pop("sunshine_duration")
                resultado["radiation_source_timestamp"] = iso(t)
                resultado["radiation_quality"] = estado
                ampliadas[(sid, t + j * PASO)] = resultado
    return ampliadas


def ejecutar(args):
    # Avisar de entradas ausentes antes de comenzar a procesar los archivos.
    for opcion in ("stations", "readings", "radiation"):
        ruta = getattr(args, opcion)
        if not ruta.is_file():
            raise FileNotFoundError(
                f"No se encuentra el archivo de entrada: {ruta}. "
                f"Colocalo en data/ o indica su ubicacion con --{opcion}."
            )
    estaciones = cargar_estaciones(args.stations)
    with args.radiation.open(encoding="utf-8-sig", newline="") as archivo:
        lector = csv.DictReader(archivo)
        if not {"station_id", "timestamp", "shortwave_radiation_instant"} <= set(lector.fieldnames or []):
            raise ValueError("Faltan columnas obligatorias en radiacion.")
        filas = list(lector)
    ids_csv = {f["station_id"] for f in filas}
    seleccion, criterio = seleccionar(args, estaciones, ids_csv)
    radiacion = ampliar_radiacion(filas, seleccion, estaciones, args.metodo)
    if not radiacion:
        raise ValueError("No hay radiacion para la seleccion.")
    inicio = min(t for _, t in radiacion)
    fin = max(t for _, t in radiacion)
    cruzadas = {}
    cuenta = Counter()
    limites_lecturas = {}
    duplicadas_identicas = 0
    total = 0
    min_lectura, max_lectura = None, None
    print(f"Seleccion: {', '.join(estaciones[s]['name'] for s in sorted(seleccion))}", flush=True)
    print("Leyendo lecturas meteorologicas por bloques...", flush=True)
    for lectura in objetos_json(args.readings):
        total += 1
        sid = str(lectura.get("station_id", ""))
        if sid not in seleccion:
            continue
        t = fecha(lectura["timestamp"])
        if t.minute % 5 or t.second or t.microsecond:
            raise ValueError(f"Lectura fuera de la rejilla de cinco minutos: {sid}, {t}")
        if sid not in limites_lecturas:
            limites_lecturas[sid] = [t, t]
        else:
            limites_lecturas[sid][0] = min(limites_lecturas[sid][0], t)
            limites_lecturas[sid][1] = max(limites_lecturas[sid][1], t)
        min_lectura = t if min_lectura is None else min(min_lectura, t)
        max_lectura = t if max_lectura is None else max(max_lectura, t)
        if not inicio <= t <= fin:
            continue
        clave = (sid, t)
        if clave not in radiacion:
            continue
        s = estaciones[sid]
        comprobar_coordenadas(lectura, s)
        fila = {
            "station_id": sid, "station_name": s["name"], "station_code": s.get("code", ""),
            "latitude": s["latitude"], "longitude": s["longitude"], "timestamp": iso(t),
            "elevation_m": s.get("elevation_m", ""), "district": s.get("district", ""),
            "is_active": s.get("is_active", ""), "reading_available": True,
            "reading_id": lectura.get("id", ""),
            **{c: numero(lectura.get(c), c) for c in METEO},
            **radiacion[clave],
        }
        if clave in cruzadas:
            # El ID de lectura puede cambiar aunque los valores sean identicos.
            if any(cruzadas[clave][c] != fila[c] for c in METEO):
                raise ValueError(f"Lecturas duplicadas con valores distintos: {sid}, {t}")
            duplicadas_identicas += 1
            continue
        cruzadas[clave] = fila
        cuenta[sid] += 1
    for sid in seleccion:
        if sid not in limites_lecturas:
            raise ValueError(f"No hay lecturas meteorologicas para la estacion solar {sid}.")
    # Mantiene todos los intervalos del periodo comun, tambien los huecos meteorologicos.
    rejilla = {clave: valores for clave, valores in radiacion.items()
               if limites_lecturas[clave[0]][0] <= clave[1] <= limites_lecturas[clave[0]][1]}
    for sid in seleccion:
        fechas_estacion = sorted(t for s, t in rejilla if s == sid)
        if not fechas_estacion:
            raise ValueError(f"No hay periodo comun entre radiacion y lecturas para {sid}.")
        if any(b - a != PASO for a, b in zip(fechas_estacion, fechas_estacion[1:])):
            raise ValueError(f"Hay horas de radiacion ausentes en {sid}; no se puede construir la rejilla continua.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    columnas_estacion = ("station_id", "station_name", "station_code", "latitude", "longitude",
                         "elevation_m", "district", "is_active", "timestamp")
    columnas_sol = (*RADIACION, "is_day", "sunshine_duration_source_s", "radiation_source_timestamp", "radiation_quality")
    destino = args.output_dir / "aruba_cruzado_5min.csv"
    with destino.open("w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=(*columnas_estacion, "reading_id", "reading_available", *METEO, *columnas_sol))
        escritor.writeheader()
        for clave in sorted(rejilla, key=lambda x: (x[1], x[0])):
            if clave in cruzadas:
                escritor.writerow(cruzadas[clave])
            else:
                sid, t = clave
                s = estaciones[sid]
                escritor.writerow(dict(station_id=sid, station_name=s["name"], station_code=s.get("code", ""),
                                        latitude=s["latitude"], longitude=s["longitude"],
                                        elevation_m=s.get("elevation_m", ""), district=s.get("district", ""),
                                        is_active=s.get("is_active", ""), timestamp=iso(t),
                                        reading_available=False, **rejilla[clave]))
    desconocidas = sorted(ids_csv - set(estaciones))
    informe = {
        "criterio_seleccion": criterio,
        "metodo_radiacion": args.metodo,
        "zona_horaria": "UTC",
        "cruce": "station_id + timestamp exacto; coordenadas procedentes del catalogo",
        "radiacion_original_filas": len(filas),
        "radiacion_filas_seleccionadas": sum(f["station_id"] in seleccion for f in filas),
        "radiacion_5min_filas": len(radiacion),
        "lecturas_json_revisadas": total,
        "lecturas_duplicadas_identicas_eliminadas": duplicadas_identicas,
        "filas_dataset": len(rejilla),
        "filas_con_lectura": len(cruzadas),
        "filas_dataset_sin_lectura": len(rejilla) - len(cruzadas),
        "radiacion_5min_fuera_periodo_lecturas": len(radiacion) - len(rejilla),
        "inicio_dataset": iso(min(t for _, t in rejilla)),
        "fin_dataset": iso(max(t for _, t in rejilla)),
        "inicio_radiacion_5min": iso(inicio), "fin_radiacion_5min": iso(fin),
        "inicio_lecturas_seleccionadas": iso(min_lectura) if min_lectura else None,
        "fin_lecturas_seleccionadas": iso(max_lectura) if max_lectura else None,
        "estaciones_radiacion_sin_catalogo_excluidas": desconocidas,
        "estaciones": [{"id": s, "name": estaciones[s]["name"],
                        "latitude": estaciones[s]["latitude"], "longitude": estaciones[s]["longitude"],
                        "filas_con_lectura": cuenta[s],
                        "filas_dataset": sum(sid == s for sid, _ in rejilla),
                        "inicio_dataset": iso(min(t for sid, t in rejilla if sid == s)),
                        "fin_dataset": iso(max(t for sid, t in rejilla if sid == s))}
                       for s in sorted(seleccion)],
        "avisos": [],
    }
    if desconocidas:
        informe["avisos"].append("Estaciones sin catalogo excluidas; no se inventan coordenadas ni equivalencias.")
    if informe["filas_dataset_sin_lectura"]:
        informe["avisos"].append("Los intervalos sin lectura se conservan con meteorologia vacia y reading_available=False.")
    if duplicadas_identicas:
        informe["avisos"].append("Se conserva la primera lectura cuando todos los valores meteorologicos coinciden; los duplicados con valores distintos producen un error.")
    informe["avisos"].append("La radiacion a 5 minutos es una estimacion; sunshine_duration_source_s conserva el dato original, no una duracion de 5 minutos.")
    with (args.output_dir / "informe_cruce.json").open("w", encoding="utf-8") as archivo:
        json.dump(informe, archivo, ensure_ascii=False, indent=2)
        archivo.write("\n")
    print(f"Resultado: {len(rejilla):,} filas del dataset; {len(cruzadas):,} con lectura. {destino}")
    print(f"Sin lectura: {informe['filas_dataset_sin_lectura']:,}. Fuera del periodo comun: {len(radiacion) - len(rejilla):,}")
    return 0 if cruzadas else 2


if __name__ == "__main__":
    try:
        sys.exit(ejecutar(argumentos()))
    except (ValueError, KeyError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
