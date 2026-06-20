export const API_BASE = process.env.NEXT_PUBLIC_API_URL || ''

export async function api(path: string, options: RequestInit = {}): Promise<any> {
  const url = `${API_BASE}${path}`
  const { headers: customHeaders, ...restOptions } = options
  const opts: RequestInit = {
    ...restOptions,
    headers: {
      'Content-Type': 'application/json',
      ...customHeaders,
    },
  }
  const res = await fetch(url, opts)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API error ${res.status}: ${text}`)
  }
  return res.json()
}
