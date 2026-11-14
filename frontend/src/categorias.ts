import { useEffect, useState } from 'react'
import { api } from './api'

let cache: string[] | undefined
export function useCategorias() {
  const [c, setC] = useState<string[]>(cache ?? [])
  useEffect(() => { if (!cache) api.categorias().then(r => { cache = r; setC(r) }) }, [])
  return c
}
