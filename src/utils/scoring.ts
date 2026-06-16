import { haversineKm } from './distance'
import type { FacilityRow, ScoredFacility, CareNeedDef, Evidence, ConfidenceLevel } from '../types'

// Maximum search radius used for linear proximity decay
const MAX_KM = 300

// ---------------------------------------------------------------------------
// capability_pts = round(45 * (0.6·specialty_match + 0.4·keyword_strength))
// specialty_match  = fraction of keywords matched in any specialty display_name
// keyword_strength = total weighted hits / (keywords.length * max_weight), ≤ 1
// ---------------------------------------------------------------------------
function capabilityPts(row: FacilityRow, careNeed: CareNeedDef): number {
  const specialties  = row.specialties  ?? []
  const procedures   = row.procedures   ?? []
  const equipment    = row.equipment    ?? []
  const capabilities = row.capabilities ?? []
  const kwds = careNeed.keywords

  // specialty_match: fraction of keywords that hit at least one specialty
  const specHits = kwds.filter(kw =>
    specialties.some(s => s.display_name.toLowerCase().includes(kw))
  ).length
  const specialtyMatch = kwds.length > 0 ? specHits / kwds.length : 0

  // keyword_strength: weighted evidence hits, normalised
  // max weight per keyword per source type: 1.0 (spec) + 0.8 (proc) + 0.8 (equip) + 0.4 (cap) = 3.0
  const MAX_WEIGHT_PER_KW = 3.0
  let totalHits = 0
  for (const kw of kwds) {
    const kwl = kw.toLowerCase()
    const spec = specialties.find(s => s.display_name.toLowerCase().includes(kwl))
    if (spec) totalHits += 1.0

    const proc = procedures.find(p =>
      (p.text?.toLowerCase() ?? '').includes(kwl) || (p.tag?.toLowerCase() ?? '').includes(kwl))
    if (proc) totalHits += proc.is_reliable ? 0.8 : 0.3

    const equip = equipment.find(e =>
      (e.text?.toLowerCase() ?? '').includes(kwl) || (e.tag?.toLowerCase() ?? '').includes(kwl))
    if (equip) totalHits += equip.is_reliable ? 0.8 : 0.3

    const cap = capabilities.find(c => (c.text?.toLowerCase() ?? '').includes(kwl))
    if (cap) totalHits += cap.is_reliable ? 0.4 : 0.15
  }
  const keywordStrength = kwds.length > 0
    ? Math.min(1, totalHits / (kwds.length * MAX_WEIGHT_PER_KW))
    : 0

  return Math.round(45 * (0.6 * specialtyMatch + 0.4 * keywordStrength))
}

// ---------------------------------------------------------------------------
// proximity_pts = round(30 * max(0, 1 - distance_km / MAX_KM))  — linear decay
// ---------------------------------------------------------------------------
function proximityPts(distanceKm: number | null): number {
  if (distanceKm === null) return 0
  return Math.round(30 * Math.max(0, 1 - distanceKm / MAX_KM))
}

// ---------------------------------------------------------------------------
// freshness_pts = round(15 * recency_score)
// Derived from evidence_band (proxy for data recency/quality)
// ---------------------------------------------------------------------------
function freshnessPts(row: FacilityRow): number {
  const recency =
    row.evidence_band === 'High' ? 1.0 :
    row.evidence_band === 'Med'  ? 0.65 : 0.3
  return Math.round(15 * recency)
}

// ---------------------------------------------------------------------------
// Confidence from DB evidence_band
// ---------------------------------------------------------------------------

function computeConfidence(row: FacilityRow): { level: ConfidenceLevel; reason: string } {
  if (row.evidence_band === 'High')
    return { level: 'high', reason: 'Strong, well-corroborated record with high data quality from the catalog pipeline.' }
  if (row.evidence_band === 'Med')
    return { level: 'med', reason: 'Moderate evidence quality. Some claims are unverified — confirm service availability by phone.' }
  if (row.evidence_band === 'Low')
    return { level: 'low', reason: 'Limited corroboration or data quality issues detected. Treat all claims as unverified.' }
  // Fallback: data_quality_score
  const dqs = row.data_quality_score ?? 0
  if (dqs >= 0.7) return { level: 'high', reason: 'Good data quality score from catalog pipeline.' }
  if (dqs >= 0.4) return { level: 'med', reason: 'Moderate data quality score. Confirm by phone before referral.' }
  return { level: 'low', reason: 'Low data quality score. Treat as unverified.' }
}

