"""Actualización diaria de precios (Yahoo Finance) con histórico.

- Fondos: se busca por ISIN (Yahoo da el código de Morningstar, p. ej. 0P0001CLDK.F).
- Acciones/ETF de XTB: el ticker de XTB se traduce al de Yahoo (EGLN.UK -> EGLN.L, NXT.ES -> NXT.MC...).
- Todo se pasa a EUR.
- Control de seguridad: antes de dar por bueno un símbolo, su precio se compara con el de una
  operación o informe real del mismo día (±10 %). Si no cuadra, no se usa y se avisa.
- Los precios de operaciones/informes (exactos) nunca se pisan con los de Yahoo.
"""
import json
import logging
import threading
import time
from datetime import date, datetime, timedelta

import pandas as pd

log = logging.getLogger("precios")

SUFIJOS_XTB = {"UK": ".L", "ES": ".MC", "DE": ".DE", "US": "", "FR": ".PA", "NL": ".AS", "IT": ".MI"}
TOLERANCIA = 0.10  # un error de divisa (USD/EUR ~10 %) o de símbolo salta


def _yf():
    import yfinance as yf  # import perezoso: tarda en cargar
    return yf


def candidatos(activo) -> list[str]:
    if activo["ticker_precio"]:
        return [activo["ticker_precio"]]
    if activo["isin"]:
        try:
            quotes = _yf().Search(activo["isin"], max_results=5).quotes
        except Exception as e:  # sin red, Yahoo caído...
            log.warning("búsqueda %s: %s", activo["isin"], e)
            return []
        simbolos = [q["symbol"] for q in quotes if q.get("symbol")]
        return sorted(simbolos, key=lambda s: not s.endswith(".F"))  # Morningstar (.F) primero
    if activo["ticker"] and "." in activo["ticker"]:
        base, mercado = activo["ticker"].rsplit(".", 1)
        if mercado in SUFIJOS_XTB:
            return [base + SUFIJOS_XTB[mercado]]
    return []


_fx_cache: dict[str, pd.Series] = {}


def _a_eur(serie: pd.Series, moneda: str | None, desde: str) -> pd.Series | None:
    if not moneda or moneda == "EUR":
        return serie
    factor = 1.0
    if moneda in ("GBp", "GBX"):
        moneda, factor = "GBP", 0.01
    if moneda not in _fx_cache:
        fx = _yf().Ticker(f"EUR{moneda}=X").history(start=desde, auto_adjust=False)["Close"]
        fx.index = fx.index.tz_localize(None).normalize()
        _fx_cache[moneda] = fx
    fx = _fx_cache[moneda].reindex(serie.index, method="ffill")
    return (serie * factor / fx).dropna()


def historico(simbolo: str, desde: str) -> pd.Series | None:
    """Cierres diarios en EUR desde la fecha (índice: fecha sin hora)."""
    t = _yf().Ticker(simbolo)
    h = t.history(start=desde, auto_adjust=False)
    if h is None or h.empty:
        return None
    serie = h["Close"].dropna()
    serie.index = serie.index.tz_localize(None).normalize()
    try:
        moneda = t.fast_info.get("currency")
    except Exception:
        moneda = None
    return _a_eur(serie, moneda, desde)


def _valida(con, activo_id, serie: pd.Series) -> tuple[bool, str]:
    """Compara con precios reales (operaciones/informes) en fechas que la serie cubre."""
    reales = con.execute("SELECT fecha, precio FROM precios WHERE activo_id = ? AND fuente != 'yahoo' "
                         "ORDER BY fecha DESC LIMIT 5", (activo_id,)).fetchall()
    comprobados = 0
    for r in reales:
        f = pd.Timestamp(r["fecha"])
        cerca = serie[(serie.index >= f - pd.Timedelta(days=4)) & (serie.index <= f + pd.Timedelta(days=4))]
        if cerca.empty:
            continue
        ratio = float(cerca.iloc[0]) / r["precio"]
        if not (1 - TOLERANCIA <= ratio <= 1 + TOLERANCIA):
            return False, f"precio {cerca.iloc[0]:.4f} frente a {r['precio']:.4f} real el {r['fecha']}"
        comprobados += 1
    return (True, "ok") if comprobados else (True, "sin precio real con el que comparar")


