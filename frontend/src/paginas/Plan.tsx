import { useEffect, useState } from 'react'
import { ArrowLeft, Plus, X } from 'lucide-react'
import { api, CATEGORIAS, numero, type PlanEditable } from '../api'
import { Cargando, ErrorCaja, Tarjeta } from '../ui'

type Fila = { tipo: string; pct: string }
const aFilas = (xs: { tipo: string; porcentaje: number }[]): Fila[] =>
  xs.map(x => ({ tipo: x.tipo, pct: String(Math.round(x.porcentaje * 1000) / 10).replace('.', ',') }))
const campo = 'rounded-lg bg-s2 border border-line px-2.5 py-2 text-base text-tx outline-none focus:border-acc'

export default function Plan({ volver }: { volver: () => void }) {
  const [p, setP] = useState<PlanEditable>()
  const [objetivo, setObjetivo] = useState('')
  const [em, setEm] = useState<Fila[]>([])
  const [inv, setInv] = useState<Fila[]>([])
  const [error, setError] = useState<string>()
  const [estado, setEstado] = useState<string>()

  useEffect(() => {
    api.plan().then(r => {
      setP(r); setObjetivo(String(r.emergencia.objetivo)); setEm(aFilas(r.emergencia.componentes)); setInv(aFilas(r.inversion))
    }).catch(e => setError(String(e.message ?? e)))
  }, [])
  if (error) return <ErrorCaja error={error} />
  if (!p) return <Cargando />

  const suma = (fs: Fila[]) => fs.reduce((s, f) => s + (numero(f.pct) || 0), 0)
  const guardar = async () => {
    setEstado(undefined)
    try {
      await api.guardarPlan({
        emergencia_objetivo: numero(objetivo) || 0,
        emergencia: em.filter(f => f.tipo).map(f => ({ tipo: f.tipo, porcentaje: (numero(f.pct) || 0) / 100 })),
        inversion: inv.filter(f => f.tipo).map(f => ({ tipo: f.tipo, porcentaje: (numero(f.pct) || 0) / 100 })),
      })
      setEstado('Guardado ✓')
    } catch (e) { setEstado('⚠️ ' + (e as Error).message) }
  }

  return (
    <div className="space-y-4">
      <button onClick={volver} className="flex items-center gap-1 text-sm text-tx2 pt-2"><ArrowLeft className="w-4 h-4" /> Volver</button>
      <h1 className="text-xl font-semibold">Plan de reparto</h1>

      <Tarjeta titulo="Fondo de emergencia">
        <label className="text-xs text-tx3">Importe objetivo (€)
          <input inputMode="decimal" className={`${campo} w-full mt-1`} value={objetivo} onChange={e => setObjetivo(e.target.value)} />
        </label>
        <p className="text-xs text-tx3 mt-3 mb-2">Dónde se guarda (debe sumar 100 %):</p>
        <ListaFilas filas={em} setFilas={setEm} tipos={p.tipos} />
        <Suma valor={suma(em)} />
      </Tarjeta>

      <Tarjeta titulo="Resto del patrimonio">
        <p className="text-xs text-tx3 mb-2">Reparto de todo lo demás. "Cuenta corriente" es la liquidez que sobra fuera del fondo de emergencia.</p>
        <ListaFilas filas={inv} setFilas={setInv} tipos={p.tipos} />
        <Suma valor={suma(inv)} />
      </Tarjeta>

      <div className="sticky bottom-20 z-10">
        <button onClick={guardar} className="w-full rounded-lg bg-acc px-3 py-3 text-sm font-medium text-white shadow-lg">Guardar plan</button>
        {estado && <p className="text-xs text-tx2 mt-2 text-center bg-bg/90 rounded">{estado}</p>}
      </div>

      <Clasificacion p={p} />
    </div>
  )
}

