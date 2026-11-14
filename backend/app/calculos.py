"""Cálculo de posiciones, valor de cada cuenta en una fecha y evolución del patrimonio.

Criterios:
- Bancos y activos manuales: último saldo/valor conocido en esa fecha.
- Crowdfunding (Equito, Urbanitae): último valor conocido + aportaciones/compras - retiradas/ventas
  posteriores. Las rentas e intereses NO suben el valor: cuentan como rendimiento cobrado.
- Brókers: títulos x último precio conocido (+ efectivo en XTB). Si faltan precios recientes
  y hay dato del Excel antiguo para ese mes, se usa el del Excel.
- Coste medio: los traspasos entre fondos conservan el coste (como en Hacienda).
"""
from collections import defaultdict
from datetime import date, timedelta

import pandas as pd

ENTRAN = {"compra", "traspaso_entrada"}
SALEN = {"venta", "traspaso_salida"}
RENDIMIENTOS = {"dividendo", "retencion", "interes", "renta", "comision"}
MAX_ANTIGUEDAD_PRECIO = 62  # días


def _ops(con, cuenta_id, hasta):
    return [dict(r) for r in con.execute(
        "SELECT * FROM operaciones WHERE cuenta_id = ? AND fecha <= ? ORDER BY fecha, id", (cuenta_id, hasta))]


def precio_en(con, activo_id, fecha):
    r = con.execute("SELECT fecha, precio FROM precios WHERE activo_id = ? AND fecha <= ? "
                    "ORDER BY fecha DESC LIMIT 1", (activo_id, fecha)).fetchone()
    return (r["precio"], r["fecha"]) if r else (None, None)


def posiciones(con, cuenta_id, hasta):
    """Devuelve (posiciones por activo, resumen de flujos de la cuenta)."""
    pos = defaultdict(lambda: {"titulos": 0.0, "coste": 0.0, "realizado": 0.0})
    flujos = {"aportado": 0.0, "retirado": 0.0, "rendimientos": 0.0, "caja": 0.0}
    ops = _ops(con, cuenta_id, hasta)
    usa_caja = any(o["tipo"] in ("aportacion", "retirada") for o in ops)

    por_fecha = defaultdict(list)
    for o in ops:
        por_fecha[o["fecha"]].append(o)

    # Traspasos pendientes: lo que ha salido de un fondo y aún no ha entrado en otro
    # (Inversis liquida la salida y la entrada en días distintos).
    bolsa_coste = bolsa_importe = 0.0
    for fecha in sorted(por_fecha):
        dia = por_fecha[fecha]
        for o in dia:
            if o["tipo"] in SALEN and o["activo_id"]:
                p = pos[o["activo_id"]]
                t = min(o["titulos"] or 0, p["titulos"]) if p["titulos"] > 0 else 0
                parte = p["coste"] * t / p["titulos"] if p["titulos"] > 0 else 0
                # no se puede vender más de lo que hay (p. ej. acciones regaladas sin compra registrada)
                p["titulos"] = max(p["titulos"] - (o["titulos"] or 0), 0.0)
                p["coste"] -= parte
                if abs(p["titulos"]) < 1e-6:
                    p["titulos"], p["coste"] = 0.0, 0.0
                if o["tipo"] == "traspaso_salida":
                    bolsa_coste += parte
                    bolsa_importe += o["importe"]
                else:
                    p["realizado"] += o["importe"] - parte
                    if not usa_caja:
                        flujos["retirado"] += o["importe"]
        for o in dia:
            if o["tipo"] in ENTRAN and o["activo_id"]:
                p = pos[o["activo_id"]]
                p["titulos"] += o["titulos"] or 0
                externo = -o["importe"]
                if o["tipo"] == "traspaso_entrada" and bolsa_importe > 0.005:
                    usado = min(externo, bolsa_importe)
                    coste = bolsa_coste * usado / bolsa_importe
                    p["coste"] += coste
                    bolsa_coste -= coste
                    bolsa_importe -= usado
                    externo -= usado
                if externo > 0.005:  # compra, o traspaso desde fuera
                    p["coste"] += externo
                    if not usa_caja:
                        flujos["aportado"] += externo
            elif not o["activo_id"] and (o["tipo"] in ENTRAN or o["tipo"] in SALEN):
                # crowdfunding sin activo concreto: compra/venta de tokens = aportación/retirada
                if o["tipo"] in ENTRAN:
                    flujos["aportado"] += -o["importe"]
                else:
                    flujos["retirado"] += o["importe"]
            if o["tipo"] == "aportacion":
                flujos["aportado"] += o["importe"]
            elif o["tipo"] in ("retirada", "devolucion"):
                flujos["retirado"] += -o["importe"]
            elif o["tipo"] in RENDIMIENTOS:
                flujos["rendimientos"] += o["importe"]
            if usa_caja:
                flujos["caja"] += o["importe"]
    return {k: v for k, v in pos.items() if v["titulos"] > 1e-6 or v["realizado"]}, flujos


