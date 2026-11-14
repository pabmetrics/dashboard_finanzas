import { useEffect, useState } from 'react'
import { marked } from 'marked'
import { api } from '../api'
import { Cargando, ErrorCaja } from '../ui'

export default function Ayuda() {
  const [html, setHtml] = useState<string>()
  const [error, setError] = useState<string>()
  useEffect(() => {
    api.manual().then(r => setHtml(marked.parse(r.texto) as string)).catch(e => setError(String(e.message ?? e)))
  }, [])
  if (error) return <ErrorCaja error={error} />
  if (!html) return <Cargando />
  return <article className="manual pt-2" dangerouslySetInnerHTML={{ __html: html }} />
}
