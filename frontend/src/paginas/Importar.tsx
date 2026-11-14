import { useEffect, useState } from 'react'
import { api, numero } from '../api'
import { Tarjeta } from '../ui'

const ORIGENES = [
  { id: 'xtb', nombre: 'XTB', ayuda: 'Informe Excel completo (Cash Operations, Open/Closed Positions).' },
  { id: 'inversis', nombre: 'Fondos (Inversis)', ayuda: 'El .xls de operaciones de Inversis.' },
  { id: 'bbva', nombre: 'BBVA', ayuda: 'Excel de movimientos. Elige a qué cuenta corresponde.', entidad: 'BBVA' },
  { id: 'revolut', nombre: 'Revolut', ayuda: 'CSV de movimientos.' },
  { id: 'myinvestor', nombre: 'Cuenta MyInvestor', ayuda: 'CSV de movimientos. El saldo se calcula sumando todos los movimientos guardados. Saldo final: déjalo vacío, salvo que te pida cuadrar el saldo (por ejemplo, si el primer archivo no empieza en la apertura de la cuenta).', saldo: true },
  { id: 'urbanitae', nombre: 'Urbanitae', ayuda: 'Excel de inversiones (ProjectTableInvestments). Fija el capital vivo.' },
]

export default function Importar() {
  const [origen, setOrigen] = useState(ORIGENES[0].id)
  const [archivo, setArchivo] = useState<File | null>(null)
  const [cuenta, setCuenta] = useState('')
  const [cuentasBanco, setCuentasBanco] = useState<{ nombre: string; entidad: string | null }[]>([])
  useEffect(() => { api.resumen().then(r => setCuentasBanco(r.cuentas.filter(c => c.tipo === 'banco'))).catch(() => {}) }, [])
  const [saldo, setSaldo] = useState('')
  const [res, setRes] = useState<string>()
  const [ocupado, setOcupado] = useState(false)
  const o = ORIGENES.find(x => x.id === origen)!
  const opciones = o.entidad ? cuentasBanco.filter(c => (c.entidad ?? '').toUpperCase() === o.entidad || c.nombre.toUpperCase().startsWith(o.entidad)).map(c => c.nombre) : []
  const cuentaElegida = opciones.includes(cuenta) ? cuenta : opciones[0]

  const subir = async () => {
    if (!archivo) return
    setOcupado(true); setRes(undefined)
    try {
      const r = await api.importar(origen, archivo, { cuenta: o.entidad ? cuentaElegida : undefined, saldo_final: saldo ? String(numero(saldo)) : undefined })
      setRes(resumir(r))
    } catch (e) { setRes('⚠️ ' + (e as Error).message) }
    setOcupado(false)
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold pt-2">Importar extracto</h1>
      <Tarjeta>
        <div className="grid grid-cols-2 gap-2">
          {ORIGENES.map(x => (
            <button key={x.id} onClick={() => { setOrigen(x.id); setRes(undefined) }}
              className={`rounded-lg border px-3 py-2.5 text-sm text-left ${x.id === origen ? 'border-acc bg-s2 text-tx' : 'border-line text-tx2'}`}>
              {x.nombre}
            </button>
          ))}
        </div>
        <p className="text-xs text-tx3 mt-3">{o.ayuda}</p>
        {o.entidad && opciones.length > 0 && (
          <select className="mt-3 w-full rounded-lg bg-s2 border border-line px-3 py-2.5" value={cuentaElegida} onChange={e => setCuenta(e.target.value)}>
            {opciones.map(c => <option key={c}>{c}</option>)}
          </select>
        )}
        {o.saldo && (
          <input inputMode="decimal" placeholder="Saldo final € (opcional)" value={saldo} onChange={e => setSaldo(e.target.value)}
            className="mt-3 w-full rounded-lg bg-s2 border border-line px-3 py-2.5" />
        )}
        <label className="mt-3 block rounded-lg border border-dashed border-line px-3 py-4 text-center text-sm text-tx2">
          {archivo ? archivo.name : 'Elegir archivo'}
          <input type="file" className="hidden" onChange={e => setArchivo(e.target.files?.[0] ?? null)} />
        </label>
        <button disabled={!archivo || ocupado} onClick={subir}
          className="mt-3 w-full rounded-lg bg-acc px-3 py-2.5 text-sm font-medium text-white disabled:opacity-50">
          {ocupado ? 'Importando…' : 'Importar'}
        </button>
        {res && <pre className="mt-3 whitespace-pre-wrap text-xs text-tx2">{res}</pre>}
      </Tarjeta>
      <p className="text-xs text-tx3 px-1">Puedes subir el mismo archivo o uno que se solape: los movimientos repetidos se ignoran.</p>
    </div>
  )
}

function resumir(r: Record<string, unknown>): string {
  const n = (r.nuevos ?? r.nuevas) as number | undefined
  const leidos = (r.leidos ?? r.operaciones_leidas) as number | undefined
  if (n !== undefined) return `✓ ${n} nuevos de ${leidos} leídos${r.desde ? ` (${r.desde} → ${r.hasta})` : ''}.`
    + (r.saldo_actual != null ? `\nSaldo calculado: ${r.saldo_actual} €.` : '')
  if (r.capital_vivo !== undefined) return `✓ Capital vivo en Urbanitae: ${r.capital_vivo} € en ${r.proyectos_vivos} proyectos.`
  return '✓ ' + JSON.stringify(r)
}