def _valoracion(con, cuenta_id, fecha, fuente=None):
    q = "SELECT fecha, valor, fuente FROM valoraciones WHERE cuenta_id = ? AND fecha <= ?"
    args = [cuenta_id, fecha]
    if fuente:
        q += " AND fuente = ?"
        args.append(fuente)
    r = con.execute(q + " ORDER BY fecha DESC LIMIT 1", args).fetchone()
    return dict(r) if r else None


def valor_cuenta(con, c, fecha) -> dict:
    """Valor de la cuenta c (fila de cuentas) en la fecha. Devuelve valor, desglose y fecha del dato."""
    if c["tipo"] == "broker":
        pos, flujos = posiciones(con, c["id"], fecha)
        hay_ops = con.execute("SELECT 1 FROM operaciones WHERE cuenta_id = ? AND fecha <= ? LIMIT 1",
                              (c["id"], fecha)).fetchone()
        excel = _valoracion(con, c["id"], fecha, "excel")
        if not hay_ops:
            if excel:
                return {"valor": excel["valor"], "fecha_dato": excel["fecha"], "fuente": "excel", "desglose": {}}
            return {"valor": 0.0, "fecha_dato": None, "fuente": None, "desglose": {}}
        desglose, completo, fecha_dato = {}, True, None
        limite = (date.fromisoformat(fecha) - timedelta(days=MAX_ANTIGUEDAD_PRECIO)).isoformat()
        for aid, p in pos.items():
            if p["titulos"] <= 1e-6:
                continue
            precio, fprecio = precio_en(con, aid, fecha)
            if precio is None or fprecio < limite:
                completo = False  # se usa el último precio conocido; se avisa en la app
            desglose[aid] = p["titulos"] * (precio or 0)
            fecha_dato = max(fecha_dato or "", fprecio or "")
        valor = sum(desglose.values()) + flujos["caja"]
        return {"valor": valor, "fecha_dato": fecha_dato, "fuente": "calculado",
                "desglose": desglose, "caja": flujos["caja"], "completo": completo}

    v = _valoracion(con, c["id"], fecha)
    base = v["valor"] if v else 0.0
    if c["tipo"] in ("crowdfunding", "manual"):
        desde = v["fecha"] if v else "0000"
        for o in con.execute("SELECT tipo, importe FROM operaciones WHERE cuenta_id = ? AND fecha > ? "
                             "AND fecha <= ?", (c["id"], desde, fecha)):
            if o["tipo"] in ENTRAN or o["tipo"] == "aportacion":
                base += abs(o["importe"])
            elif o["tipo"] in SALEN or o["tipo"] in ("retirada", "devolucion"):
                base -= abs(o["importe"])
    signo = -1 if c["tipo"] == "deuda" else 1
    return {"valor": signo * base, "fecha_dato": v["fecha"] if v else None,
            "fuente": v["fuente"] if v else None, "desglose": {}}


