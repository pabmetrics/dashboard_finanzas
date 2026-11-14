"""Importador de operaciones de fondos de Inversis (el .xls que es en realidad una tabla HTML)."""
import io

import pandas as pd

from app.db import activo, cuenta, guardar_precio, insertar
from app.importers.comun import huella, numero_es

TIPOS = {
    "SUSCRIPCION": "compra",
    "REEMBOLSO": "venta",
    "SUSCR.POR TRASPASO I": "traspaso_entrada",
    "ALTA IIC SWITCH": "traspaso_entrada",
    "REEMB.POR TRASPASO I": "traspaso_salida",
    "BAJA IIC SWITCH": "traspaso_salida",
}

# Clasificación por ISIN (tipo de inversión como en la hoja Plan del Excel antiguo).
CLASIFICACION = {
    "FR0000989626": ("Renta Fija", "Fondo monetario"),       # Groupama Trésorerie
    "IE00BL1GVT98": ("Renta Fija", "Fondo monetario"),       # Ultra short term euro
    "IE00BFZMJT78": ("Renta Fija", "Renta fija"),            # Short duration euro bond
    "IE00BYX5NX33": ("Renta Variable", "Fondo indexado"),    # MSCI World
    "IE00BYX5MX67": ("Renta Variable", "Fondo indexado"),    # S&P 500
    "IE0031786696": ("Renta Variable", "Fondo indexado"),    # Emerging markets
    "ES0165243025": ("Renta Variable", "Fondo de inversión"),  # MyInvestor Value
}


def _leer(ruta) -> pd.DataFrame:
    with open(ruta, encoding="latin-1") as f:
        df = pd.read_html(io.StringIO(f.read()))[0]
    nombres = []
    for a, b in df.columns:
        if a == "Fechas":
            nombres.append(f"Fecha {b}")
        elif b == "Operación.1":
            nombres.append("Tipo")
        elif a == "Operación":
            nombres.append("Referencia")
        else:
            nombres.append(b)
    df.columns = nombres
    return df


def importar_inversis(con, ruta, nombre_cuenta="Fondos MyInvestor"):
    cid = cuenta(con, nombre_cuenta, "broker", entidad="Inversis", categoria="Renta Variable")
    df = _leer(ruta)
    nuevas, desconocidas = 0, []
    for _, r in df.iterrows():
        tipo = TIPOS.get(str(r["Tipo"]).strip())
        if tipo is None:
            desconocidas.append(str(r["Tipo"]))
            continue
        isin = str(r["ISIN"]).strip()
        cat, tipo_inv = CLASIFICACION.get(isin, ("Renta Variable", "Fondo indexado"))
        aid = activo(con, str(r["Valor"]).strip().title(), isin=isin, clase="fondo",
                     categoria=cat, tipo_inversion=tipo_inv)
        titulos = numero_es(r["Títulos/NOMINAL"])
        precio = numero_es(r["Precio Neto"])
        bruto = numero_es(r["Importe neto"])
        fecha = pd.to_datetime(r["Fecha Operación"]).strftime("%Y-%m-%d")
        # importe: negativo cuando entra dinero en el fondo (sale de la liquidez), positivo cuando sale
        importe = -bruto if tipo in ("compra", "traspaso_entrada") else bruto
        guardar_precio(con, aid, fecha, precio, "operacion")
        nuevas += insertar(
            con, "operaciones",
            cuenta_id=cid, activo_id=aid, fecha=fecha, tipo=tipo, titulos=titulos, precio=precio,
            importe=importe, nota=str(r["Tipo"]), huella=huella("inversis", r["Referencia"]),
        )
    return {"cuenta": nombre_cuenta, "operaciones_leidas": len(df), "nuevas": nuevas,
            "tipos_desconocidos": sorted(set(desconocidas))}
