import { useEffect, useState } from 'react'
import { AlertTriangle, ChevronRight, Plus } from 'lucide-react'
import { api, CATEGORIAS, COLOR_CATEGORIA, fmt, fmtSigno, type PuntoEvolucion, type Resumen } from '../api'
import { BarraReparto, Cargando, Dato, ErrorCaja, FondoEmergencia, GraficoEvolucion, Tarjeta } from '../ui'

const GRUPOS: Record<string, string> = {
  banco: 'Cuentas', broker: 'Inversiones', crowdfunding: 'Crowdfunding', manual: 'Otros activos', deuda: 'Deudas',
}
const DIAS_AVISO = 35

export default function Inicio({ abrirCuenta }: { abrirCuenta: (id: number) => void }) {
  const [r, setR] = useState<Resumen>()
  const [evol, setEvol] = useState<PuntoEvolucion[]>()
  const [error, setError] = useState<string>()

  useEffect(() => {
    Promise.all([api.resumen(), api.evolucion()]).then(([a, b]) => { setR(a); setEvol(b) })
      .catch(e => setError(String(e.message ?? e)))
  }, [])

  if (error) return <ErrorCaja error={error} />
  if (!r || !evol) return <Cargando />

  const varPct = r.variacion_mes != null && r.patrimonio - r.variacion_mes !== 0
    ? r.variacion_mes / (r.patrimonio - r.variacion_mes) * 100 : null
  const aportadoInv = r.inversiones - r.ganancia_inversiones
  const grupos = Object.keys(GRUPOS).map(g => ({ g, cuentas: r.cuentas.filter(c => c.tipo === g) }))
    .filter(x => x.cuentas.length)

  return (
    <div className="space-y-4">
      <header className="pt-2">
        <div className="text-sm text-tx3">Patrimonio neto</div>
        <div className="num text-4xl font-semibold tracking-tight">{fmt(r.patrimonio)}</div>
        {r.variacion_mes != null && (
          <div className={`num text-sm mt-0.5 ${r.variacion_mes >= 0 ? 'text-good' : 'text-bad'}`}>
            {r.variacion_mes >= 0 ? '▲' : '▼'} {fmtSigno(r.variacion_mes)}
            {varPct != null && ` (${varPct.toLocaleString('es-ES', { maximumFractionDigits: 1 })} %)`}
            <span className="text-tx3"> este mes</span>
          </div>
        )}
      </header>

      <div className="grid grid-cols-3 gap-2">
        <Dato etiqueta="Liquidez" valor={fmt(r.liquidez)} />
        <Dato etiqueta="Invertido" valor={fmt(r.inversiones)} />
        <Dato etiqueta="Ganancia inv." valor={fmtSigno(r.ganancia_inversiones)}
          detalle={aportadoInv > 0 ? `${(r.ganancia_inversiones / aportadoInv * 100).toLocaleString('es-ES', { maximumFractionDigits: 1 })} %` : undefined}
          tono={r.ganancia_inversiones >= 0 ? 'bueno' : 'malo'} />
      </div>

      <Tarjeta titulo="Evolución">
        <GraficoEvolucion datos={evol} />
      </Tarjeta>

      <Tarjeta titulo="Fondo de emergencia">
        <FondoEmergencia e={r.emergencia} />
      </Tarjeta>

      <Tarjeta titulo="Reparto">
        <BarraReparto partes={CATEGORIAS.filter(c => r.por_categoria[c])
          .map(c => ({ nombre: c, valor: r.por_categoria[c], color: COLOR_CATEGORIA[c] }))} />
      </Tarjeta>

      {grupos.map(({ g, cuentas }) => (
        <Tarjeta key={g} titulo={GRUPOS[g]}
          accion={<span className="num text-sm text-tx">{fmt(cuentas.reduce((s, c) => s + c.valor, 0))}</span>}>
          <ul className="-mx-2">
            {cuentas.map(c => {
              const viejo = c.dias_sin_actualizar != null && c.dias_sin_actualizar > DIAS_AVISO
              return (
                <li key={c.id}>
                  <button onClick={() => abrirCuenta(c.id)}
                    className="w-full flex items-center justify-between gap-2 rounded-lg px-2 py-2.5 hover:bg-s2 active:bg-s2 text-left">
                    <span className="min-w-0">
                      <span className="block text-sm text-tx truncate">{c.nombre}</span>
                      <span className={`block text-xs ${viejo ? 'text-warn' : 'text-tx3'}`}>
                        {viejo && <AlertTriangle className="inline w-3 h-3 mr-1 -mt-0.5" />}
                        {!c.fecha_dato ? 'Sin datos' : c.dias_sin_actualizar === 0 ? 'Actualizado hoy' : c.dias_sin_actualizar === 1 ? 'Dato de ayer' : `Dato de hace ${c.dias_sin_actualizar} días`}
                        {c.fuente === 'excel' && ' · Excel antiguo'}
                      </span>
                    </span>
                    <span className="flex items-center gap-1 shrink-0">
                      <span className="num text-sm text-tx">{fmt(c.valor)}</span>
                      <ChevronRight className="w-4 h-4 text-tx3" />
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>
        </Tarjeta>
      ))}

      <NuevoActivo alCrear={id => abrirCuenta(id)} />
    </div>
  )
}

const TIPOS_NUEVO = [
  { id: 'manual', nombre: 'Otro activo' }, { id: 'crowdfunding', nombre: 'Crowdfunding' },
  { id: 'banco', nombre: 'Cuenta bancaria' }, { id: 'deuda', nombre: 'Deuda' },
]

function NuevoActivo({ alCrear }: { alCrear: (id: number) => void }) {
  const [abierto, setAbierto] = useState(false)
  const [nombre, setNombre] = useState('')
  const [tipo, setTipo] = useState('manual')
  const [categoria, setCategoria] = useState('Liquidez')
  const [error, setError] = useState<string>()
  if (!abierto) return (
    <button onClick={() => setAbierto(true)}
      className="w-full flex items-center justify-center gap-2 rounded-2xl border border-dashed border-line py-3 text-sm text-tx2">
      <Plus className="w-4 h-4" /> Añadir activo
    </button>
  )
  const crear = async () => {
    try {
      const r = await api.crearCuenta({ nombre, tipo, categoria: tipo === 'crowdfunding' ? 'Renta Fija' : tipo === 'banco' ? 'Liquidez' : categoria })
      alCrear(r.id)
    } catch (e) { setError((e as Error).message) }
  }
  const campo = 'w-full rounded-lg bg-s2 border border-line px-3 py-2.5 text-base text-tx outline-none focus:border-acc'
  return (
    <Tarjeta titulo="Añadir activo">
      <input placeholder="Nombre (p. ej. Depósito Trade Republic)" className={campo} value={nombre} onChange={e => setNombre(e.target.value)} />
      <div className="grid grid-cols-2 gap-1.5 mt-2">
        {TIPOS_NUEVO.map(t => (
          <button key={t.id} onClick={() => setTipo(t.id)}
            className={`rounded-lg border px-2 py-2 text-sm ${t.id === tipo ? 'border-acc bg-s2 text-tx' : 'border-line text-tx2'}`}>{t.nombre}</button>
        ))}
      </div>
      {tipo === 'manual' && (
        <select className={`${campo} mt-2`} value={categoria} onChange={e => setCategoria(e.target.value)}>
          {CATEGORIAS.map(c => <option key={c}>{c}</option>)}
        </select>
      )}
      <div className="grid grid-cols-2 gap-2 mt-2">
        <button className="rounded-lg border border-line py-2.5 text-sm text-tx2" onClick={() => setAbierto(false)}>Cancelar</button>
        <button className="rounded-lg bg-acc py-2.5 text-sm font-medium text-white disabled:opacity-50" disabled={!nombre.trim()} onClick={crear}>Crear</button>
      </div>
      {error && <p className="text-xs text-bad mt-2">{error}</p>}
    </Tarjeta>
  )
}
