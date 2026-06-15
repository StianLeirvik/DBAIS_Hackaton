import type { FacilityRow } from '../types'

export async function searchFacilities(location: string, limit = 200): Promise<FacilityRow[]> {
  const params = new URLSearchParams({
    location,
    limit: String(limit),
  })
  const res = await fetch(`/api/facilities/search?${params}`)
  if (!res.ok) {
    const body = await res.json().catch(() => ({})) as { error?: string }
    throw new Error(body.error ?? `HTTP ${res.status}`)
  }
  return (await res.json()) as FacilityRow[]
}

export async function geocodePincode(
  pincode: string,
): Promise<{ lat: number; lng: number } | null> {
  const res = await fetch(`/api/pincodes/${encodeURIComponent(pincode)}`)
  if (!res.ok) return null
  return (await res.json()) as { lat: number; lng: number } | null
}
