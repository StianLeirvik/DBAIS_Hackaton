export function getOrCreateUserId(): string {
  if (typeof localStorage === 'undefined') return 'anon'
  let id = localStorage.getItem('caremap_user_id')
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem('caremap_user_id', id)
  }
  return id
}

export async function loadSavedFacilityIds(): Promise<string[]> {
  const user_id = getOrCreateUserId()
  try {
    const res = await fetch(`/api/shortlist?user_id=${encodeURIComponent(user_id)}`)
    if (!res.ok) return []
    const rows = (await res.json()) as { facility_id: string }[]
    return rows.map(r => r.facility_id)
  } catch { return [] }
}

export async function saveToShortlist(
  facility_id: string,
  distanceKm: number | null,
): Promise<void> {
  const user_id = getOrCreateUserId()
  await fetch('/api/shortlist/item', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id, facility_id, distance_km: distanceKm }),
  }).catch(() => {})
}

export async function removeFromShortlist(facility_id: string): Promise<void> {
  const user_id = getOrCreateUserId()
  await fetch(
    `/api/shortlist/item/${encodeURIComponent(facility_id)}?user_id=${encodeURIComponent(user_id)}`,
    { method: 'DELETE' },
  ).catch(() => {})
}
