"""API de la app de finanzas. Arranque: .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8501"""
import shutil
import tempfile
from datetime import date
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import json
import threading

from app import calculos, precios
from app.db import RAIZ, conectar, guardar_valoracion, insertar
from app.importers import bancos, inversis, otros, xtb
from app.importers.comun import categorizar, huella

app = FastAPI(title="Finanzas")


def db():
    """Una conexión por petición; se cierra al terminar."""
    con = conectar()
    try:
        yield con
    finally:
        con.close()


@app.on_event("startup")
def preparar():
    con = conectar()
    otros.inicializar(con)
    con.commit()
    con.close()
    # precios: se comprueba cada 30 min y se actualiza si la última vez fue hace más de 6 h
    threading.Thread(target=precios.bucle_diario, args=(conectar,), daemon=True).start()


@app.get("/api/inversiones")
def inversiones(con=Depends(db)):
    res = calculos.inversiones(con)
    res["cuadre"] = calculos.cuadre_plan(con)
    est = dict(con.execute("SELECT clave, valor FROM estado").fetchall())
    res["precios"] = {"actualizados": est.get("precios_actualizados"),
                      "resultado": json.loads(est["precios_resultado"]) if est.get("precios_resultado") else None}
    return res


class FilaPlan(BaseModel):
    tipo: str
    porcentaje: float  # en tanto por uno (0.25 = 25 %)


class Plan(BaseModel):
    emergencia_objetivo: float
    emergencia: list[FilaPlan]
    inversion: list[FilaPlan]


@app.get("/api/plan")
def ver_plan(con=Depends(db)):
    tipos = set(otros.TIPOS_INVERSION)
    tipos |= {r[0] for r in con.execute("SELECT tipo_inversion FROM activos WHERE tipo_inversion IS NOT NULL")}
    tipos |= {r[0] for r in con.execute("SELECT tipo_inversion FROM cuentas WHERE tipo_inversion IS NOT NULL")}
    tipos |= {r[0] for r in con.execute("SELECT tipo FROM plan_reparto")}
    hoy = date.today().isoformat()
    clasificacion = []
    for a in con.execute("SELECT a.id, a.nombre, a.tipo_inversion, a.categoria FROM activos a ORDER BY a.nombre"):
        clasificacion.append({"clase": "activo", "id": a["id"], "nombre": a["nombre"],
                              "tipo_inversion": a["tipo_inversion"], "categoria": a["categoria"]})
    for c in calculos.cuentas_activas(con):
        if c["tipo"] in ("crowdfunding", "manual") and calculos.es_inversion(c):
            clasificacion.append({"clase": "cuenta", "id": c["id"], "nombre": c["nombre"],
                                  "tipo_inversion": c["tipo_inversion"], "categoria": c["categoria"]})
    # solo lo que se tiene ahora (lo vendido no hace falta clasificarlo)
    vivos = set()
    for c in calculos.cuentas_activas(con):
        if c["tipo"] == "broker":
            pos, _ = calculos.posiciones(con, c["id"], hoy)
            vivos |= {aid for aid, p in pos.items() if p["titulos"] > 1e-6}
    clasificacion = [x for x in clasificacion if x["clase"] == "cuenta" or x["id"] in vivos]
    return calculos.leer_plan(con) | {"tipos": sorted(tipos), "clasificacion": clasificacion}


@app.put("/api/plan")
def guardar_plan(p: Plan, con=Depends(db)):
    for bloque, filas in (("emergencia", p.emergencia), ("inversion", p.inversion)):
        suma = sum(f.porcentaje for f in filas)
        if filas and abs(suma - 1) > 0.005:
            raise HTTPException(400, f"Los porcentajes de {'emergencia' if bloque == 'emergencia' else 'inversión'} "
                                     f"suman {suma * 100:.1f} %, deben sumar 100 %")
    con.execute("DELETE FROM plan_reparto")
    for bloque, filas in (("emergencia", p.emergencia), ("inversion", p.inversion)):
        for f in filas:
            if f.tipo.strip():
                con.execute("INSERT OR REPLACE INTO plan_reparto (bloque, tipo, porcentaje) VALUES (?, ?, ?)",
                            (bloque, f.tipo.strip(), f.porcentaje))
    con.execute("INSERT OR REPLACE INTO estado (clave, valor) VALUES ('emergencia_objetivo', ?)",
                (str(p.emergencia_objetivo),))
    con.commit()
    return {"ok": True}