def cuentas_activas(con):
    return [dict(r) for r in con.execute("SELECT * FROM cuentas WHERE activa = 1 ORDER BY tipo, nombre")]


def fechas_mensuales(con, hasta=None):
    """Fin de cada mes desde que hay saldos bancarios (antes el patrimonio estaría incompleto) hasta hoy."""
    hasta = hasta or date.today().isoformat()
    r = con.execute("SELECT MIN(v.fecha) AS f FROM valoraciones v JOIN cuentas c ON c.id = v.cuenta_id "
                    "WHERE c.tipo = 'banco'").fetchone()
    if not r or not r["f"]:
        return [hasta]
    meses = pd.date_range(pd.Timestamp(r["f"]) + pd.offsets.MonthEnd(0), hasta, freq="ME")
    fechas = [m.strftime("%Y-%m-%d") for m in meses]
    if not fechas or fechas[-1] != hasta:
        fechas.append(hasta)
    return fechas


def reparto(con, fecha):
    """Valor por cuenta, por categoría y por tipo de inversión en una fecha."""
    activos = {r["id"]: dict(r) for r in con.execute("SELECT * FROM activos")}
    cuentas, por_cat, por_tipo = [], defaultdict(float), defaultdict(float)
    for c in cuentas_activas(con):
        v = valor_cuenta(con, c, fecha)
        cuentas.append({**c, **{k: v[k] for k in ("valor", "fecha_dato", "fuente")}})
        if v.get("desglose"):
            for aid, val in v["desglose"].items():
                a = activos[aid]
                por_cat[a["categoria"] or "Otros"] += val
                por_tipo[a["tipo_inversion"] or "Otros"] += val
            por_cat["Liquidez"] += v.get("caja", 0)
        else:
            por_cat[c["categoria"] or ("Deuda" if c["tipo"] == "deuda" else "Otros")] += v["valor"]
            if c["tipo_inversion"]:
                por_tipo[c["tipo_inversion"]] += v["valor"]
            elif c["tipo"] == "broker":
                por_tipo["Otros"] += v["valor"]
    return cuentas, dict(por_cat), dict(por_tipo)


def evolucion(con, hasta=None):
    filas = []
    for f in fechas_mensuales(con, hasta):
        cuentas, por_cat, _ = reparto(con, f)
        filas.append({"fecha": f, "total": round(sum(c["valor"] for c in cuentas), 2),
                      **{k: round(v, 2) for k, v in por_cat.items()}})
    return filas


def detalle_broker(con, cuenta_id, fecha=None):
    fecha = fecha or date.today().isoformat()
    pos, flujos = posiciones(con, cuenta_id, fecha)
    activos = {r["id"]: dict(r) for r in con.execute("SELECT * FROM activos")}
    filas = []
    for aid, p in pos.items():
        precio, fprecio = precio_en(con, aid, fecha)
        valor = p["titulos"] * (precio or 0)
        a = activos[aid]
        filas.append({
            "activo_id": aid, "nombre": a["nombre"], "isin": a["isin"], "ticker": a["ticker"],
            "categoria": a["categoria"], "tipo_inversion": a["tipo_inversion"],
            "titulos": round(p["titulos"], 6), "precio": precio, "fecha_precio": fprecio,
            "valor": round(valor, 2), "coste": round(p["coste"], 2),
            "ganancia": round(valor - p["coste"], 2) if p["titulos"] > 1e-6 else 0,
            "rentabilidad": round((valor / p["coste"] - 1) * 100, 2) if p["coste"] > 0 and p["titulos"] > 1e-6 else None,
            "realizado": round(p["realizado"], 2),
        })
    filas.sort(key=lambda x: -x["valor"])
    return {"posiciones": filas, "flujos": {k: round(v, 2) for k, v in flujos.items()}}


def es_inversion(c) -> bool:
    return c["tipo"] in ("broker", "crowdfunding") or (
        c["tipo"] == "manual" and c["categoria"] in ("Renta Variable", "Renta Fija"))


