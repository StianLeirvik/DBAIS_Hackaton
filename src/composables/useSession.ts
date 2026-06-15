import { reactive } from 'vue'
import type { ScoredFacility, ConfidenceLevel } from '../types'
import { loadSavedFacilityIds, saveToShortlist, removeFromShortlist } from '../api/shortlist'

interface FacilitySession {
  saved: boolean
  note: string
  verified: boolean
  dismissed: boolean
}

const sessions = reactive<Record<string, FacilitySession>>({})

function ensureSession(id: string) {
  if (!sessions[id]) {
    sessions[id] = { saved: false, note: '', verified: false, dismissed: false }
  }
}

// Hydrate from DB on startup (best-effort — silent if tables don't exist yet)
loadSavedFacilityIds().then(ids => {
  for (const id of ids) {
    ensureSession(id)
    sessions[id].saved = true
  }
})

export function useSession() {
  function getSession(id: string): FacilitySession {
    ensureSession(id)
    return sessions[id]
  }

  function toggleSave(id: string, facility?: ScoredFacility) {
    ensureSession(id)
    const nowSaved = !sessions[id].saved
    sessions[id].saved = nowSaved
    if (nowSaved) {
      saveToShortlist(id, facility?.distanceKm ?? null)
    } else {
      removeFromShortlist(id)
    }
  }

  function toggleVerify(id: string) {
    ensureSession(id)
    sessions[id].verified = !sessions[id].verified
  }

  function toggleDismiss(id: string) {
    ensureSession(id)
    sessions[id].dismissed = !sessions[id].dismissed
  }

  function setNote(id: string, text: string) {
    ensureSession(id)
    sessions[id].note = text
  }

  function savedCount(): number {
    return Object.values(sessions).filter(s => s.saved).length
  }

  function effectiveConfidence(facility: ScoredFacility): ConfidenceLevel {
    const s = sessions[facility.facility_id]
    return s?.verified ? 'high' : facility.confLevel
  }

  function getSaved(facilities: ScoredFacility[]): ScoredFacility[] {
    return facilities.filter(f => sessions[f.facility_id]?.saved)
  }

  return {
    sessions,
    getSession,
    toggleSave,
    toggleVerify,
    toggleDismiss,
    setNote,
    savedCount,
    effectiveConfidence,
    getSaved,
  }
}
