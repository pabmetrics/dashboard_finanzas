"""Utilidades comunes de los importadores."""
import hashlib
from collections import Counter

import pandas as pd

from app.db import guardar_valoracion, insertar


def huella(*partes) -> str:
    return hashlib.sha1("|".join(str(p) for p in partes).encode()).hexdigest()


def numero_es(v) -> float | None:
    """Convierte '1.234,56' o '-11,47' o '598.62 EUR' a float."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace("EUR", "").replace("€", "").strip()
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def categorizar(con, concepto: str, importe: float) -> tuple[str | None, str]:
    """Aplica las reglas (la más larga que encaje gana). Devuelve (categoria, tipo)."""
    texto = (concepto or "").lower()
    mejor = None
    for r in con.execute("SELECT patron, categoria, tipo FROM reglas"):
        if r["patron"].lower() in texto and (mejor is None or len(r["patron"]) > len(mejor["patron"])):
            mejor = r
    if mejor:
        return mejor["categoria"], mejor["tipo"] or ("Ingreso" if importe > 0 else "Gasto")
    return None, "Ingreso" if importe > 0 else "Gasto"


def guardar_movimientos(con, cuenta_id: int, filas: list[dict]) -> int:
    """Guarda movimientos bancarios evitando duplicados.

    filas: dicts con fecha (YYYY-MM-DD), concepto, detalle, importe, saldo (opcional).
    La huella incluye el nº de repetición dentro del archivo, para que dos movimientos
    idénticos el mismo día no se tomen por duplicados.
    """
    vistos = Counter()
    nuevos = 0
    for f in filas:
        clave = (f["fecha"], f.get("concepto"), f.get("detalle"), round(f["importe"], 2))
        vistos[clave] += 1
        categoria, tipo = categorizar(con, f"{f.get('concepto') or ''} {f.get('detalle') or ''}", f["importe"])
        nuevos += insertar(
            con, "movimientos",
            cuenta_id=cuenta_id, fecha=f["fecha"], concepto=f.get("concepto"), detalle=f.get("detalle"),
            importe=f["importe"], saldo=f.get("saldo"), categoria=categoria, tipo=tipo,
            huella=huella(cuenta_id, *clave, vistos[clave]),
        )
    return nuevos


def guardar_saldos_diarios(con, cuenta_id: int, filas: list[dict], fuente="extracto"):
    """Guarda como valoración el último saldo de cada día.

    filas deben venir en orden cronológico (de más antigua a más reciente).
    """
    ultimo = {}
    for f in filas:
        if f.get("saldo") is not None:
            ultimo[f["fecha"]] = f["saldo"]
    if ultimo:
        # desde que hay extracto manda el extracto: el Excel antiguo solo vale para fechas anteriores
        con.execute("DELETE FROM valoraciones WHERE cuenta_id = ? AND fuente = 'excel' AND fecha >= ?",
                    (cuenta_id, min(ultimo)))
    for fecha, saldo in ultimo.items():
        guardar_valoracion(con, cuenta_id, fecha, saldo, fuente)
    return len(ultimo)


def recalcular_saldo_acumulado(con, cuenta_id) -> dict:
    """Saldo diario de una cuenta cuyo extracto no trae saldo (Cuenta MyInvestor).

    saldo(día) = suma de todos los movimientos guardados hasta ese día (empezando en 0, desde la
    apertura de la cuenta). Si hay un saldo conocido (ancla), todo se desplaza para cuadrar con él.
    """
    movs = con.execute("SELECT fecha, SUM(importe) AS total FROM movimientos WHERE cuenta_id = ? "
                       "GROUP BY fecha ORDER BY fecha", (cuenta_id,)).fetchall()
    if not movs:
        return {"saldos": 0}
    acumulado, por_dia = 0.0, {}
    for m in movs:
        acumulado += m["total"]
        por_dia[m["fecha"]] = acumulado
    ancla = con.execute("SELECT fecha, saldo FROM anclas WHERE cuenta_id = ? ORDER BY fecha DESC LIMIT 1",
                        (cuenta_id,)).fetchone()
    ajuste = 0.0
    if ancla:
        previos = [f for f in por_dia if f <= ancla["fecha"]]
        ajuste = ancla["saldo"] - (por_dia[max(previos)] if previos else 0.0)
    con.execute("DELETE FROM valoraciones WHERE cuenta_id = ? AND fuente = 'extracto'", (cuenta_id,))
    filas = [{"fecha": f, "saldo": round(v + ajuste, 2)} for f, v in por_dia.items()]
    n = guardar_saldos_diarios(con, cuenta_id, filas)
    return {"saldos": n, "saldo_actual": filas[-1]["saldo"], "ajuste_por_ancla": round(ajuste, 2),
            "desde": movs[0]["fecha"]}