function ListaFilas({ filas, setFilas, tipos }: { filas: Fila[]; setFilas: (f: Fila[]) => void; tipos: string[] }) {
  const cambiar = (i: number, f: Partial<Fila>) => setFilas(filas.map((x, j) => j === i ? { ...x, ...f } : x))
  return (
    <div className="space-y-2">
      {filas.map((f, i) => (
        <div key={i} className="flex gap-2 items-center">
          <select className={`${campo} flex-1 min-w-0`} value={f.tipo} onChange={e => cambiar(i, { tipo: e.target.value })}>
            <option value="">Elige…</option>
            {[...new Set([...tipos, f.tipo])].filter(Boolean).map(t => <option key={t}>{t}</option>)}
          </select>
          <div className="relative w-24 shrink-0">
            <input inputMode="decimal" className={`${campo} w-full pr-6 text-right`} value={f.pct} onChange={e => cambiar(i, { pct: e.target.value })} />
            <span className="absolute right-2 top-1/2 -translate-y-1/2 text-tx3 text-sm">%</span>
          </div>
          <button aria-label="Quitar" onClick={() => setFilas(filas.filter((_, j) => j !== i))} className="p-2 text-tx3"><X className="w-4 h-4" /></button>
        </div>
      ))}
      <button onClick={() => setFilas([...filas, { tipo: '', pct: '0' }])} className="inline-flex items-center gap-1 text-sm text-acc pt-1">
        <Plus className="w-4 h-4" /> Añadir tipo
      </button>
    </div>
  )
}

function Suma({ valor }: { valor: number }) {
  const ok = Math.abs(valor - 100) < 0.5
  return <div className={`num text-sm text-right mt-2 ${ok ? 'text-good' : 'text-warn'}`}>Suma: {valor.toLocaleString('es-ES', { maximumFractionDigits: 1 })} % {ok ? '✓' : '(debe ser 100 %)'}</div>
}

/** A qué tipo del plan pertenece cada cosa que tienes. */
function Clasificacion({ p }: { p: PlanEditable }) {
  const [items, setItems] = useState(p.clasificacion)
  const [nuevoTipo, setNuevoTipo] = useState<Record<string, string>>({})
  const guardar = async (i: number, tipo: string, categoria?: string) => {
    const it = items[i]
    await api.clasificar({ clase: it.clase, id: it.id, tipo_inversion: tipo, categoria })
    setItems(items.map((x, j) => j === i ? { ...x, tipo_inversion: tipo, categoria: categoria ?? x.categoria } : x))
  }
  return (
    <Tarjeta titulo="Qué es cada activo">
      <p className="text-xs text-tx3 mb-3">Tipo del plan y categoría (para el reparto) de lo que tienes ahora. Se guarda al cambiarlo.</p>
      <ul className="divide-y divide-line">
        {items.map((it, i) => (
          <li key={`${it.clase}-${it.id}`} className="py-2.5">
            <div className="text-sm text-tx mb-1.5">{it.nombre}</div>
            <div className="grid grid-cols-2 gap-2">
              <select className={`${campo} text-sm`} value={nuevoTipo[i] !== undefined ? '__nuevo' : (it.tipo_inversion ?? '')}
                onChange={e => e.target.value === '__nuevo' ? setNuevoTipo({ ...nuevoTipo, [i]: '' }) : guardar(i, e.target.value)}>
                {[...new Set([...p.tipos, it.tipo_inversion ?? ''])].filter(t => t && t !== 'Cuenta corriente').map(t => <option key={t}>{t}</option>)}
                <option value="__nuevo">+ Tipo nuevo…</option>
              </select>
              <select className={`${campo} text-sm`} value={it.categoria ?? ''} onChange={e => guardar(i, it.tipo_inversion ?? '', e.target.value)}>
                {CATEGORIAS.map(c => <option key={c}>{c}</option>)}
              </select>
            </div>
            {nuevoTipo[i] !== undefined && (
              <div className="flex gap-2 mt-2">
                <input placeholder="Nombre del tipo" className={`${campo} flex-1 text-sm`} value={nuevoTipo[i]}
                  onChange={e => setNuevoTipo({ ...nuevoTipo, [i]: e.target.value })} />
                <button className="rounded-lg bg-acc px-3 text-sm text-white" disabled={!nuevoTipo[i]?.trim()}
                  onClick={async () => { await guardar(i, nuevoTipo[i].trim()); const n = { ...nuevoTipo }; delete n[i]; setNuevoTipo(n) }}>OK</button>
              </div>
            )}
          </li>
        ))}
      </ul>
    </Tarjeta>
  )
}
