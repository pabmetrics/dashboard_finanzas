"""Importador del informe de XTB (Excel con hojas Cash Operations, Open Positions, Closed Positions)."""
import re

import pandas as pd

from app.db import activo, cuenta, guardar_precio, insertar
from app.importers.comun import huella

TIPOS = {
    "Deposit": "aportacion",
    "Withdrawal": "retirada",
    "Stock purchase": "compra",
    "Stock sell": "venta",
    "Dividend": "dividendo",
    "Withholding tax": "retencion",
    "Free funds interest": "interes",
    "Free funds interest tax": "retencion",
}

# Clasificación por defecto de lo que hay/hubo en XTB (se puede cambiar luego en la app).
CLASIFICACION = {
    "EGLN.UK": ("etc", "Renta Variable", "Oro"),
    "XXBT.DE": ("etc", "Renta Variable", "Bitcoin"),
    "TRET.DE": ("etf", "Renta Fija", "REITs"),
    "IDUP.UK": ("etf", "Renta Fija", "REITs"),
}
VOLUMEN = re.compile(r"(?:OPEN|CLOSE) BUY (?:[A-Z][A-Z0-9]*\.[A-Z]+ )?([\d.]+)(?:/| @)")


def _hoja(ruta, nombre, texto_cabecera):
    bruto = pd.read_excel(ruta, sheet_name=nombre, header=None)
    fila = next(i for i in range(len(bruto)) if str(bruto.iloc[i, 0]).strip() == texto_cabecera
                or str(bruto.iloc[i, 1]).strip() == texto_cabecera)
    return pd.read_excel(ruta, sheet_name=nombre, header=fila)


def _activo_xtb(con, ticker, nombre, categoria_xtb):
    clase, cat, tipo = CLASIFICACION.get(ticker, ("accion" if categoria_xtb == "STOCK" else "etf",
                                                  "Renta Variable", "Acciones value"))
    return activo(con, nombre, ticker=ticker, clase=clase, categoria=cat, tipo_inversion=tipo)


def importar_xtb(con, ruta, nombre_cuenta="XTB"):
    cid = cuenta(con, nombre_cuenta, "broker", entidad="XTB", categoria="Renta Variable")

    cerradas = _hoja(ruta, "Closed Positions", "Instrument")
    vol_cerrada = {int(r["Position ID"]): float(r["Volume"]) for _, r in cerradas.iterrows()
                   if pd.notna(r.get("Position ID"))}

    caja = _hoja(ruta, "Cash Operations", "Type")
    caja = caja[caja["Type"].isin(TIPOS)]
    nuevas, sin_tipo = 0, 0
    for _, r in caja.iterrows():
        tipo = TIPOS[r["Type"]]
        importe = float(r["Amount"])
        fecha = pd.Timestamp(r["Time"]).strftime("%Y-%m-%d")
        aid, titulos, precio = None, None, None
        if pd.notna(r.get("Ticker")):
            aid = _activo_xtb(con, r["Ticker"], r["Instrument"], r.get("Category"))
        if tipo in ("compra", "venta"):
            m = VOLUMEN.search(str(r.get("Comment") or ""))
            if m:
                titulos = float(m.group(1))
            elif tipo == "venta" and pd.notna(r.get("Position ID")):
                titulos = vol_cerrada.get(int(r["Position ID"]))
            if titulos:
                precio = abs(importe) / titulos  # precio en EUR (el comentario lo da en la divisa del activo)
                guardar_precio(con, aid, fecha, precio, "operacion")
            else:
                sin_tipo += 1
        nuevas += insertar(
            con, "operaciones",
            cuenta_id=cid, activo_id=aid, fecha=fecha, tipo=tipo, titulos=titulos, precio=precio,
            importe=importe, nota=r.get("Comment"), huella=huella("xtb", int(r["ID"])),
        )

    # Posiciones abiertas: precio actual en EUR (valor / títulos) a la fecha del informe.
    bruto = pd.read_excel(ruta, sheet_name="Open Positions", header=None)
    fecha_informe = pd.Timestamp(bruto.iloc[2, 1]).strftime("%Y-%m-%d")
    abiertas = _hoja(ruta, "Open Positions", "Instrument/Position")
    resumen = abiertas[abiertas["Category"].notna() & abiertas["Ticker"].notna()]
    posiciones = []
    for _, r in resumen.iterrows():
        aid = _activo_xtb(con, r["Ticker"], r["Instrument/Position"], r["Category"])
        precio = float(r["Value"]) / float(r["Volume"])
        guardar_precio(con, aid, fecha_informe, precio, "xtb")
        posiciones.append({"ticker": r["Ticker"], "titulos": float(r["Volume"]), "valor": float(r["Value"])})

    return {"cuenta": nombre_cuenta, "operaciones_leidas": len(caja), "nuevas": nuevas,
            "sin_titulos": sin_tipo, "fecha_informe": fecha_informe, "posiciones_abiertas": posiciones}
