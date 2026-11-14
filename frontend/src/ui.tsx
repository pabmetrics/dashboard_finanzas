import type { ReactNode } from 'react'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { CATEGORIAS, COLOR_CATEGORIA, fmt, mesCorto, type PuntoEvolucion } from './api'

export function Tarjeta({ titulo, accion, children, className = '' }:
  { titulo?: string; accion?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-2xl bg-s1 border border-line p-4 ${className}`}>
      {(titulo || accion) && (
        <div className="flex items-center justify-between mb-3">
          {titulo && <h2 className="text-sm font-medium text-tx2">{titulo}</h2>}
          {accion}
        </div>
      )}
      {children}
    </section>
  )
}

export function Dato({ etiqueta, valor, detalle, tono }:
  { etiqueta: string; valor: string; detalle?: string; tono?: 'bueno' | 'malo' }) {
  return (
    <div className="rounded-xl bg-s2 px-3 py-2.5 min-w-0">
      <div className="text-xs text-tx3 truncate">{etiqueta}</div>
      <div className="num text-lg font-semibold text-tx truncate">{valor}</div>
      {detalle && (
        <div className={`num text-xs ${tono === 'bueno' ? 'text-good' : tono === 'malo' ? 'text-bad' : 'text-tx3'}`}>
          {tono === 'bueno' ? '▲ ' : tono === 'malo' ? '▼ ' : ''}{detalle}
        </div>
      )}
    </div>
  )
}

export function Leyenda({ items }: { items: { nombre: string; color: string; valor?: string }[] }) {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-tx2">
      {items.map(i => (
        <span key={i.nombre} className="inline-flex items-center gap-1.5">
          <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: i.color }} />
          {i.nombre}{i.valor && <span className="num text-tx">{i.valor}</span>}
        </span>
      ))}
    </div>
  )
}

const ejeTick = { fill: 'var(--text-muted)', fontSize: 11 }
const kEur = (v: number) => Math.abs(v) >= 10000 ? `${Math.round(v / 1000)}k`
  : Math.abs(v) >= 1000 ? `${(v / 1000).toLocaleString('es-ES', { maximumFractionDigits: 1 })}k` : `${v}`

function CajaTooltip({ titulo, filas }: { titulo: string; filas: { nombre: string; valor: number; color?: string }[] }) {
  return (
    <div className="rounded-lg border border-line bg-s2 px-3 py-2 text-xs shadow-lg">
      <div className="text-tx2 mb-1">{titulo}</div>
      {filas.map(f => (
        <div key={f.nombre} className="flex items-center justify-between gap-4">
          <span className="inline-flex items-center gap-1.5 text-tx2">
            {f.color && <span className="w-2 h-2 rounded-sm" style={{ background: f.color }} />}{f.nombre}
          </span>
          <span className="num text-tx">{fmt(f.valor)}</span>
        </div>
      ))}
    </div>
  )
}

/** Evolución del patrimonio: áreas apiladas por categoría; el tooltip da el total y el desglose. */
export function GraficoEvolucion({ datos }: { datos: PuntoEvolucion[] }) {
  const cats = CATEGORIAS.filter(c => datos.some(d => typeof d[c] === 'number' && (d[c] as number) !== 0))
  return (
    <div>
      <div className="h-56 -ml-2">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={datos} margin={{ top: 8, right: 4, bottom: 0, left: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--border)" strokeDasharray="0" />
            <XAxis dataKey="fecha" tickFormatter={mesCorto} tick={ejeTick} axisLine={false} tickLine={false}
              minTickGap={24} />
            <YAxis tickFormatter={kEur} tick={ejeTick} axisLine={false} tickLine={false} width={36} />
            <Tooltip cursor={{ stroke: 'var(--text-muted)', strokeWidth: 1 }}
              content={({ active, payload, label }) => active && payload?.length ? (
                <CajaTooltip titulo={mesCorto(String(label))} filas={[
                  { nombre: 'Total', valor: Number(payload[0].payload.total) },
                  ...[...cats].reverse().map(c => ({ nombre: c, valor: Number(payload[0].payload[c] ?? 0), color: COLOR_CATEGORIA[c] })),
                ]} />
              ) : null} />
            {cats.map(c => (
              <Area key={c} type="monotone" dataKey={c} stackId="1" stroke="var(--surface-1)" strokeWidth={2}
                fill={COLOR_CATEGORIA[c]} fillOpacity={0.9} isAnimationActive={false} />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-2"><Leyenda items={cats.map(c => ({ nombre: c, color: COLOR_CATEGORIA[c] }))} /></div>
    </div>
  )
}

/** Una sola serie: línea de 2px con cursor y tooltip. */
export function GraficoLinea({ datos }: { datos: { fecha: string; valor: number }[] }) {
  return (
    <div className="h-44 -ml-2">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={datos} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--border)" />
          <XAxis dataKey="fecha" tickFormatter={mesCorto} tick={ejeTick} axisLine={false} tickLine={false} minTickGap={24} />
          <YAxis tickFormatter={kEur} tick={ejeTick} axisLine={false} tickLine={false} width={36} />
          <Tooltip cursor={{ stroke: 'var(--text-muted)', strokeWidth: 1 }}
            content={({ active, payload, label }) => active && payload?.length ? (
              <CajaTooltip titulo={mesCorto(String(label))} filas={[{ nombre: 'Valor', valor: Number(payload[0].value) }]} />
            ) : null} />
          <Line type="monotone" dataKey="valor" stroke="var(--series-1)" strokeWidth={2} dot={false}
            activeDot={{ r: 4, stroke: 'var(--surface-1)', strokeWidth: 2 }} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

/** Barra segmentada (parte de un todo) con 2px de separación entre segmentos y leyenda con valores. */
export function BarraReparto({ partes }: { partes: { nombre: string; valor: number; color: string }[] }) {
  const total = partes.reduce((s, p) => s + Math.max(p.valor, 0), 0) || 1
  return (
    <div>
      <div className="flex h-3 gap-[2px] rounded-full overflow-hidden" role="img"
        aria-label={partes.map(p => `${p.nombre} ${Math.round(p.valor / total * 100)}%`).join(', ')}>
        {partes.filter(p => p.valor > 0).map(p => (
          <div key={p.nombre} title={`${p.nombre}: ${fmt(p.valor)}`}
            style={{ width: `${p.valor / total * 100}%`, background: p.color }} />
        ))}
      </div>
      <div className="mt-3 grid grid-cols-1 gap-1.5">
        {partes.map(p => (
          <div key={p.nombre} className="flex items-center justify-between text-sm">
            <span className="inline-flex items-center gap-2 text-tx2">
              <span className="w-2.5 h-2.5 rounded-sm" style={{ background: p.color }} />{p.nombre}
            </span>
            <span className="num text-tx">{fmt(p.valor)} <span className="text-tx3 text-xs w-10 inline-block text-right">
              {Math.round(p.valor / total * 100)}%</span></span>
          </div>
        ))}
      </div>
    </div>
  )
}

/** Real frente a objetivo: barra (real) y marca vertical (objetivo); debajo, cuánto falta o sobra. */
export function RealVsPlan({ filas }: { filas: { tipo: string; real: number; objetivo: number; valor: number; diferencia?: number; fuera_del_plan?: boolean }[] }) {
  const max = Math.max(...filas.map(f => Math.max(f.real, f.objetivo)), 1)
  return (
    <div className="space-y-3">
      {filas.map(f => {
        const desviado = Math.abs(f.real - f.objetivo) >= 3
        return (
          <div key={f.tipo}>
            <div className="flex justify-between text-xs mb-1 gap-2">
              <span className="text-tx2 truncate">{f.tipo === 'Cuenta corriente' ? 'Liquidez (cuenta corriente)' : f.tipo}</span>
              <span className="num text-tx shrink-0">{f.real.toLocaleString('es-ES')} %
                <span className="text-tx3"> / {f.fuera_del_plan ? 'fuera del plan' : `${f.objetivo.toLocaleString('es-ES')} %`}</span>
              </span>
            </div>
            <div className="relative h-2 rounded-full bg-s2">
              <div className="absolute inset-y-0 left-0 rounded-full" style={{ width: `${f.real / max * 100}%`, background: 'var(--series-1)' }} />
              {f.objetivo > 0 && (
                <div className="absolute -top-1 -bottom-1 w-[2px] bg-tx" style={{ left: `calc(${f.objetivo / max * 100}% - 1px)` }} />
              )}
            </div>
            {f.diferencia !== undefined && Math.abs(f.diferencia) >= 50 && (
              <div className={`num text-[11px] mt-0.5 ${desviado ? 'text-warn' : 'text-tx3'}`}>
                {f.diferencia > 0 ? `Faltan ${fmt(f.diferencia)}` : `Sobran ${fmt(-f.diferencia)}`} · {fmt(f.valor)} ahora
              </div>
            )}
          </div>
        )
      })}
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-tx3 pt-1">
        <span className="inline-flex items-center gap-1.5"><span className="w-3 h-2 rounded-full" style={{ background: 'var(--series-1)' }} />Real</span>
        <span className="inline-flex items-center gap-1.5"><span className="w-[2px] h-3 bg-tx" />Objetivo</span>
        <span>En naranja: se desvía 3 puntos o más</span>
      </div>
    </div>
  )
}

/** Fondo de emergencia: progreso hacia el objetivo y su reparto. */
export function FondoEmergencia({ e }: { e: { objetivo: number; cubierto: number; componentes: { tipo: string; objetivo: number; real: number }[] } }) {
  const pctCubierto = e.objetivo ? Math.min(e.cubierto / e.objetivo * 100, 100) : 0
  const completo = e.cubierto >= e.objetivo - 0.5
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="num text-xl font-semibold">{fmt(e.cubierto)}</span>
        <span className="num text-sm text-tx3">de {fmt(e.objetivo)}</span>
      </div>
      <div className="h-2 rounded-full bg-s2 mt-2 overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${pctCubierto}%`, background: completo ? 'var(--good)' : 'var(--warning)' }} />
      </div>
      <div className={`text-xs mt-1 ${completo ? 'text-good' : 'text-warn'}`}>
        {completo ? '✓ Completo' : `⚠ Faltan ${fmt(e.objetivo - e.cubierto)}`}
      </div>
      <div className="mt-3 space-y-1">
        {e.componentes.map(c => (
          <div key={c.tipo} className="flex justify-between text-sm">
            <span className="text-tx2">{c.tipo === 'Cuenta corriente' ? 'En liquidez' : `En ${c.tipo.toLowerCase()}`}</span>
            <span className="num text-tx">{fmt(c.real)} <span className="text-tx3 text-xs">/ {fmt(c.objetivo)}</span></span>
          </div>
        ))}
      </div>
    </div>
  )
}