// ---------------------------------------------------------------------------
// PIN validation
// ---------------------------------------------------------------------------

function isPinOk(pin: string | null): boolean {
  return !!pin && /^\d{6}$/.test(pin.trim())
}

// ---------------------------------------------------------------------------
// Evidence generation
// ---------------------------------------------------------------------------

function generateEvidence(
  row: FacilityRow,
  careNeed: CareNeedDef,
): { green: Evidence[]; amber: Evidence[]; coral: Evidence[]; grey: Evidence[] } {
  const green: Evidence[] = []
  const amber: Evidence[] = []
  const coral: Evidence[] = []
  const grey: Evidence[] = []

  const specialties  = row.specialties  ?? []
  const procedures   = row.procedures   ?? []
  const equipment    = row.equipment    ?? []
  const capabilities = row.capabilities ?? []

  // ── Green ──────────────────────────────────────────────────────────────
  const matchingSpecs = specialties.filter(s =>
    careNeed.keywords.some(kw => s.display_name.toLowerCase().includes(kw)))
  if (matchingSpecs.length > 0) {
    const names = [...new Set(matchingSpecs.map(s => s.display_name))]
    green.push({ text: `${careNeed.label} listed among documented specialties`,
      field: 'facility_specialty.display_name', raw: names.slice(0, 8).join(', ') })
  }

  const reliableProcs = procedures.filter(p => p.is_reliable &&
    careNeed.keywords.some(kw =>
      (p.text?.toLowerCase() ?? '').includes(kw) || (p.tag?.toLowerCase() ?? '').includes(kw)))
  if (reliableProcs.length > 0)
    green.push({ text: `${careNeed.label} named as a delivered procedure`,
      field: 'facility_procedure.procedure_text',
      raw: reliableProcs.map(p => `"${p.text}"`).slice(0, 4).join('\n'),
      urls: reliableProcs.filter(p => p.url).map(p => p.url!).slice(0, 3) })

  const reliableEquip = equipment.filter(e => e.is_reliable &&
    careNeed.keywords.some(kw =>
      (e.text?.toLowerCase() ?? '').includes(kw) || (e.tag?.toLowerCase() ?? '').includes(kw)))
  if (reliableEquip.length > 0)
    green.push({ text: `${careNeed.label} equipment documented on site`,
      field: 'facility_equipment.equipment_text',
      raw: reliableEquip.map(e => `"${e.text}"`).slice(0, 4).join('\n') })

  const reliableCaps = capabilities.filter(c => c.is_reliable &&
    careNeed.keywords.some(kw => (c.text?.toLowerCase() ?? '').includes(kw)))
  if (reliableCaps.length > 0)
    green.push({ text: `${careNeed.label} capability documented`,
      field: 'facility_capability.capability_text',
      raw: reliableCaps.map(c => `"${c.text}"`).slice(0, 3).join('\n') })

  if (row.number_doctors != null && row.number_doctors >= 5)
    green.push({ text: `${row.number_doctors} doctors on record`,
      field: 'dim_facility.number_doctors', raw: String(row.number_doctors) })

  if (row.capacity_beds != null && row.capacity_beds >= 50)
    green.push({ text: `${row.capacity_beds} beds capacity on record`,
      field: 'dim_facility.capacity_beds', raw: String(row.capacity_beds) })

  // ── Amber ──────────────────────────────────────────────────────────────
  const uncertainProcs = procedures.filter(p => p.reliability === 'Uncertain' &&
    careNeed.keywords.some(kw => (p.text?.toLowerCase() ?? '').includes(kw)))
  if (uncertainProcs.length > 0)
    amber.push({ text: `${careNeed.label} procedure claim is uncertain: ${uncertainProcs[0].reliability_reason ?? 'verification pending'}`,
      field: 'facility_procedure.reliability',
      raw: `"${uncertainProcs[0].reliability}" — ${uncertainProcs[0].reliability_reason ?? ''}` })

  if (matchingSpecs.length === 0 && reliableProcs.length === 0 && reliableEquip.length === 0)
    amber.push({ text: `No confirmed ${careNeed.label.toLowerCase()} specialty, procedure or equipment found in this record`,
      field: 'facility_specialty / facility_procedure / facility_equipment',
      raw: '(no matching reliable entry)' })

  if (['dialysis', 'emergency_surgery', 'cardiac'].includes(careNeed.id) && equipment.length === 0)
    amber.push({ text: `No equipment inventory documented — ${careNeed.label.toLowerCase()} machine count cannot be confirmed`,
      field: 'facility_equipment', raw: '(empty)' })

  if (row.number_doctors != null && row.number_doctors <= 2)
    amber.push({ text: `Thinly staffed: ${row.number_doctors} doctor${row.number_doctors === 1 ? '' : 's'} on record`,
      field: 'dim_facility.number_doctors', raw: String(row.number_doctors) })

  // ── Coral ──────────────────────────────────────────────────────────────
  if (!row.geo_is_valid)
    coral.push({ text: `Location data is invalid or unverified${row.pincode ? ` — pincode "${row.pincode}" could not be resolved` : ''}`,
      field: 'dim_facility.geo_is_valid',
      raw: `geo_is_valid: false, geo_source: ${row.geo_source ?? 'none'}` })
  else if (row.pincode && !isPinOk(row.pincode))
    coral.push({ text: `Postcode "${row.pincode}" is not a valid 6-digit Indian PIN — distance cannot be trusted`,
      field: 'dim_facility.pincode', raw: `"${row.pincode}"` })

  const unreliable = procedures.filter(p => p.reliability === 'Unreliable' &&
    careNeed.keywords.some(kw => (p.text?.toLowerCase() ?? '').includes(kw)))
  if (unreliable.length > 0)
    coral.push({ text: `${careNeed.label} procedure claim flagged as unreliable: ${unreliable[0].reliability_reason ?? ''}`,
      field: 'facility_procedure.reliability_reason', raw: `"${unreliable[0].text}"` })

  // ── Grey ───────────────────────────────────────────────────────────────
  grey.push(
    { text: 'Licence and accreditation status', field: 'not in dataset' },
    { text: `Current ${careNeed.label.toLowerCase()} availability`, field: 'not in dataset' },
    { text: 'Live service status today', field: 'not in dataset' },
  )

  return { green, amber, coral, grey }
}