def inversiones(con, fecha=None):
    """Todo lo invertido: posiciones, ganancias, rentas cobradas y evolución valor vs. aportado."""
    fecha = fecha or date.today().isoformat()
    cuentas = [c for c in cuentas_activas(con) if es_inversion(c)]
    activos = {r["id"]: dict(r) for r in con.execute("SELECT * FROM activos")}

    def foto(f):
        """Valor y aportado neto de todas las inversiones en la fecha f."""
        valor = aportado = 0.0
        for c in cuentas:
            v = valor_cuenta(con, c, f)["valor"]
            valor += v
            if c["tipo"] == "broker":
                _, fl = posiciones(con, c["id"], f)
                aportado += fl["aportado"] - fl["retirado"]
            else:
                aportado += v  # crowdfunding y manuales: se valoran a lo aportado
        return valor, aportado

    posiciones_abiertas, vendidas = [], []
    latente = realizada = cobrado = cobrado_fuera = 0.0  # cobrado_fuera: rentas que no quedan en la cuenta
    for c in cuentas:
        if c["tipo"] == "broker":
            d = detalle_broker(con, c["id"], fecha)
            cobrado += d["flujos"]["rendimientos"]
            for p in d["posiciones"]:
                realizada += p["realizado"]
                if p["titulos"] > 1e-6:
                    latente += p["ganancia"]
                    posiciones_abiertas.append({**p, "cuenta": c["nombre"], "cuenta_id": c["id"]})
                elif p["realizado"]:
                    vendidas.append({"nombre": p["nombre"], "cuenta": c["nombre"], "realizado": p["realizado"]})
            if d["flujos"]["caja"]:
                posiciones_abiertas.append({
                    "nombre": f"Efectivo en {c['nombre']}", "cuenta": c["nombre"], "cuenta_id": c["id"],
                    "categoria": "Liquidez", "tipo_inversion": "Efectivo", "valor": round(d["flujos"]["caja"], 2),
                    "coste": round(d["flujos"]["caja"], 2), "ganancia": 0, "rentabilidad": None, "titulos": None,
                    "precio": None, "fecha_precio": None, "realizado": 0})
        else:
            v = valor_cuenta(con, c, fecha)
            _, fl = posiciones(con, c["id"], fecha)
            cobrado += fl["rendimientos"]
            cobrado_fuera += fl["rendimientos"]
            posiciones_abiertas.append({
                "nombre": c["nombre"], "cuenta": c["entidad"] or c["nombre"], "cuenta_id": c["id"],
                "categoria": c["categoria"], "tipo_inversion": c["tipo_inversion"], "valor": round(v["valor"], 2),
                "coste": round(v["valor"], 2), "ganancia": 0, "rentabilidad": None, "titulos": None,
                "precio": None, "fecha_precio": v["fecha_dato"], "realizado": 0,
                "rentas": round(fl["rendimientos"], 2), "manual": True})

    total = sum(p["valor"] for p in posiciones_abiertas) or 1
    for p in posiciones_abiertas:
        p["peso"] = round(p["valor"] / total * 100, 1)
    posiciones_abiertas.sort(key=lambda p: -p["valor"])

    serie = []
    for f in fechas_mensuales(con, fecha):
        v, a = foto(f)
        serie.append({"fecha": f, "valor": round(v, 2), "aportado": round(a, 2)})
    valor_hoy, aportado_hoy = (serie[-1]["valor"], serie[-1]["aportado"]) if serie else foto(fecha)
    mes = None
    if len(serie) >= 2:
        prev = serie[-2]
        mes = round((valor_hoy - prev["valor"]) - (aportado_hoy - prev["aportado"]), 2)

    ingresos = defaultdict(float)
    ids = [c["id"] for c in cuentas]
    if ids:
        for r in con.execute(
                f"SELECT substr(fecha, 1, 7) AS mes, SUM(importe) AS total FROM operaciones WHERE cuenta_id IN "
                f"({','.join('?' * len(ids))}) AND tipo IN ('dividendo', 'retencion', 'interes', 'renta') "
                f"GROUP BY mes ORDER BY mes", ids):
            ingresos[r["mes"]] = round(r["total"], 2)

    return {
        "fecha": fecha,
        "valor": round(valor_hoy, 2),
        "aportado": round(aportado_hoy, 2),
        # en XTB los dividendos/intereses ya están en el efectivo de la cuenta (dentro del valor)
        "ganancia": round(valor_hoy - aportado_hoy + cobrado_fuera, 2),
        "ganancia_mes": mes,
        "latente": round(latente, 2),
        "realizada": round(realizada, 2),
        "cobrado": round(cobrado, 2),
        "posiciones": posiciones_abiertas,
        "vendidas": sorted(vendidas, key=lambda x: -abs(x["realizado"])),
        "evolucion": serie,
        "ingresos_mensuales": [{"mes": k, "importe": v} for k, v in sorted(ingresos.items())][-12:],
    }



