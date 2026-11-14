# App de finanzas (versión nueva)

Sustituye al dashboard de Streamlit (`app.py`, que sigue funcionando mientras tanto).

- **backend/**: Python (FastAPI + SQLite). Importadores de extractos, cálculos y API.
- **frontend/**: React (Vite + Tailwind + Recharts), pensado para el móvil (se puede instalar en la pantalla de inicio).
- **Datos**: `datos-locales/finanzas.db`. Nunca dentro del repo (`datos-locales/` está excluida).

## Arrancar

```bash
cd backend && uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt
cd ../frontend && npm install && npm run build      # genera frontend/dist
cd ../backend && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8501
```

El backend sirve también el frontend compilado. Para desarrollar el frontend: `npm run dev` (redirige `/api` al 8501).

Carga inicial con los archivos de `datos-locales/ejemplos/`: `.venv/bin/python cargar_ejemplos.py`.

## Fuentes de datos

| Fuente | Archivo | Qué se saca |
|---|---|---|
| XTB | Informe Excel (Cash Operations, Open/Closed Positions) | Compras, ventas, dividendos, intereses, aportaciones; precio actual |
| Inversis (fondos MyInvestor) | `.xls` de operaciones (es HTML) | Suscripciones, reembolsos, traspasos y switches con precio |
| BBVA | Excel de movimientos | Movimientos y saldo |
| Revolut | CSV | Movimientos y saldo |
| Cuenta MyInvestor | CSV | Movimientos (sin saldo: se reconstruye desde el saldo final que se indica) |
| Urbanitae | Excel de inversiones | Capital vivo |
| Equito / Urbanitae | Formulario | Compras/ventas de tokens o aportaciones/devoluciones, y rentas mensuales globales |
| Efectivo, Pluxee, Bleap, Cartera Rock… | Formulario | Valor a mano |
| Excel antiguo | `Excel Finanzas Personales.xlsx` | Histórico mensual (saldos a principio de mes) y Plan de reparto |

Reimportar un archivo (o uno que se solape) no duplica: cada movimiento/operación tiene una huella única.

## Criterios de cálculo

- **Patrimonio** = suma del valor de cada cuenta en la fecha (último dato conocido).
- **Brókers**: títulos × último precio conocido (+ efectivo en XTB). Coste medio; los traspasos entre fondos conservan el coste aunque salida y entrada se liquiden en días distintos.
- **Crowdfunding**: se valora a capital invertido. Las rentas e intereses **no** suben el valor: se cuentan como rendimiento cobrado.
- **Gastos**: las transferencias entre cuentas propias no cuentan. Categorías por reglas de texto, que se crean desde la app tocando un movimiento.

- **Precios**: `app/precios.py`. Hilo en segundo plano dentro de la app: cada 30 min mira si la última actualización tiene más de 6 h; si es así, descarga de Yahoo (fondos por ISIN → código Morningstar, XTB por ticker traducido), pasa a EUR y valida contra precios reales (±10 %). También `POST /api/precios/actualizar`.
- **Plan**: tabla `plan_reparto` (bloques `emergencia` e `inversion`) + `estado.emergencia_objetivo`. Cuadre en `calculos.cuadre_plan`.

## Pendiente

- Carga de históricos completos de los bancos (corrige los saltos de abril-mayo 2026, que salen del Excel mensual).
