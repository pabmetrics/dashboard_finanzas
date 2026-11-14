"""Importadores de extractos bancarios: Revolut, BBVA y cuenta MyInvestor."""
import pandas as pd

from app.db import cuenta
from app.importers.comun import (guardar_movimientos, guardar_saldos_diarios, numero_es,
                                 recalcular_saldo_acumulado)


def _resultado(nombre, filas, nuevos, saldos):
    return {
        "cuenta": nombre,
        "leidos": len(filas),
        "nuevos": nuevos,
        "desde": filas[0]["fecha"] if filas else None,
        "hasta": filas[-1]["fecha"] if filas else None,
        "saldos": saldos,
    }


def importar_revolut(con, ruta, nombre_cuenta="Revolut"):
    df = pd.read_csv(ruta)
    df = df[df["State"].astype(str).str.upper().isin(["COMPLETADO", "COMPLETED"])]
    filas = []
    for _, r in df.iterrows():
        importe = numero_es(r["Importe"]) - (numero_es(r.get("Comisión")) or 0)
        filas.append({
            "fecha": str(r["Fecha de inicio"])[:10],
            "concepto": r["Descripción"],
            "detalle": r["Tipo"],
            "importe": round(importe, 2),
            "saldo": numero_es(r["Saldo"]),
        })
    filas.sort(key=lambda f: f["fecha"])  # estable: respeta el orden del archivo dentro del día
    cid = cuenta(con, nombre_cuenta, "banco", entidad="Revolut", subtipo="Cuenta corriente", categoria="Liquidez")
    nuevos = guardar_movimientos(con, cid, filas)
    saldos = guardar_saldos_diarios(con, cid, filas)
    return _resultado(nombre_cuenta, filas, nuevos, saldos)


def importar_bbva(con, ruta, nombre_cuenta="BBVA"):
    bruto = pd.read_excel(ruta, header=None)
    fila_cab = next(i for i in range(len(bruto)) if str(bruto.iloc[i, 1]).strip() == "Fecha valor")
    df = pd.read_excel(ruta, header=fila_cab)
    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(subset=["Fecha", "Importe"])
    filas = []
    for _, r in df.iterrows():
        filas.append({
            "fecha": pd.to_datetime(r["Fecha"], dayfirst=True).strftime("%Y-%m-%d"),
            "concepto": r["Concepto"],
            "detalle": None if pd.isna(r.get("Movimiento")) else r.get("Movimiento"),
            "importe": numero_es(r["Importe"]),
            "saldo": numero_es(r["Disponible"]),
        })
    filas.reverse()  # BBVA viene de más reciente a más antiguo
    cid = cuenta(con, nombre_cuenta, "banco", entidad="BBVA", subtipo="Cuenta nómina", categoria="Liquidez")
    nuevos = guardar_movimientos(con, cid, filas)
    saldos = guardar_saldos_diarios(con, cid, filas)
    return _resultado(nombre_cuenta, filas, nuevos, saldos)


def importar_myinvestor_cuenta(con, ruta, saldo_final=None, nombre_cuenta="Cuenta MyInvestor"):
    """El extracto de MyInvestor no trae saldo: se calcula acumulando todos los movimientos guardados.

    - Si los movimientos guardados empiezan en la apertura de la cuenta, no hace falta nada más.
    - Si no, basta indicar UNA vez el saldo tras el último movimiento de un archivo (saldo_final):
      queda como referencia y el resto se cuadra a partir de él.
    """
    df = pd.read_csv(ruta, sep=";", encoding="utf-8-sig")
    filas = []
    for _, r in df.iterrows():
        filas.append({
            "fecha": pd.to_datetime(r["Fecha de operación"], dayfirst=True).strftime("%Y-%m-%d"),
            "concepto": r["Concepto"],
            "detalle": None,
            "importe": numero_es(r["Importe"]),
        })
    filas.reverse()  # viene de más reciente a más antiguo
    filas.sort(key=lambda f: f["fecha"])
    cid = cuenta(con, nombre_cuenta, "banco", entidad="MyInvestor", subtipo="Cuenta remunerada", categoria="Liquidez")
    nuevos = guardar_movimientos(con, cid, filas)
    if saldo_final is not None and filas:
        con.execute("INSERT OR REPLACE INTO anclas (cuenta_id, fecha, saldo) VALUES (?, ?, ?)",
                    (cid, filas[-1]["fecha"], saldo_final))
    res = recalcular_saldo_acumulado(con, cid)
    return _resultado(nombre_cuenta, filas, nuevos, res["saldos"]) | {
        "saldo_actual": res.get("saldo_actual"), "con_referencia": res.get("ajuste_por_ancla", 0) != 0}
