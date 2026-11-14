"""Urbanitae, Excel antiguo y datos iniciales (cuentas manuales, reglas, plan)."""
from datetime import date

import pandas as pd

from app.db import cuenta, guardar_valoracion, insertar
from app.importers.comun import numero_es

# Cuentas que no se importan de ningún extracto: su valor se mete a mano.
CUENTAS_MANUALES = [
    # nombre, tipo, entidad, subtipo, categoria, tipo_inversion
    ("Efectivo", "manual", None, "Otros", "Liquidez", None),
    ("Pluxee", "manual", "Pluxee", "Otros", "Liquidez", None),
    ("Bleap", "manual", "Bleap", "Otros", "Liquidez", None),
    ("Cartera Rock", "manual", "MyInvestor", "Otros", "Otros", None),  # activo con valor a mano, fuera del plan
    ("Equito", "crowdfunding", "Equito", "Inmobiliario (tokens)", "Renta Fija", "Crowlending inmobiliario"),
    ("Urbanitae", "crowdfunding", "Urbanitae", "Inmobiliario (préstamo)", "Renta Fija", "Crowlending inmobiliario"),
]

REGLAS = [
    # patrón, categoría, tipo
    ("mercadona", "Alimentación", None), ("ahorramas", "Alimentación", None), ("carrefour", "Alimentación", None),
    ("lidl", "Alimentación", None), ("dia ", "Alimentación", None), ("alcampo", "Alimentación", None),
    ("amazon", "Compras", None), ("nómina", "Salario", "Ingreso"), ("nomina", "Salario", "Ingreso"),
    ("pension", "Salario", "Ingreso"), ("intereses", "Cobro de interés", "Ingreso"),
    ("renfe", "Transporte", None), ("cabify", "Transporte", None), ("uber", "Transporte", None),
    ("repsol", "Transporte", None), ("cepsa", "Transporte", None),
    ("farmacia", "Salud", None), ("netflix", "Ocio", None), ("spotify", "Ocio", None),
    ("restaurante", "Ocio", None), ("gelateria", "Ocio", None),
    ("alquiler", "Vivienda", None), ("airbnb", "Ocio", None), ("decathlon", "Compras", None),
    ("clinica", "Salud", None), ("autopista", "Transporte", None), ("gelaterie", "Ocio", None),
    ("ahorro", "Transferencia interna", "Transferencia"), ("transferencia desde", "Transferencia interna", "Transferencia"),
    ("redondeo", "Transferencia interna", "Transferencia"), ("traspaso", "Transferencia interna", "Transferencia"),
]

CATEGORIAS = ["Alimentación", "Vivienda", "Transporte", "Ocio", "Salud", "Educación", "Gastos financieros",
              "Compras", "Otros gastos", "Inversión", "Salario", "Dividendo", "Cobro de interés",
              "Transferencia interna"]


def inicializar(con):
    for nombre, tipo, entidad, subtipo, categoria, tipo_inv in CUENTAS_MANUALES:
        cuenta(con, nombre, tipo, entidad=entidad, subtipo=subtipo, categoria=categoria, tipo_inversion=tipo_inv)
    for patron, categoria, tipo in REGLAS:
        insertar(con, "reglas", patron=patron, categoria=categoria, tipo=tipo)


def importar_urbanitae(con, ruta, fecha=None):
    """Guarda como valor de Urbanitae el capital vivo (invertido en proyectos aún no terminados)."""
    df = pd.read_excel(ruta)
    vivos = df[df["Obtained IRR"].isna() | (df["Obtained IRR"].astype(str).str.strip() == "")]
    capital = sum(numero_es(v) or 0 for v in vivos["Invested amount"])
    fecha = fecha or date.today().isoformat()
    cid = cuenta(con, "Urbanitae", "crowdfunding")
    guardar_valoracion(con, cid, fecha, round(capital, 2), "extracto")
    proximos = [
        {"proyecto": r["Project name"], "trimestre": r["Next payment quarter"],
         "importe": numero_es(r["Next payment amount"]), "invertido": numero_es(r["Invested amount"]),
         "tir": numero_es(r["Updated IRR"])}
        for _, r in vivos.iterrows()
    ]
    return {"cuenta": "Urbanitae", "proyectos_vivos": len(vivos), "capital_vivo": capital, "proximos_pagos": proximos}


# Excel antiguo: a qué cuenta va cada inversión de la hoja Inversiones.
MAPA_INVERSIONES = {
    "Equito": "Equito", "Urbanitae": "Urbanitae", "Cartera Rock": "Cartera Rock",
    "Groupama": "Fondos MyInvestor", "MSCI World": "Fondos MyInvestor", "Emerging Markets": "Fondos MyInvestor",
    "Neuberger": "Fondos MyInvestor", "MyInvestor Value": "Fondos MyInvestor",
}
MAPA_ACTIVOS = {"Saldo XTB": "XTB"}  # el saldo libre de XTB va dentro de la cuenta XTB
MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7,
         "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12}


