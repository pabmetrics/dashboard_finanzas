"""Carga los archivos de ejemplo de datos-locales/ejemplos en una base de datos de prueba.

Uso: SALDO_MYINVESTOR=1234.56 CUENTA_BBVA="BBVA ..." .venv/bin/python cargar_ejemplos.py [ruta_db]
(los datos personales van por variables de entorno, nunca en el código)
"""
import json
import os
import sys
from pathlib import Path

from app.db import RAIZ, conectar
from app.importers.bancos import importar_bbva, importar_myinvestor_cuenta, importar_revolut
from app.importers.inversis import importar_inversis
from app.importers.otros import importar_excel_antiguo, importar_urbanitae, inicializar
from app.importers.xtb import importar_xtb

EJ = RAIZ / "datos-locales" / "ejemplos"


def uno(patron):
    encontrados = sorted(EJ.glob(patron))
    if not encontrados:
        raise SystemExit(f"No encuentro {patron} en {EJ}")
    return encontrados[0]


def main():
    db = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "datos-locales" / "finanzas.db"
    con = conectar(db)
    inicializar(con)
    res = {
        "excel": importar_excel_antiguo(con, uno("Excel Finanzas*.xlsx")),
        "xtb": importar_xtb(con, uno("EUR_*.xlsx")),
        "inversis": importar_inversis(con, uno("salida*.xls")),
        "revolut": importar_revolut(con, uno("*-*-*-*-*.csv")),
        "bbva": importar_bbva(con, uno("??-??-????.xlsx"), os.environ.get("CUENTA_BBVA", "BBVA")),
        "myinvestor": importar_myinvestor_cuenta(
            con, uno("Movimientos Mi Cuenta*.csv"),
            saldo_final=float(os.environ["SALDO_MYINVESTOR"]) if os.environ.get("SALDO_MYINVESTOR") else None),
        "urbanitae": importar_urbanitae(con, uno("ProjectTableInvestments.xlsx")),
    }
    con.commit()
    print(json.dumps(res, indent=1, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