def actualizar(con) -> dict:
    """Descarga precios desde el último guardado (o desde la primera operación) hasta hoy."""
    resultado = {"actualizados": [], "fallidos": [], "nuevos_precios": 0}
    activos = con.execute(
        "SELECT a.*, MIN(o.fecha) AS primera FROM activos a JOIN operaciones o ON o.activo_id = a.id "
        "GROUP BY a.id").fetchall()
    _fx_cache.clear()
    for a in activos:
        ultimo = con.execute("SELECT MAX(fecha) FROM precios WHERE activo_id = ? AND fuente = 'yahoo'",
                             (a["id"],)).fetchone()[0]
        desde = (date.fromisoformat(ultimo) - timedelta(days=7)).isoformat() if ultimo else a["primera"]
        hecho = False
        for simbolo in candidatos(a):
            try:
                serie = historico(simbolo, desde)
            except Exception as e:
                log.warning("%s: %s", simbolo, e)
                continue
            if serie is None or serie.empty:
                continue
            ok, motivo = _valida(con, a["id"], serie)
            if not ok:
                resultado["fallidos"].append({"activo": a["nombre"], "simbolo": simbolo, "motivo": motivo})
                continue
            n = 0
            for f, p in serie.items():
                cur = con.execute("INSERT OR IGNORE INTO precios (activo_id, fecha, precio, fuente) "
                                  "VALUES (?, ?, ?, 'yahoo')", (a["id"], f.strftime("%Y-%m-%d"), float(p)))
                n += cur.rowcount
            if not a["ticker_precio"]:
                con.execute("UPDATE activos SET ticker_precio = ? WHERE id = ?", (simbolo, a["id"]))
            resultado["nuevos_precios"] += n
            resultado["actualizados"].append({"activo": a["nombre"], "simbolo": simbolo, "ultimo": serie.index[-1].strftime("%Y-%m-%d")})
            hecho = True
            break
        if not hecho and not any(f["activo"] == a["nombre"] for f in resultado["fallidos"]):
            resultado["fallidos"].append({"activo": a["nombre"], "simbolo": None, "motivo": "sin cotización en Yahoo"})
    ahora = datetime.now().isoformat(timespec="minutes")
    con.execute("INSERT OR REPLACE INTO estado (clave, valor) VALUES ('precios_actualizados', ?)", (ahora,))
    con.execute("INSERT OR REPLACE INTO estado (clave, valor) VALUES ('precios_resultado', ?)",
                (json.dumps(resultado, ensure_ascii=False),))
    con.commit()
    return resultado


_cerrojo = threading.Lock()


def actualizar_seguro(conectar) -> dict | None:
    """Evita dos actualizaciones a la vez (la automática y el botón)."""
    if not _cerrojo.acquire(blocking=False):
        return None
    try:
        con = conectar()
        try:
            return actualizar(con)
        finally:
            con.close()
    finally:
        _cerrojo.release()


def bucle_diario(conectar, cada_horas=6):
    """Hilo en segundo plano: actualiza si la última actualización tiene más de `cada_horas` horas."""
    time.sleep(30)  # deja arrancar la app
    while True:
        try:
            con = conectar()
            fila = con.execute("SELECT valor FROM estado WHERE clave = 'precios_actualizados'").fetchone()
            con.close()
            if not fila or datetime.now() - datetime.fromisoformat(fila["valor"]) > timedelta(hours=cada_horas):
                r = actualizar_seguro(conectar)
                if r:
                    log.info("precios: %d nuevos, %d fallidos", r["nuevos_precios"], len(r["fallidos"]))
        except Exception:
            log.exception("error actualizando precios")
        time.sleep(1800)
