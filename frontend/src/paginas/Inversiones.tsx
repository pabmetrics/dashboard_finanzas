import { useCallback, useEffect, useState } from 'react'
import { AlertTriangle, ChevronRight, RefreshCw } from 'lucide-react'
import { api, fechaCorta, fmt, fmtSigno, pct, type Inversiones as Datos } from '../api'
import { Cargando, Dato, ErrorCaja, FondoEmergencia, GraficoBarras, GraficoValorAportado, RealVsPlan, Tarjeta } from '../ui'

export default function Inversiones({ abrirCuenta }: { abrirCuenta: (id: number) => void }) {
  const [d, setD] = useState<Datos>()
  const [error, setError] = useState<string>()
  const [actualizando, setActualizando] = useState(false)
  const [verVendidas, setVerVendidas] = useState(false)
  const cargar = useCallback(() => { api.inversiones().then(setD).catch(e => setError(String(e.message ?? e))) }, [])
  useEffect(cargar, [cargar])

  if (error) return <ErrorCaja error={error} />
  if (!d) return <Cargando />

  const actualizar = async () => {
    setActualizando(true)
    try { await api.actualizarPrecios() } catch (e) { setError((e as Error).message) }
    setActualizando(false); cargar()
  }
  const rentabilidad = d.aportado > 0 ? d.ganancia / d.aportado * 100 : null
  // solo avisa de lo que se tiene ahora (lo vendido no necesita precio)
  const fallidos = (d.precios.resultado?.fallidos ?? []).filter(f => d.posiciones.some(p => p.nombre === f.activo))
  const actualizado = d.precios.actualizados

  return (
    <div className="space-y-4">
      <header className="pt-2">
        <div className="text-sm text-tx3">Inversiones</div>
        <div className="num text-4xl font-semibold tracking-tight">{fmt(d.valor)}</div>
        <div className={`num text-sm mt-0.5 ${d.ganancia >= 0 ? 'text-good' : 'text-bad'}`}>
          {d.ganancia >= 0 ? '▲' : '▼'} {fmtSigno(d.ganancia)}{rentabilidad != null && ` (${pct(rentabilidad)})`}
          <span className="text-tx3"> sobre {fmt(d.aportado)} aportados</span>
        </div>
      </header>

      <div className="grid grid-cols-2 gap-2">
        <Dato etiqueta="Este mes" valor={d.ganancia_mes != null ? fmtSigno(d.ganancia_mes) : '—'}
          detalle="sin contar aportaciones" />
        <Dato etiqueta="Latente" valor={fmtSigno(d.latente)} detalle="en lo que tienes ahora" />
        <Dato etiqueta="Realizada" valor={fmtSigno(d.realizada)} detalle="en lo ya vendido" />
        <Dato etiqueta="Cobrado" valor={fmt(d.cobrado)} detalle="dividendos, intereses y rentas" />
      </div>

      <Tarjeta titulo="Valor frente a aportado">
        <GraficoValorAportado datos={d.evolucion} />
      </Tarjeta>

      <Tarjeta titulo="Posiciones">
        <ul className="-mx-2">
          {d.posiciones.map((p, i) => (
            <li key={i}>
              <button onClick={() => abrirCuenta(p.cuenta_id)}
                className="w-full flex items-center justify-between gap-2 rounded-lg px-2 py-2.5 hover:bg-s2 active:bg-s2 text-left">
                <span className="min-w-0">
                  <span className="block text-sm text-tx truncate">{p.nombre}</span>
                  <span className="block text-xs text-tx3 truncate">
                    {p.cuenta} · {p.peso.toLocaleString('es-ES')} %
                    {p.fecha_precio && ` · ${p.manual ? 'dato' : 'precio'} ${fechaCorta(p.fecha_precio)}`}
                  </span>
                </span>
                <span className="flex items-center gap-1 shrink-0">
                  <span className="text-right">
                    <span className="block num text-sm text-tx">{fmt(p.valor)}</span>
                    {p.manual ? (
                      p.rentas ? <span className="block num text-xs text-good">+{fmt(p.rentas)} rentas</span> : null
                    ) : p.titulos != null && (
                      <span className={`block num text-xs ${p.ganancia >= 0 ? 'text-good' : 'text-bad'}`}>
                        {fmtSigno(p.ganancia)}{p.rentabilidad != null && ` · ${pct(p.rentabilidad)}`}
                      </span>
                    )}
                  </span>
                  <ChevronRight className="w-4 h-4 text-tx3" />
                </span>
              </button>
            </li>
          ))}
        </ul>
      </Tarjeta>

      <Tarjeta titulo="Fondo de emergencia" accion={<a href="#/plan" className="text-xs text-acc">Editar plan</a>}>
        <FondoEmergencia e={d.cuadre.emergencia} />
      </Tarjeta>

      <Tarjeta titulo="Resto del patrimonio: real vs. plan" accion={<a href="#/plan" className="text-xs text-acc">Editar plan</a>}>
        <p className="text-xs text-tx3 -mt-1 mb-3">
          {fmt(d.cuadre.resto.base)}: todo menos el fondo de emergencia. La liquidez que sobra cuenta como "cuenta corriente".
        </p>
        <RealVsPlan filas={d.cuadre.resto.filas} />
      </Tarjeta>

      {d.ingresos_mensuales.length > 0 && (
        <Tarjeta titulo="Cobrado por mes" accion={<span className="text-xs text-tx3">neto de retenciones</span>}>
          <GraficoBarras datos={d.ingresos_mensuales} />
        </Tarjeta>
      )}

      {d.vendidas.length > 0 && (
        <Tarjeta titulo="Vendido" accion={
          <button className="text-xs text-acc" onClick={() => setVerVendidas(!verVendidas)}>{verVendidas ? 'Ocultar' : `Ver ${d.vendidas.length}`}</button>}>
          <div className="flex justify-between text-sm">
            <span className="text-tx2">Ganancia realizada total</span>
            <span className={`num ${d.realizada >= 0 ? 'text-good' : 'text-bad'}`}>{fmtSigno(d.realizada, true)}</span>
          </div>
          {verVendidas && (
            <ul className="divide-y divide-line mt-2">
              {d.vendidas.map((v, i) => (
                <li key={i} className="py-2 flex justify-between text-sm">
                  <span className="text-tx2 truncate">{v.nombre} <span className="text-tx3 text-xs">· {v.cuenta}</span></span>
                  <span className={`num ${v.realizado >= 0 ? 'text-good' : 'text-bad'}`}>{fmtSigno(v.realizado, true)}</span>
                </li>
              ))}
            </ul>
          )}
        </Tarjeta>
      )}

      <div className="rounded-2xl border border-line p-3 text-xs text-tx3 space-y-2">
        <div className="flex items-center justify-between gap-2">
          <span>Precios {actualizado ? `actualizados el ${fechaCorta(actualizado.slice(0, 10))} a las ${actualizado.slice(11, 16)}` : 'sin actualizar'} · automático cada día</span>
          <button onClick={actualizar} disabled={actualizando}
            className="inline-flex items-center gap-1 rounded-lg border border-line px-2.5 py-1.5 text-tx2 disabled:opacity-50">
            <RefreshCw className={`w-3.5 h-3.5 ${actualizando ? 'animate-spin' : ''}`} />{actualizando ? 'Actualizando' : 'Actualizar'}
          </button>
        </div>
        {fallidos.length > 0 && (
          <div className="text-warn"><AlertTriangle className="inline w-3 h-3 mr-1 -mt-0.5" />
            Sin precio automático: {fallidos.map(f => f.activo).join(', ')}. Se usa el último conocido.</div>
        )}
      </div>
    </div>
  )
}