class Clasificacion(BaseModel):
    clase: str  # activo | cuenta
    id: int
    tipo_inversion: str
    categoria: str | None = None


@app.put("/api/clasificacion")
def clasificar(c: Clasificacion, con=Depends(db)):
    """Cambia a qué tipo del plan (y categoría) pertenece un activo o una cuenta."""
    tabla = {"activo": "activos", "cuenta": "cuentas"}.get(c.clase)
    if not tabla:
        raise HTTPException(400, "Clase no válida")
    con.execute(f"UPDATE {tabla} SET tipo_inversion = ? WHERE id = ?", (c.tipo_inversion.strip(), c.id))
    if c.categoria:
        con.execute(f"UPDATE {tabla} SET categoria = ? WHERE id = ?", (c.categoria, c.id))
    con.commit()
    return {"ok": True}


@app.post("/api/precios/actualizar")
def actualizar_precios():
    r = precios.actualizar_seguro(conectar)
    if r is None:
        raise HTTPException(409, "Ya se están actualizando, prueba en un minuto")
    return r


def _mes_anterior(evol):
    """Último punto de fin de mes anterior al actual."""
    return evol[-2] if len(evol) >= 2 else None


@app.get("/api/resumen")
def resumen(fecha: str | None = None, con=Depends(db)):
    fecha = fecha or date.today().isoformat()
    cuentas, por_cat, por_tipo = calculos.reparto(con, fecha)
    total = sum(c["valor"] for c in cuentas)
    evol = calculos.evolucion(con, fecha)
    ant = _mes_anterior(evol)

    aportado = rendimiento_cobrado = valor_inversiones = 0.0
    for c in cuentas:
        if c["tipo"] in ("broker", "crowdfunding"):
            _, fl = calculos.posiciones(con, c["id"], fecha)
            valor_inversiones += c["valor"]
            if c["tipo"] == "broker":
                aportado += fl["aportado"] - fl["retirado"]
            else:
                aportado += c["valor"]  # el crowdfunding se valora a coste
            rendimiento_cobrado += fl["rendimientos"]

    em = calculos.cuadre_plan(con, fecha)["emergencia"]
    hoy = date.today()
    return {
        "fecha": fecha,
        "patrimonio": round(total, 2),
        "variacion_mes": round(total - ant["total"], 2) if ant else None,
        "fecha_mes_anterior": ant["fecha"] if ant else None,
        "liquidez": round(por_cat.get("Liquidez", 0), 2),
        "inversiones": round(valor_inversiones, 2),
        "ganancia_inversiones": round(valor_inversiones - aportado, 2),
        "rendimientos_cobrados": round(rendimiento_cobrado, 2),
        "por_categoria": {k: round(v, 2) for k, v in por_cat.items() if abs(v) > 0.005},
        "emergencia": em,
        "cuentas": [
            {k: c[k] for k in ("id", "nombre", "tipo", "entidad", "subtipo", "categoria", "fecha_dato", "fuente")}
            | {"valor": round(c["valor"], 2),
               "dias_sin_actualizar": (hoy - date.fromisoformat(c["fecha_dato"])).days if c["fecha_dato"] else None}
            for c in cuentas
        ],
    }


@app.get("/api/evolucion")
def evolucion(con=Depends(db)):
    return calculos.evolucion(con)


@app.get("/api/cuentas/{cuenta_id}")
def detalle_cuenta(cuenta_id: int, con=Depends(db)):
    c = con.execute("SELECT * FROM cuentas WHERE id = ?", (cuenta_id,)).fetchone()
    if not c:
        raise HTTPException(404, "No existe la cuenta")
    c = dict(c)
    hoy = date.today().isoformat()
    res = {"cuenta": c, **calculos.valor_cuenta(con, c, hoy)}
    res.pop("desglose", None)
    if c["tipo"] == "broker":
        res |= calculos.detalle_broker(con, cuenta_id, hoy)
    res["historico"] = [{"fecha": f, "valor": round(calculos.valor_cuenta(con, c, f)["valor"], 2)}
                        for f in calculos.fechas_mensuales(con, hoy)]
    res["operaciones"] = [dict(r) for r in con.execute(
        "SELECT o.fecha, o.tipo, o.titulos, o.precio, o.importe, a.nombre AS activo FROM operaciones o "
        "LEFT JOIN activos a ON a.id = o.activo_id WHERE o.cuenta_id = ? ORDER BY o.fecha DESC, o.id DESC LIMIT 200",
        (cuenta_id,))]
    res["valoraciones"] = [dict(r) for r in con.execute(
        "SELECT fecha, valor, fuente FROM valoraciones WHERE cuenta_id = ? ORDER BY fecha DESC LIMIT 60", (cuenta_id,))]
    return res


