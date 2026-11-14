"""Base de datos SQLite de la app de finanzas.

La base de datos vive en datos-locales/ (excluida de git): nunca dentro del repo.

Modelo:
- cuentas: dónde está el dinero (banco, bróker, plataforma de crowdfunding, activo manual).
- activos: lo que se tiene dentro de un bróker (fondo, ETF, acción...).
- movimientos: movimientos de cuentas bancarias (gastos e ingresos).
- operaciones: compras, ventas, traspasos, dividendos, rentas, aportaciones...
- precios: precio de cada activo por fecha.
- valoraciones: valor de una cuenta en una fecha (saldo bancario, valor manual, histórico del Excel).
- reglas: reglas para categorizar movimientos por texto del concepto.
"""
import os
import sqlite3
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DB_PATH = Path(os.environ.get("FINANZAS_DB", RAIZ / "datos-locales" / "finanzas.db"))

ESQUEMA = """
CREATE TABLE IF NOT EXISTS cuentas (
    id INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE,
    tipo TEXT NOT NULL,            -- banco | broker | crowdfunding | manual | deuda
    entidad TEXT,                  -- BBVA, XTB, Inversis, Equito...
    subtipo TEXT,                  -- Cuenta nómina, Cuenta remunerada, Otros...
    titular TEXT DEFAULT 'Conjunta',
    categoria TEXT,                -- para el reparto: Liquidez, Renta Fija, Renta Variable...
    tipo_inversion TEXT,           -- para comparar con el Plan: Crowlending inmobiliario...
    activa INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS activos (
    id INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL,
    isin TEXT UNIQUE,
    ticker TEXT UNIQUE,
    clase TEXT,                    -- fondo | etf | etc | accion | cripto
    categoria TEXT,                -- Renta Variable | Renta Fija | ...
    tipo_inversion TEXT,           -- Fondo indexado, Oro, Acciones value... (como en el Plan)
    moneda TEXT DEFAULT 'EUR',
    ticker_precio TEXT             -- símbolo para descargar precios (si difiere)
);

CREATE TABLE IF NOT EXISTS movimientos (
    id INTEGER PRIMARY KEY,
    cuenta_id INTEGER NOT NULL REFERENCES cuentas(id),
    fecha TEXT NOT NULL,
    concepto TEXT,
    detalle TEXT,
    importe REAL NOT NULL,
    saldo REAL,
    categoria TEXT,
    tipo TEXT,                     -- Ingreso | Gasto | Transferencia
    huella TEXT NOT NULL UNIQUE    -- evita duplicados al reimportar
);

CREATE TABLE IF NOT EXISTS operaciones (
    id INTEGER PRIMARY KEY,
    cuenta_id INTEGER NOT NULL REFERENCES cuentas(id),
    activo_id INTEGER REFERENCES activos(id),
    fecha TEXT NOT NULL,
    tipo TEXT NOT NULL,            -- compra | venta | traspaso_entrada | traspaso_salida | dividendo
                                   -- | retencion | interes | renta | aportacion | retirada | comision | devolucion
    titulos REAL,
    precio REAL,
    importe REAL NOT NULL,         -- en EUR, positivo = entra dinero en la cuenta, negativo = sale
    nota TEXT,
    huella TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS precios (
    activo_id INTEGER NOT NULL REFERENCES activos(id),
    fecha TEXT NOT NULL,
    precio REAL NOT NULL,
    fuente TEXT,
    PRIMARY KEY (activo_id, fecha)
);

CREATE TABLE IF NOT EXISTS valoraciones (
    cuenta_id INTEGER NOT NULL REFERENCES cuentas(id),
    fecha TEXT NOT NULL,
    valor REAL NOT NULL,
    fuente TEXT,                   -- manual | extracto | excel
    PRIMARY KEY (cuenta_id, fecha)
);

CREATE TABLE IF NOT EXISTS reglas (
    id INTEGER PRIMARY KEY,
    patron TEXT NOT NULL UNIQUE,   -- texto a buscar en el concepto (sin distinguir mayúsculas)
    categoria TEXT NOT NULL,
    tipo TEXT
);

-- Saldo conocido de una cuenta en una fecha (para cuentas cuyo extracto no trae saldo).
CREATE TABLE IF NOT EXISTS anclas (
    cuenta_id INTEGER NOT NULL REFERENCES cuentas(id),
    fecha TEXT NOT NULL,
    saldo REAL NOT NULL,
    PRIMARY KEY (cuenta_id, fecha)
);

CREATE TABLE IF NOT EXISTS estado (
    clave TEXT PRIMARY KEY,
    valor TEXT
);

-- Plan de reparto en dos bloques: 'emergencia' (reparto del fondo de emergencia, cuyo importe
-- objetivo está en estado.emergencia_objetivo) e 'inversion' (reparto de todo lo demás).
-- 'Cuenta corriente' representa la liquidez.
CREATE TABLE IF NOT EXISTS plan_reparto (
    bloque TEXT NOT NULL,
    tipo TEXT NOT NULL,
    porcentaje REAL NOT NULL,
    PRIMARY KEY (bloque, tipo)
);

CREATE TABLE IF NOT EXISTS plan (
    tipo_inversion TEXT PRIMARY KEY,
    porcentaje REAL NOT NULL
);
"""


def conectar(path: Path | None = None) -> sqlite3.Connection:
    path = Path(path or DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, check_same_thread=False, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(ESQUEMA)
    return con


def cuenta(con, nombre, tipo, **campos) -> int:
    """Devuelve el id de la cuenta, creándola si no existe."""
    fila = con.execute("SELECT id FROM cuentas WHERE nombre = ?", (nombre,)).fetchone()
    if fila:
        return fila["id"]
    cols = ["nombre", "tipo", *campos.keys()]
    cur = con.execute(
        f"INSERT INTO cuentas ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
        (nombre, tipo, *campos.values()),
    )
    return cur.lastrowid


def activo(con, nombre, isin=None, ticker=None, **campos) -> int:
    """Devuelve el id del activo (buscado por ISIN o ticker), creándolo si no existe."""
    for col, val in (("isin", isin), ("ticker", ticker)):
        if val:
            fila = con.execute(f"SELECT id FROM activos WHERE {col} = ?", (val,)).fetchone()
            if fila:
                return fila["id"]
    cols = ["nombre", "isin", "ticker", *campos.keys()]
    cur = con.execute(
        f"INSERT INTO activos ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
        (nombre, isin, ticker, *campos.values()),
    )
    return cur.lastrowid


def insertar(con, tabla, **campos) -> bool:
    """INSERT que ignora duplicados (por huella / clave primaria). Devuelve True si insertó."""
    cols = list(campos)
    cur = con.execute(
        f"INSERT OR IGNORE INTO {tabla} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
        tuple(campos.values()),
    )
    return cur.rowcount > 0


def guardar_valoracion(con, cuenta_id, fecha, valor, fuente):
    con.execute(
        "INSERT INTO valoraciones (cuenta_id, fecha, valor, fuente) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(cuenta_id, fecha) DO UPDATE SET valor = excluded.valor, fuente = excluded.fuente",
        (cuenta_id, fecha, valor, fuente),
    )


def guardar_precio(con, activo_id, fecha, precio, fuente):
    con.execute(
        "INSERT INTO precios (activo_id, fecha, precio, fuente) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(activo_id, fecha) DO UPDATE SET precio = excluded.precio, fuente = excluded.fuente",
        (activo_id, fecha, precio, fuente),
    )
