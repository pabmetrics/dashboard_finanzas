import { useCallback, useEffect, useState } from 'react'
import { ArrowLeft } from 'lucide-react'
import { api, numero, fechaCorta, fmt, fmtSigno, hoy, pct, type DetalleCuenta } from '../api'
import { Cargando, Dato, ErrorCaja, GraficoLinea, Tarjeta } from '../ui'

const NOMBRE_TIPO: Record<string, string> = {
  compra: 'Compra', venta: 'Venta', traspaso_entrada: 'Traspaso (entra)', traspaso_salida: 'Traspaso (sale)',
  dividendo: 'Dividendo', retencion: 'Retención', interes: 'Intereses', renta: 'Renta', aportacion: 'Aportación',
  retirada: 'Retirada', comision: 'Comisión', devolucion: 'Devolución de capital',
}

export default function Cuenta({ id, volver }: { id: number; volver: () => void }) {
  const [d, setD] = useState<DetalleCuenta>()
  const [error, setError] = useState<string>()
  const cargar = useCallback(() => {
    api.cuenta(id).then(setD).catch(e => setError(String(e.message ?? e)))
  }, [id])
  useEffect(cargar, [cargar])

  if (error) return <ErrorCaja error={error} />
  if (!d) return <Cargando />
  const c = d.cuenta
  const crowd = c.tipo === 'crowdfunding'
  const rendimientos = d.flujos?.rendimientos ?? 0

  return (
    <div className="space-y-4">
      <button onClick={volver} className="flex items-center gap-1 text-sm text-tx2 pt-2">
        <ArrowLeft className="w-4 h-4" /> Volver
      </button>
      <header>
        <div className="text-sm text-tx3">{[c.entidad, c.subtipo].filter(Boolean).join(' · ')}</div>
        <h1 className="text-xl font-semibold">{c.nombre}</h1>
        <div className="num text-3xl font-semibold mt-1">{fmt(d.valor, true)}</div>
        {d.fecha_dato && <div className="text-xs text-tx3">Dato del {fechaCorta(d.fecha_dato)}{d.fuente === 'excel' ? ' (Excel antiguo)' : ''}</div>}
      </header>

      {d.flujos && c.tipo === 'broker' && (
        <div className="grid grid-cols-3 gap-2">
          <Dato etiqueta="Aportado neto" valor={fmt(d.flujos.aportado - d.flujos.retirado)} />
          <Dato etiqueta="Ganancia" valor={fmtSigno(d.valor - (d.flujos.aportado - d.flujos.retirado))}
            tono={d.valor - (d.flujos.aportado - d.flujos.retirado) >= 0 ? 'bueno' : 'malo'} />
          <Dato etiqueta="Cobrado" valor={fmt(rendimientos)} detalle="dividendos e intereses" />
        </div>
      )}
      {crowd && (
        <div className="grid grid-cols-2 gap-2">
          <Dato etiqueta="Capital invertido" valor={fmt(d.valor)} />
          <Dato etiqueta="Rentas cobradas" valor={fmt(rendimientos)} tono={rendimientos > 0 ? 'bueno' : undefined}
            detalle={d.valor > 0 && rendimientos ? `${(rendimientos / d.valor * 100).toLocaleString('es-ES', { maximumFractionDigits: 1 })} % del capital` : undefined} />
        </div>
      )}

      {d.historico.length > 1 && <Tarjeta titulo="Evolución"><GraficoLinea datos={d.historico} /></Tarjeta>}

      {d.posiciones && d.posiciones.some(p => p.titulos > 0) && (
        <Tarjeta titulo="Posiciones">
          <ul className="divide-y divide-line">
            {d.posiciones.filter(p => p.titulos > 0).map(p => (
              <li key={p.activo_id} className="py-2.5 flex justify-between gap-3">
                <div className="min-w-0">
                  <div className="text-sm text-tx truncate">{p.nombre}</div>
                  <div className="text-xs text-tx3 num">
                    {p.titulos.toLocaleString('es-ES', { maximumFractionDigits: 4 })} × {p.precio?.toLocaleString('es-ES', { maximumFractionDigits: 4 })} €
                    {p.fecha_precio && ` · ${fechaCorta(p.fecha_precio)}`}
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <div className="num text-sm text-tx">{fmt(p.valor)}</div>
                  <div className={`num text-xs ${p.ganancia >= 0 ? 'text-good' : 'text-bad'}`}>
                    {fmtSigno(p.ganancia)}{p.rentabilidad != null && ` · ${pct(p.rentabilidad)}`}
                  </div>
                </div>
              </li>
            ))}
          </ul>
          {!!d.caja && <div className="flex justify-between text-sm pt-2 border-t border-line">
            <span className="text-tx2">Efectivo en la cuenta</span><span className="num">{fmt(d.caja, true)}</span></div>}
        </Tarjeta>
      )}

      {d.posiciones && d.posiciones.some(p => p.titulos === 0 && p.realizado) && (
        <Tarjeta titulo="Vendido (ganancia realizada)">
          <ul className="divide-y divide-line">
            {d.posiciones.filter(p => p.titulos === 0 && p.realizado).map(p => (
              <li key={p.activo_id} className="py-2 flex justify-between text-sm">
                <span className="text-tx2 truncate">{p.nombre}</span>
                <span className={`num ${p.realizado >= 0 ? 'text-good' : 'text-bad'}`}>{fmtSigno(p.realizado, true)}</span>
              </li>
            ))}
          </ul>
        </Tarjeta>
      )}

      {crowd && <FormDatoMes cuentaId={c.id} alGuardar={cargar} />}
      {(c.tipo === 'manual' || c.tipo === 'banco' || c.tipo === 'deuda') &&
        <FormValor cuentaId={c.id} alGuardar={cargar}
          ayuda={c.tipo === 'deuda' ? 'Importe pendiente, en positivo.' : c.tipo === 'banco' ? 'Saldo de la cuenta (si no la importas).' : undefined} />}

      {d.operaciones.length > 0 && (
        <Tarjeta titulo="Operaciones">
          <ul className="divide-y divide-line">
            {d.operaciones.slice(0, 60).map((o, i) => (
              <li key={i} className="py-2 flex justify-between gap-3 text-sm">
                <div className="min-w-0">
                  <div className="text-tx truncate">{NOMBRE_TIPO[o.tipo] ?? o.tipo}{o.activo && ` · ${o.activo}`}</div>
                  <div className="text-xs text-tx3">{fechaCorta(o.fecha)} {o.fecha.slice(0, 4)}</div>
                </div>
                <span className="num shrink-0 text-tx">{fmtSigno(o.importe, true)}</span>
              </li>
            ))}
          </ul>
        </Tarjeta>
      )}
    </div>
  )
}

