import { useEffect, useState } from 'react'
import { ChartLine, CircleHelp, Home, Receipt, Upload } from 'lucide-react'
import Inicio from './paginas/Inicio'
import Cuenta from './paginas/Cuenta'
import Gastos from './paginas/Gastos'
import Importar from './paginas/Importar'
import Ayuda from './paginas/Ayuda'
import Inversiones from './paginas/Inversiones'
import Plan from './paginas/Plan'

// Navegación por hash (#/, #/cuenta/3, #/gastos, #/importar): el botón atrás del móvil funciona.
function useRuta() {
  const [ruta, setRuta] = useState(location.hash.slice(1) || '/')
  useEffect(() => {
    const f = () => { setRuta(location.hash.slice(1) || '/'); window.scrollTo(0, 0) }
    window.addEventListener('hashchange', f)
    return () => window.removeEventListener('hashchange', f)
  }, [])
  return ruta
}
const ir = (r: string) => { location.hash = r }

const PESTANAS = [
  { ruta: '/', nombre: 'Patrimonio', icono: Home },
  { ruta: '/inversiones', nombre: 'Inversiones', icono: ChartLine },
  { ruta: '/gastos', nombre: 'Gastos', icono: Receipt },
  { ruta: '/importar', nombre: 'Importar', icono: Upload },
  { ruta: '/ayuda', nombre: 'Ayuda', icono: CircleHelp },
]

export default function App() {
  const ruta = useRuta()
  const cuenta = ruta.match(/^\/cuenta\/(\d+)/)
  let pagina
  if (cuenta) pagina = <Cuenta key={cuenta[1]} id={+cuenta[1]} volver={() => history.back()} />
  else if (ruta === '/gastos') pagina = <Gastos />
  else if (ruta === '/inversiones') pagina = <Inversiones abrirCuenta={id => ir(`/cuenta/${id}`)} />
  else if (ruta === '/importar') pagina = <Importar />
  else if (ruta === '/ayuda') pagina = <Ayuda />
  else if (ruta === '/plan') pagina = <Plan volver={() => history.back()} />
  else pagina = <Inicio abrirCuenta={id => ir(`/cuenta/${id}`)} />

  return (
    <div className="min-h-dvh pb-24">
      <main className="mx-auto max-w-xl px-4 pt-[max(env(safe-area-inset-top),0.75rem)]">{pagina}</main>
      <nav className="fixed bottom-0 inset-x-0 border-t border-line bg-bg/95 backdrop-blur pb-[env(safe-area-inset-bottom)]">
        <div className="mx-auto max-w-xl grid grid-cols-5">
          {PESTANAS.map(p => {
            const activa = p.ruta === '/' ? (ruta === '/' || !!cuenta) : p.ruta === '/inversiones' ? (ruta === p.ruta || ruta === '/plan') : ruta === p.ruta
            return (
              <button key={p.ruta} onClick={() => ir(p.ruta)}
                className={`flex flex-col items-center gap-0.5 py-2.5 text-[11px] ${activa ? 'text-tx' : 'text-tx3'}`}>
                <p.icono className="w-5 h-5" />{p.nombre}
              </button>
            )
          })}
        </div>
      </nav>
    </div>
  )
}
