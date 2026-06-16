// Sub-row types returned by joined star-schema subqueries
export interface ContactRow {
  channel: string        // 'phone' | 'email' | 'web' | 'fb'
  value: string
  is_official: boolean
}

export interface SpecialtyRow {
  specialty_code: string
  display_name: string
  mention_count: number
  confidence: number
}

export interface ClaimRow {
  text: string
  tag?: string | null
  confidence: number
  reliability: string    // 'Reliable' | 'Uncertain' | 'Unreliable'
  reliability_reason?: string | null
  url?: string | null
  is_reliable: boolean
}

export interface SourceRow {
  url: string
  is_official: boolean
}

// Row returned by /api/facilities/search (one row per facility with all relations aggregated)
export interface FacilityRow {
  facility_id: string
  cluster_id: string | null
  name_clean: string
  facility_type: string | null
  operator_type: string | null
  year_established: number | null
  capacity_beds: number | null
  number_doctors: number | null
  city: string | null
  state: string | null
  pincode: string | null
  latitude_clean: number | null
  longitude_clean: number | null
  geo_is_valid: boolean
  geo_source: string | null
  evidence_band: 'High' | 'Med' | 'Low' | null
  data_quality_score: number | null
  contacts: ContactRow[] | null
  specialties: SpecialtyRow[] | null
  procedures: ClaimRow[] | null
  equipment: ClaimRow[] | null
  capabilities: ClaimRow[] | null
  sources: SourceRow[] | null
}

// Alias so older imports still compile
export type FacilityRaw = FacilityRow

export interface Evidence {
  text: string
  field: string
  raw?: string
  urls?: string[]
}

export type ConfidenceLevel = 'high' | 'med' | 'low'

export interface ScoredFacility extends FacilityRow {
  // Derived contact fields (pre-extracted from contacts array)
  phone: string | null
  email: string | null
  website: string | null
  // Score components
  overallScore: number     // 0–90
  capabilityScore: number  // 0–45
  proximityScore: number   // 0–30
  freshnessScore: number   // 0–15
  riskPenalty: number      // subtracted from sum
  distanceKm: number | null
  // Confidence
  confLevel: ConfidenceLevel
  confReason: string
  pinOk: boolean
  // Evidence tiers
  greenEvidence: Evidence[]
  amberEvidence: Evidence[]
  coralEvidence: Evidence[]
  greyEvidence: Evidence[]
  // Dot counts for list card
  dotGreen: number
  dotAmber: number
  dotCoral: number
  dotGrey: number
}

export interface CareNeedDef {
  id: string
  label: string
  icon: string
  keywords: string[]
}

export type SortBy = 'score' | 'distance'

export const CARE_NEEDS: CareNeedDef[] = [
  {
    id: 'dialysis',
    label: 'Dialysis',
    icon: '🩸',
    keywords: ['dialysis', 'nephrology', 'kidney', 'renal', 'dialysi'],
  },
  {
    id: 'emergency_surgery',
    label: 'Emergency Surgery',
    icon: '🚑',
    keywords: ['emergency', 'surgery', 'surgical', 'trauma', 'icu', 'intensive care', 'operating'],
  },
  {
    id: 'maternity',
    label: 'Maternity Care',
    icon: '🤱',
    keywords: ['maternity', 'obstetric', 'gynecolog', 'gynaecolog', 'delivery', 'prenatal', 'antenatal', 'neonat', 'labour'],
  },
  {
    id: 'cardiac',
    label: 'Cardiac Care',
    icon: '❤️',
    keywords: ['cardio', 'cardiac', 'heart', 'coronary', 'ecg', 'echocardiograph'],
  },
  {
    id: 'cancer',
    label: 'Cancer Care',
    icon: '🎗️',
    keywords: ['oncol', 'cancer', 'chemotherapy', 'radiotherapy', 'tumor', 'tumour'],
  },
  {
    id: 'pediatrics',
    label: 'Pediatrics',
    icon: '👶',
    keywords: ['pediatric', 'paediatric', 'child', 'neonat', 'infant'],
  },
  {
    id: 'eye',
    label: 'Eye Care',
    icon: '👁️',
    keywords: ['ophthalmol', 'optometry', 'eye', 'vision', 'cataract', 'retina', 'glaucoma'],
  },
  {
    id: 'orthopedic',
    label: 'Orthopedics',
    icon: '🦴',
    keywords: ['orthoped', 'orthopaedic', 'bone', 'joint', 'fracture', 'spine', 'arthroplasty'],
  },
]

export function getCareNeed(id: string): CareNeedDef | undefined {
  return CARE_NEEDS.find(c => c.id === id)
}