// ---------------------------------------------------------------------------
// Main scoring function
// match_score = capabilityPts + proximityPts + freshnessPts - riskPenalty
// risk_penalty: red flags (coral) = −8 pts each, yellow (amber) = −3 pts each
// ---------------------------------------------------------------------------

export function scoreFacility(
  row: FacilityRow,
  careNeed: CareNeedDef,
  userLat: number | null,
  userLng: number | null,
): ScoredFacility {
  let distanceKm: number | null = null
  if (row.latitude_clean != null && row.longitude_clean != null &&
      userLat != null && userLng != null) {
    distanceKm = haversineKm(userLat, userLng, row.latitude_clean, row.longitude_clean)
  }

  const capabilityScore = capabilityPts(row, careNeed)
  const proximityScore  = proximityPts(distanceKm)
  const freshnessScore  = freshnessPts(row)

  const { green: greenEvidence, amber: amberEvidence, coral: coralEvidence, grey: greyEvidence } =
    generateEvidence(row, careNeed)

  const riskPenalty  = coralEvidence.length * 8 + amberEvidence.length * 3
  const overallScore = Math.max(0, Math.min(90,
    capabilityScore + proximityScore + freshnessScore - riskPenalty))

  const { level: confLevel, reason: confReason } = computeConfidence(row)
  const pinOk = isPinOk(row.pincode)

  const contacts = row.contacts ?? []
  const phone   = contacts.find(c => c.channel === 'phone')?.value ?? null
  const email   = contacts.find(c => c.channel === 'email')?.value ?? null
  const website = contacts.find(c => c.channel === 'web')?.value   ?? null

  return {
    ...row,
    phone, email, website,
    overallScore, capabilityScore, proximityScore, freshnessScore, riskPenalty, distanceKm,
    confLevel, confReason, pinOk,
    greenEvidence, amberEvidence, coralEvidence, greyEvidence,
    dotGreen: greenEvidence.length,
    dotAmber: amberEvidence.length,
    dotCoral: coralEvidence.length,
    dotGrey:  greyEvidence.length,
  }
}

export function sortFacilities(
  facilities: ScoredFacility[],
  sortBy: 'score' | 'distance',
): ScoredFacility[] {
  return [...facilities].sort((a, b) => {
    if (sortBy === 'distance') {
      if (a.distanceKm === null && b.distanceKm === null) return 0
      if (a.distanceKm === null) return 1
      if (b.distanceKm === null) return -1
      return a.distanceKm - b.distanceKm
    }
    return b.overallScore - a.overallScore
  })
}
