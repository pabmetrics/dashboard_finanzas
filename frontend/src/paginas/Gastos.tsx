import { useEffect, useState } from 'react'
import { useCategorias } from '../categorias'
import { api, fechaCorta, fmt, fmtSigno, mesCorto, type Movimientos } from '../api'
import { Cargando, Dato, ErrorCaja, Tarjeta } from '../ui'

export default function Gastos() {
  const [mes, setMes] = useState<string>()
  const [d, setD] = useState<Movimientos>()
  const [error, setError] = useState<string>()
  const [abierto, setAbierto] = useState<number>()
  const [recarga, setRecarga] = useState(0)

  useEffect(() => {
    api.movimientos(mes).then(r => {
      // si el mes actual no tiene movimientos, saltar al último que tenga
      if (!mes && r.movimientos.length === 0 && r.meses.length) setMes(r.meses[0])
      else setD(r)
    }).catch(e => setError(String(e.message ?? e)))
  }, [mes, recarga])

  if (error) return <ErrorCaja error={error} />
  if (!d) return <Cargando />
  const max = Math.max(...Object.values(d.gastos_por_categoria), 1)
  const ahorro = d.ingresos - d.gastos

  return (
    <div className="space-y-4">
      <header className="pt-2 flex items-center justify-between">
        <h1 className="text-xl font-semibold">Gastos e ingresos</h1>
        <select className="rounded-lg bg-s2 border border-line px-2 py-1.5 text-sm" value={d.mes}
          onChange={e => setMes(e.target.value)}>
          {(d.meses.includes(d.mes) ? d.meses : [d.mes, ...d.meses]).map(m => <option key={m} value={m}>{mesCorto(m + '-01')}</option>)}
        </select>
      </header>
      <div className="grid grid-cols-3 gap-2">
        <Dato etiqueta="Ingresos" valor={fmt(d.ingresos)} />
        <Dato etiqueta="Gastos" valor={fmt(d.gastos)} />
        <Dato etiqueta="Ahorro" valor={fmtSigno(ahorro)} tono={ahorro >= 0 ? 'bueno' : 'malo'}
          detalle={d.ingresos ? `${Math.round(ahorro / d.ingresos * 100)} %` : undefined} />
      </div>
      <p className="text-xs text-tx3 -mt-2">No cuenta las transferencias entre tus cuentas.</p>

      <Tarjeta titulo="Gasto por categoría">
        <div className="space-y-2">
          {Object.entries(d.gastos_por_categoria).map(([cat, v]) => (
            <div key={cat}>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-tx2">{cat}</span><span className="num text-tx">{fmt(v)}</span>
              </div>
              <div className="h-2 rounded-full bg-s2">
                <div className="h-full rounded-full" style={{ width: `${v / max * 100}%`, background: 'var(--series-2)' }} />
              </div>
            </div>
          ))}
        </div>
      </Tarjeta>

      <Tarjeta titulo="Movimientos">
        <ul className="divide-y divide-line">
          {d.movimientos.map((m, i) => (
            <li key={i} className="py-2 text-sm">
              <button className="w-full flex justify-between gap-3 text-left" onClick={() => setAbierto(abierto === i ? undefined : i)}>
                <div className="min-w-0">
                  <div className="text-tx truncate">{m.concepto}{m.detalle && <span className="text-tx3"> · {m.detalle}</span>}</div>
                  <div className="text-xs text-tx3">{fechaCorta(m.fecha)} · {m.cuenta} · <span className={m.categoria ? '' : 'text-warn'}>{m.categoria ?? 'Sin categoría'}</span></div>
                </div>
                <span className={`num shrink-0 ${m.importe > 0 ? 'text-good' : 'text-tx'}`}>{fmtSigno(m.importe, true)}</span>
              </button>
              {abierto === i && <Categorizar concepto={m.concepto} alGuardar={() => { setAbierto(undefined); setRecarga(x => x + 1) }} />}
            </li>
          ))}
        </ul>
      </Tarjeta>
    </div>
  )
}

/** Crea una regla: los movimientos cuyo concepto contenga el texto pasan a la categoría elegida. */
function Categorizar({ concepto, alGuardar }: { concepto: string; alGuardar: () => void }) {
  const categorias = useCategorias()
  // propuesta: el concepto sin números finales (p. ej. "GRUPO SUP AHORRAMAS 950" -> "grupo sup ahorramas")
  const [patron, setPatron] = useState(concepto.toLowerCase().replace(/[*#]\S*/g, '').replace(/[\d\s]+$/g, '').trim())
  const [estado, setEstado] = useState<string>()
  const guardar = async (cat: string) => {
    try {
      const r = await api.regla(patron, cat)
      setEstado(`✓ ${r.movimientos_actualizados} movimientos`)
      setTimeout(alGuardar, 600)
    } catch (e) { setEstado('⚠️ ' + (e as Error).message) }
  }
  return (
    <div className="mt-2 rounded-lg bg-s2 p-2.5">
      <label className="text-xs text-tx3">Cuando el concepto contenga:</label>
      <input value={patron} onChange={e => setPatron(e.target.value)}
        className="mt-1 w-full rounded-md bg-s1 border border-line px-2 py-1.5 text-sm outline-none focus:border-acc" />
      <div className="mt-2 flex flex-wrap gap-1.5">
        {categorias.map(c => (
          <button key={c} onClick={() => guardar(c)} className="rounded-full border border-line px-2.5 py-1 text-xs text-tx2 active:bg-s1">{c}</button>
        ))}
      </div>
      {estado && <p className="text-xs text-tx2 mt-2">{estado}</p>}
    </div>
  )
}