class NuevaCuenta(BaseModel):
    nombre: str
    tipo: str = "manual"        # manual | crowdfunding | banco | deuda
    categoria: str = "Liquidez"  # Liquidez | Renta Variable | Renta Fija
    subtipo: str | None = None


@app.post("/api/cuentas")
def crear_cuenta(c: NuevaCuenta, con=Depends(db)):
    """Activo nuevo de valor manual (efectivo, saldo en otra plataforma, crowdfunding, deuda...)."""
    nombre = c.nombre.strip()
    if not nombre:
        raise HTTPException(400, "Falta el nombre")
    if c.tipo not in ("manual", "crowdfunding", "banco", "deuda"):
        raise HTTPException(400, f"Tipo no válido: {c.tipo}")
    if con.execute("SELECT 1 FROM cuentas WHERE nombre = ?", (nombre,)).fetchone():
        raise HTTPException(400, "Ya existe una cuenta con ese nombre")
    tipo_inv = "Crowlending inmobiliario" if c.tipo == "crowdfunding" else None
    cur = con.execute("INSERT INTO cuentas (nombre, tipo, subtipo, categoria, tipo_inversion) VALUES (?, ?, ?, ?, ?)",
                      (nombre, c.tipo, c.subtipo, "Deuda" if c.tipo == "deuda" else c.categoria, tipo_inv))
    con.commit()
    return {"ok": True, "id": cur.lastrowid}


@app.get("/api/manual")
def manual():
    return {"texto": (RAIZ / "docs" / "manual.md").read_text(encoding="utf-8")}


class Valoracion(BaseModel):
    cuenta_id: int
    fecha: str
    valor: float


@app.post("/api/valoraciones")
def nueva_valoracion(v: Valoracion, con=Depends(db)):
    """Valor a mano de una cuenta (efectivo, Pluxee, Cartera Rock, saldo de otra plataforma...)."""
    guardar_valoracion(con, v.cuenta_id, v.fecha, v.valor, "manual")
    con.commit()
    return {"ok": True}


class Operacion(BaseModel):
    cuenta_id: int
    fecha: str
    tipo: str          # aportacion | retirada | compra | venta | renta | interes | comision
    importe: float     # siempre positivo; el signo lo pone el tipo
    titulos: float | None = None
    nota: str | None = None


SIGNO = {"aportacion": -1, "compra": -1, "comision": -1, "retirada": 1, "venta": 1, "devolucion": 1,
         "renta": 1, "interes": 1, "dividendo": 1}


@app.post("/api/operaciones")
def nueva_operacion(o: Operacion, con=Depends(db)):
    """Operaciones manuales de crowdfunding (Equito: compra/venta de tokens y rentas; Urbanitae:
    aportación/devolución e intereses)."""
    if o.tipo not in SIGNO:
        raise HTTPException(400, f"Tipo no válido: {o.tipo}")
    importe = SIGNO[o.tipo] * abs(o.importe)
    insertar(con, "operaciones", cuenta_id=o.cuenta_id, fecha=o.fecha, tipo=o.tipo, titulos=o.titulos,
             importe=importe, nota=o.nota,
             huella=huella("manual", o.cuenta_id, o.fecha, o.tipo, importe, o.nota, date.today().isoformat()))
    con.commit()
    return {"ok": True}


IMPORTADORES = {
    "xtb": lambda con, ruta, cuenta, saldo: xtb.importar_xtb(con, ruta),
    "inversis": lambda con, ruta, cuenta, saldo: inversis.importar_inversis(con, ruta),
    "revolut": lambda con, ruta, cuenta, saldo: bancos.importar_revolut(con, ruta),
    "bbva": lambda con, ruta, cuenta, saldo: bancos.importar_bbva(con, ruta, cuenta or "BBVA"),
    "myinvestor": lambda con, ruta, cuenta, saldo: bancos.importar_myinvestor_cuenta(con, ruta, saldo),
    "urbanitae": lambda con, ruta, cuenta, saldo: otros.importar_urbanitae(con, ruta),
}


