export type Cuenta = {
  id: number; nombre: string; tipo: string; entidad: string | null; subtipo: string | null
  categoria: string | null; valor: number; fecha_dato: string | null; fuente: string | null
  dias_sin_actualizar: number | null
}
export type Resumen = {
  fecha: string; patrimonio: number; variacion_mes: number | null; fecha_mes_anterior: string | null
  liquidez: number; inversiones: number; ganancia_inversiones: number; rendimientos_cobrados: number
  por_categoria: Record<string, number>
  emergencia: Emergencia
  cuentas: Cuenta[]
}
export type Emergencia = { objetivo: number; cubierto: number; componentes: { tipo: string; objetivo: number; real: number }[] }
export type FilaCuadre = { tipo: string; valor: number; real: number; objetivo: number; importe_objetivo: number; diferencia: number; fuera_del_plan: boolean }
export type PlanEditable = {
  emergencia: { objetivo: number; componentes: { tipo: string; porcentaje: number }[] }
  inversion: { tipo: string; porcentaje: number }[]
  tipos: string[]
  clasificacion: { clase: 'activo' | 'cuenta'; id: number; nombre: string; tipo_inversion: string | null; categoria: string | null }[]
}
export type PuntoEvolucion = { fecha: string; total: number; [categoria: string]: number | string }
export type Posicion = {
  activo_id: number; nombre: string; isin: string | null; ticker: string | null; categoria: string
  tipo_inversion: string; titulos: number; precio: number | null; fecha_precio: string | null
  valor: number; coste: number; ganancia: number; rentabilidad: number | null; realizado: number
}
export type DetalleCuenta = {
  cuenta: { id: number; nombre: string; tipo: string; entidad: string | null; subtipo: string | null }
  valor: number; fecha_dato: string | null; fuente: string | null; caja?: number
  posiciones?: Posicion[]
  flujos?: { aportado: number; retirado: number; rendimientos: number; caja: number }
  historico: { fecha: string; valor: number }[]
  operaciones: { fecha: string; tipo: string; titulos: number | null; precio: number | null; importe: number; activo: string | null }[]
  valoraciones: { fecha: string; valor: number; fuente: string }[]
}
export type PosicionInv = {
  nombre: string; cuenta: string; cuenta_id: number; categoria: string | null; tipo_inversion: string | null
  valor: number; coste: number; ganancia: number; rentabilidad: number | null; titulos: number | null
  precio: number | null; fecha_precio: string | null; peso: number; rentas?: number; manual?: boolean
}
export type Inversiones = {
  fecha: string; valor: number; aportado: number; ganancia: number; ganancia_mes: number | null
  latente: number; realizada: number; cobrado: number
  posiciones: PosicionInv[]
  vendidas: { nombre: string; cuenta: string; realizado: number }[]
  evolucion: { fecha: string; valor: number; aportado: number }[]
  ingresos_mensuales: { mes: string; importe: number }[]
  cuadre: { emergencia: Emergencia; resto: { base: number; suma_objetivos: number; filas: FilaCuadre[] } }
  precios: { actualizados: string | null; resultado: { actualizados: { activo: string }[]; fallidos: { activo: string; motivo: string }[] } | null }
}
export type Movimientos = {
  mes: string; ingresos: number; gastos: number; gastos_por_categoria: Record<string, number>
  movimientos: { fecha: string; concepto: string; detalle: string | null; importe: number; categoria: string | null; tipo: string; cuenta: string }[]
  meses: string[]
}

async function pedir<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init)
  const datos = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(datos.detail ?? `Error ${r.status}`)
  return datos as T
}

export const api = {
  resumen: () => pedir<Resumen>('/api/resumen'),
  evolucion: () => pedir<PuntoEvolucion[]>('/api/evolucion'),
  cuenta: (id: number) => pedir<DetalleCuenta>(`/api/cuentas/${id}`),
  movimientos: (mes?: string) => pedir<Movimientos>(`/api/movimientos${mes ? `?mes=${mes}` : ''}`),
  valoracion: (cuenta_id: number, fecha: string, valor: number) =>
    pedir('/api/valoraciones', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cuenta_id, fecha, valor }) }),
  operacion: (o: { cuenta_id: number; fecha: string; tipo: string; importe: number; titulos?: number; nota?: string }) =>
    pedir('/api/operaciones', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(o) }),
  crearCuenta: (c: { nombre: string; tipo: string; categoria: string }) =>
    pedir<{ id: number }>('/api/cuentas', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(c) }),
  inversiones: () => pedir<Inversiones>('/api/inversiones'),
  actualizarPrecios: () => pedir<{ nuevos_precios: number; fallidos: unknown[] }>('/api/precios/actualizar', { method: 'POST' }),
  plan: () => pedir<PlanEditable>('/api/plan'),
  guardarPlan: (p: { emergencia_objetivo: number; emergencia: { tipo: string; porcentaje: number }[]; inversion: { tipo: string; porcentaje: number }[] }) =>
    pedir('/api/plan', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(p) }),
  clasificar: (c: { clase: string; id: number; tipo_inversion: string; categoria?: string }) =>
    pedir('/api/clasificacion', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(c) }),
  manual: () => pedir<{ texto: string }>('/api/manual'),
  categorias: () => pedir<string[]>('/api/categorias'),
  regla: (patron: string, categoria: string) =>
    pedir<{ movimientos_actualizados: number }>('/api/reglas', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ patron, categoria }) }),
  importar: (origen: string, archivo: File, extra: { cuenta?: string; saldo_final?: string }) => {
    const f = new FormData()
    f.append('archivo', archivo)
    if (extra.cuenta) f.append('cuenta', extra.cuenta)
    if (extra.saldo_final) f.append('saldo_final', extra.saldo_final)
    return pedir<Record<string, unknown>>(`/api/importar/${origen}`, { method: 'POST', body: f })
  },
}

const eur = new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })
const eur2 = new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR', minimumFractionDigits: 2, maximumFractionDigits: 2 })
export const fmt = (v: number, decimales = false) => (decimales ? eur2 : eur).format(v)
export const fmtSigno = (v: number, decimales = false) => (v > 0 ? '+' : '') + fmt(v, decimales)
export const pct = (v: number) => `${v > 0 ? '+' : ''}${v.toLocaleString('es-ES', { maximumFractionDigits: 1 })} %`
const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
export const mesCorto = (iso: string) => `${MESES[+iso.slice(5, 7) - 1]} ${iso.slice(2, 4)}`
export const fechaCorta = (iso: string) => `${+iso.slice(8, 10)} ${MESES[+iso.slice(5, 7) - 1]}`
export const hoy = () => new Date().toISOString().slice(0, 10)

// Color por categoría: sigue a la entidad, nunca al orden.
export const COLOR_CATEGORIA: Record<string, string> = {
  'Liquidez': 'var(--series-1)',
  'Renta Variable': 'var(--series-2)',
  'Renta Fija': 'var(--series-3)',
  'Otros': 'var(--text-muted)', // neutro: activos fuera de liquidez e inversiones
}
export const CATEGORIAS = Object.keys(COLOR_CATEGORIA)

/** Lee importes escritos a mano: "1.234,56", "1234,56", "1234.56" o "1.234" (miles). */
export function numero(t: string): number {
  const s = t.trim().replace(/[€\s]/g, '')
  if (s.includes(',')) return parseFloat(s.replace(/\./g, '').replace(',', '.'))
  if (/^-?\d{1,3}(\.\d{3})+$/.test(s)) return parseFloat(s.replace(/\./g, ''))
  return parseFloat(s)
}
