import { ref, computed } from 'vue'
import { searchFacilities, geocodePincode } from '../api/facilities'
import { scoreFacility, sortFacilities } from '../utils/scoring'
import type { ScoredFacility, SortBy } from '../types'
import { getCareNeed } from '../types'

const location = ref('')
const careNeedId = ref('dialysis')
const sortBy = ref<SortBy>('score')
const results = ref<ScoredFacility[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const hasSearched = ref(false)
const userCenter = ref<{ lat: number; lng: number } | null>(null)

const sortedResults = computed(() => sortFacilities(results.value, sortBy.value))

export function useSearch() {
  async function search() {
    const loc = location.value.trim()
    if (!loc) return

    loading.value = true
    error.value = null
    hasSearched.value = true

    try {
      const careNeed = getCareNeed(careNeedId.value)
      if (!careNeed) throw new Error('Invalid care need selected')

      // Fetch raw facilities
      const rows = await searchFacilities(loc)
      if (rows.length === 0) {
        results.value = []
        return
      }

      // Determine user reference coordinates
      let userLat: number | null = null
      let userLng: number | null = null

      // Try pincode geocoding if input is numeric
      if (/^\d{5,6}$/.test(loc)) {
        const geo = await geocodePincode(loc).catch(() => null)
        if (geo) {
          userLat = geo.lat
          userLng = geo.lng
        }
      }

      // Fallback: average coordinates of found facilities
      if (userLat === null) {
        const lats: number[] = []
        const lngs: number[] = []
        for (const row of rows.slice(0, 50)) {
          const lat = row.latitude_clean
          const lng = row.longitude_clean
          if (lat != null && lng != null) {
            lats.push(lat)
            lngs.push(lng)
          }
        }
        if (lats.length > 0) {
          userLat = lats.reduce((a, b) => a + b, 0) / lats.length
          userLng = lngs.reduce((a, b) => a + b, 0) / lngs.length
        }
      }

      // Score all facilities
      userCenter.value = userLat != null && userLng != null ? { lat: userLat, lng: userLng } : null
      results.value = rows.map(row => scoreFacility(row, careNeed, userLat, userLng))
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'An unexpected error occurred'
      results.value = []
    } finally {
      loading.value = false
    }
  }

  return {
    location,
    careNeedId,
    sortBy,
    results,
    sortedResults,
    loading,
    error,
    hasSearched,
    userCenter,
    search,
  }
}