def leer_plan(con):
    fila = con.execute("SELECT valor FROM estado WHERE clave = 'emergencia_objetivo'").fetchone()
    filas = con.execute("SELECT bloque, tipo, porcentaje FROM plan_reparto ORDER BY bloque, porcentaje DESC").fetchall()
    return {
        "emergencia": {"objetivo": float(fila["valor"]) if fila else 0.0,
                       "componentes": [{"tipo": f["tipo"], "porcentaje": f["porcentaje"]} for f in filas if f["bloque"] == "emergencia"]},
        "inversion": [{"tipo": f["tipo"], "porcentaje": f["porcentaje"]} for f in filas if f["bloque"] == "inversion"],
    }


def cuadre_plan(con, fecha=None):
    """1) Aparta el fondo de emergencia (liquidez y fondo monetario hasta su objetivo).
    2) Compara el resto del patrimonio con los porcentajes del plan."""
    fecha = fecha or date.today().isoformat()
    _, por_cat, por_tipo = reparto(con, fecha)
    valores = dict(por_tipo)
    valores["Cuenta corriente"] = por_cat.get("Liquidez", 0.0)  # la liquidez es la "cuenta corriente" del plan
    plan = leer_plan(con)

    em = plan["emergencia"]
    componentes = []
    for c in em["componentes"]:
        objetivo = em["objetivo"] * c["porcentaje"]
        cubierto = max(0.0, min(valores.get(c["tipo"], 0.0), objetivo))
        valores[c["tipo"]] = valores.get(c["tipo"], 0.0) - cubierto
        componentes.append({"tipo": c["tipo"], "objetivo": round(objetivo, 2), "real": round(cubierto, 2)})
    cubierto_total = sum(c["real"] for c in componentes)

    objetivos = {f["tipo"]: f["porcentaje"] for f in plan["inversion"]}
    base = sum(v for v in valores.values() if v > 0)
    filas = []
    for t in sorted(set(objetivos) | {k for k, v in valores.items() if abs(v) > 0.5},
                    key=lambda t: -max(valores.get(t, 0), objetivos.get(t, 0) * base)):
        v = max(valores.get(t, 0.0), 0.0)
        obj = objetivos.get(t, 0.0)
        filas.append({"tipo": t, "valor": round(v, 2), "real": round(v / base * 100, 1) if base else 0,
                      "objetivo": round(obj * 100, 1), "importe_objetivo": round(obj * base, 2),
                      "diferencia": round(obj * base - v, 2), "fuera_del_plan": t not in objetivos})
    return {
        "emergencia": {"objetivo": em["objetivo"], "cubierto": round(cubierto_total, 2), "componentes": componentes},
        "resto": {"base": round(base, 2), "filas": filas,
                  "suma_objetivos": round(sum(objetivos.values()) * 100, 1)},
    }