@app.post("/api/importar/{origen}")
def importar(origen: str, archivo: UploadFile = File(...), cuenta: str | None = Form(None),
             saldo_final: float | None = Form(None), con=Depends(db)):
    if origen not in IMPORTADORES:
        raise HTTPException(400, f"Origen no válido: {origen}")
    with tempfile.TemporaryDirectory() as tmp:
        ruta = Path(tmp) / Path(archivo.filename or "archivo").name
        with open(ruta, "wb") as f:
            shutil.copyfileobj(archivo.file, f)
        try:
            res = IMPORTADORES[origen](con, ruta, cuenta, saldo_final)
        except Exception as e:  # el archivo no tiene el formato esperado
            con.rollback()
            raise HTTPException(400, f"No he podido leer el archivo: {e}")
    con.commit()
    return res


class Regla(BaseModel):
    patron: str
    categoria: str


@app.get("/api/categorias")
def categorias():
    return otros.CATEGORIAS


@app.post("/api/reglas")
def nueva_regla(r: Regla, con=Depends(db)):
    """Crea (o cambia) una regla y recategoriza los movimientos que encajan con ella."""
    patron = r.patron.strip().lower()
    if len(patron) < 3:
        raise HTTPException(400, "El texto de la regla es demasiado corto")
    tipo = "Transferencia" if r.categoria in ("Transferencia interna", "Inversión") else None
    con.execute("INSERT INTO reglas (patron, categoria, tipo) VALUES (?, ?, ?) ON CONFLICT(patron) "
                "DO UPDATE SET categoria = excluded.categoria, tipo = excluded.tipo", (patron, r.categoria, tipo))
    n = 0
    for m in con.execute("SELECT id, concepto, detalle, importe FROM movimientos").fetchall():
        if patron in f"{m['concepto'] or ''} {m['detalle'] or ''}".lower():
            cat, t = categorizar(con, f"{m['concepto'] or ''} {m['detalle'] or ''}", m["importe"])
            con.execute("UPDATE movimientos SET categoria = ?, tipo = ? WHERE id = ?", (cat, t, m["id"]))
            n += 1
    con.commit()
    return {"ok": True, "movimientos_actualizados": n}


@app.get("/api/movimientos")
def movimientos(mes: str | None = None, con=Depends(db)):
    mes = mes or date.today().strftime("%Y-%m")
    filas = [dict(r) for r in con.execute(
        "SELECT m.fecha, m.concepto, m.detalle, m.importe, m.categoria, m.tipo, c.nombre AS cuenta "
        "FROM movimientos m JOIN cuentas c ON c.id = m.cuenta_id WHERE substr(m.fecha, 1, 7) = ? "
        "ORDER BY m.fecha DESC, m.id DESC", (mes,))]
    por_cat = {}
    for f in filas:
        if f["tipo"] == "Gasto":
            k = f["categoria"] or "Sin categoría"
            por_cat[k] = round(por_cat.get(k, 0) - f["importe"], 2)
    return {
        "mes": mes,
        "ingresos": round(sum(f["importe"] for f in filas if f["tipo"] == "Ingreso"), 2),
        "gastos": round(-sum(f["importe"] for f in filas if f["tipo"] == "Gasto"), 2),
        "gastos_por_categoria": dict(sorted(por_cat.items(), key=lambda x: -x[1])),
        "movimientos": filas,
        "meses": [r[0] for r in con.execute(
            "SELECT DISTINCT substr(fecha, 1, 7) FROM movimientos ORDER BY 1 DESC")],
    }


# Frontend ya compilado (npm run build) servido desde la misma app
DIST = RAIZ / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{ruta:path}")
    def spa(ruta: str):
        fichero = DIST / ruta
        if ruta and fichero.is_file() and DIST in fichero.resolve().parents:
            return FileResponse(fichero)
        # index.html sin caché: así el móvil coge siempre la última versión de la app
        return FileResponse(DIST / "index.html", headers={"Cache-Control": "no-cache"})