const campo = 'w-full rounded-lg bg-s2 border border-line px-3 py-2.5 text-base text-tx outline-none focus:border-acc'
const boton = 'w-full rounded-lg bg-acc px-3 py-2.5 text-sm font-medium text-white disabled:opacity-50'

function FormValor({ cuentaId, alGuardar, ayuda }: { cuentaId: number; alGuardar: () => void; ayuda?: string }) {
  const [fecha, setFecha] = useState(hoy())
  const [valor, setValor] = useState('')
  const [estado, setEstado] = useState<string>()
  const guardar = async () => {
    try {
      await api.valoracion(cuentaId, fecha, numero(valor))
      setValor(''); setEstado('Guardado ✓'); alGuardar()
    } catch (e) { setEstado(String((e as Error).message)) }
  }
  return (
    <Tarjeta titulo="Actualizar valor">
      {ayuda && <p className="text-xs text-tx3 mb-2">{ayuda}</p>}
      <div className="grid grid-cols-2 gap-2">
        <input type="date" className={campo} value={fecha} onChange={e => setFecha(e.target.value)} />
        <input inputMode="decimal" placeholder="Valor €" className={campo} value={valor} onChange={e => setValor(e.target.value)} />
      </div>
      <button className={`${boton} mt-2`} disabled={!valor} onClick={guardar}>Guardar</button>
      {estado && <p className="text-xs text-tx2 mt-2">{estado}</p>}
    </Tarjeta>
  )
}

/** Crowdfunding: valor actual de la plataforma y rentas cobradas en el mes (globales). */
function FormDatoMes({ cuentaId, alGuardar }: { cuentaId: number; alGuardar: () => void }) {
  const [fecha, setFecha] = useState(hoy())
  const [valor, setValor] = useState('')
  const [rentas, setRentas] = useState('')
  const [estado, setEstado] = useState<string>()
  const num = numero
  const guardar = async () => {
    try {
      if (valor) await api.valoracion(cuentaId, fecha, num(valor))
      if (rentas && num(rentas) !== 0) await api.operacion({ cuenta_id: cuentaId, fecha, tipo: 'renta', importe: num(rentas) })
      setValor(''); setRentas(''); setEstado('Guardado ✓'); alGuardar()
    } catch (e) { setEstado(String((e as Error).message)) }
  }
  return (
    <Tarjeta titulo="Dato del mes">
      <input type="date" className={campo} value={fecha} onChange={e => setFecha(e.target.value)} />
      <div className="grid grid-cols-2 gap-2 mt-2">
        <label className="text-xs text-tx3">Valor actual
          <input inputMode="decimal" placeholder="€" className={`${campo} mt-1`} value={valor} onChange={e => setValor(e.target.value)} />
        </label>
        <label className="text-xs text-tx3">Rentas cobradas
          <input inputMode="decimal" placeholder="€ (opcional)" className={`${campo} mt-1`} value={rentas} onChange={e => setRentas(e.target.value)} />
        </label>
      </div>
      <p className="text-xs text-tx3 mt-2">Valor: lo invertido ahora según el panel de la plataforma. Rentas: lo cobrado ese mes, en total.</p>
      <button className={`${boton} mt-2`} disabled={!valor && !rentas} onClick={guardar}>Guardar</button>
      {estado && <p className="text-xs text-tx2 mt-2">{estado}</p>}
    </Tarjeta>
  )
}