def _fecha_columna(col) -> str | None:
    """Las columnas del Excel antiguo (oct-25...) son el saldo a principio de ese mes."""
    if isinstance(col, (pd.Timestamp, date)):
        f = pd.Timestamp(col)
    else:
        s = str(col).strip().lower()
        if "-" not in s or s[:3] not in MESES:
            return None
        f = pd.Timestamp(year=2000 + int(s.split("-")[1]), month=MESES[s[:3]], day=1)
    return f.replace(day=1).strftime("%Y-%m-%d")


def importar_excel_antiguo(con, ruta):
    """Histórico mensual del Excel: saldos de Activos, valor de Inversiones y Plan."""
    hojas = pd.read_excel(ruta, sheet_name=None)
    total = 0
    valores: dict[tuple[str, str], float] = {}

    act = hojas["Activos"]
    tipos_cuenta = dict(zip(act["Nombre"], act["Tipo de Cuenta"]))
    for _, r in act.iterrows():
        nombre = MAPA_ACTIVOS.get(r["Nombre"], r["Nombre"])
        for col in act.columns[2:]:
            fecha = _fecha_columna(col)
            if fecha and pd.notna(r[col]):
                valores[(nombre, fecha)] = valores.get((nombre, fecha), 0) + float(r[col])

    inv = hojas["Inversiones"].ffill()
    for nombre_inv, g in inv.groupby("Nombre"):
        nombre = MAPA_INVERSIONES.get(nombre_inv, "XTB")
        metr = g.set_index("Métrica")
        for col in inv.columns[4:]:
            fecha = _fecha_columna(col)
            if not fecha:
                continue
            try:
                v = float(metr.loc["Títulos", col]) * float(metr.loc["Precio actual", col])
            except (KeyError, TypeError, ValueError):
                continue
            if pd.notna(v):
                valores[(nombre, fecha)] = valores.get((nombre, fecha), 0) + v

    # Solo meses con algún valor (el Excel tiene ceros antes de empezar a apuntar)
    for (nombre, fecha), v in valores.items():
        if abs(v) < 0.01:
            continue
        subtipo = tipos_cuenta.get(nombre)
        if subtipo and str(subtipo).lower().startswith("cuenta"):  # Cuenta nómina/corriente/remunerada
            cid = cuenta(con, nombre, "banco", entidad=nombre.split()[0], subtipo=subtipo, categoria="Liquidez")
        elif nombre in ("XTB", "Fondos MyInvestor"):
            cid = cuenta(con, nombre, "broker", entidad="XTB" if nombre == "XTB" else "Inversis")
        else:
            cid = cuenta(con, nombre, "manual", subtipo=subtipo, categoria="Liquidez")
        guardar_valoracion(con, cid, fecha, round(v, 2), "excel")
        total += 1

    if "Plan" in hojas:
        importar_plan(con, hojas["Plan"])
    return {"valoraciones": total}


TIPOS_INVERSION = ["Cuenta corriente", "Fondo monetario", "Renta fija", "Fondo indexado", "Fondo de inversión",
                   "Acciones value", "Crowlending inmobiliario", "REITs", "Oro", "Bitcoin", "Cartera indexada"]


def importar_plan(con, plan: pd.DataFrame):
    """Hoja Plan: bloque 'Fondo de emergencia' (importe + reparto) y bloque 'Inversiones' (reparto)."""
    bloque, objetivo = None, None
    filas = []
    for _, r in plan.iterrows():
        nombre = str(r["Activo"]).strip() if pd.notna(r["Activo"]) else ""
        if nombre == "Fondo de emergencia":
            bloque = "emergencia"
            importes = [v for v in r.iloc[2:] if pd.notna(v) and isinstance(v, (int, float))]
            objetivo = importes[-1] if importes else None
            continue
        if nombre == "Inversiones":
            bloque = "inversion"
            continue
        if bloque and nombre and pd.notna(r["Porcentaje"]):
            filas.append((bloque, nombre, float(r["Porcentaje"])))
    if filas:
        con.execute("DELETE FROM plan_reparto")
        con.executemany("INSERT OR REPLACE INTO plan_reparto (bloque, tipo, porcentaje) VALUES (?, ?, ?)", filas)
    if objetivo:
        con.execute("INSERT OR REPLACE INTO estado (clave, valor) VALUES ('emergencia_objetivo', ?)", (str(objetivo),))