export function Cargando() {
  return <div className="p-8 text-center text-tx3 text-sm">Cargando…</div>
}

export function ErrorCaja({ error }: { error: string }) {
  return <div className="m-4 rounded-xl border border-bad/50 bg-bad/10 p-3 text-sm text-tx">⚠️ {error}</div>
}

/** Valor de las inversiones frente a lo aportado (mismo eje, misma unidad). */
export function GraficoValorAportado({ datos }: { datos: { fecha: string; valor: number; aportado: number }[] }) {
  return (
    <div>
      <div className="h-52 -ml-2">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={datos} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--border)" />
            <XAxis dataKey="fecha" tickFormatter={mesCorto} tick={ejeTick} axisLine={false} tickLine={false} minTickGap={24} />
            <YAxis tickFormatter={kEur} tick={ejeTick} axisLine={false} tickLine={false} width={36} domain={['auto', 'auto']} />
            <Tooltip cursor={{ stroke: 'var(--text-muted)', strokeWidth: 1 }}
              content={({ active, payload, label }) => active && payload?.length ? (
                <CajaTooltip titulo={mesCorto(String(label))} filas={[
                  { nombre: 'Valor', valor: Number(payload[0].payload.valor), color: 'var(--series-1)' },
                  { nombre: 'Aportado', valor: Number(payload[0].payload.aportado), color: 'var(--text-muted)' },
                  { nombre: 'Ganancia', valor: Number(payload[0].payload.valor) - Number(payload[0].payload.aportado) },
                ]} />
              ) : null} />
            <Line type="monotone" dataKey="aportado" stroke="var(--text-muted)" strokeWidth={2} strokeDasharray="4 4"
              dot={false} isAnimationActive={false} />
            <Line type="monotone" dataKey="valor" stroke="var(--series-1)" strokeWidth={2} dot={false}
              activeDot={{ r: 4, stroke: 'var(--surface-1)', strokeWidth: 2 }} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-2"><Leyenda items={[{ nombre: 'Valor', color: 'var(--series-1)' }, { nombre: 'Aportado (lo que has puesto)', color: 'var(--text-muted)' }]} /></div>
    </div>
  )
}

/** Barras de una sola serie (ingresos por mes). */
export function GraficoBarras({ datos }: { datos: { mes: string; importe: number }[] }) {
  return (
    <div className="h-40 -ml-2">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={datos.map(d => ({ ...d, fecha: d.mes + '-01' }))} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--border)" />
          <XAxis dataKey="fecha" tickFormatter={mesCorto} tick={ejeTick} axisLine={false} tickLine={false} minTickGap={8} />
          <YAxis tick={ejeTick} axisLine={false} tickLine={false} width={36} />
          <Tooltip cursor={{ fill: 'var(--surface-2)' }}
            content={({ active, payload, label }) => active && payload?.length ? (
              <CajaTooltip titulo={mesCorto(String(label))} filas={[{ nombre: 'Cobrado', valor: Number(payload[0].value) }]} />
            ) : null} />
          <Bar dataKey="importe" fill="var(--series-3)" radius={[4, 4, 0, 0]} maxBarSize={28} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
