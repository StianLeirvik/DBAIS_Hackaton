import express from 'express'
import cors from 'cors'
import path from 'path'
import { fileURLToPath } from 'url'
import { getPool, DB_SCHEMA } from './db.ts'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const DIST = path.join(__dirname, '..', 'dist')

const app = express()
app.use(cors())
app.use(express.json())

const PORT = parseInt(process.env.PORT ?? '8080', 10)

// ---------------------------------------------------------------------------
// API routes
// ---------------------------------------------------------------------------

app.get('/api/health', async (_req, res) => {
  try {
    const pool = await getPool()
    const result = await pool.query<{ now: string }>('SELECT NOW() AS now')
    res.json({ ok: true, time: result.rows[0].now, schema: DB_SCHEMA })
  } catch (err) {
    res.status(500).json({ ok: false, error: String(err) })
  }
})

// ---------------------------------------------------------------------------
// Schema auto-detection (star vs flat) — cached after first call
// ---------------------------------------------------------------------------

type SchemaStrategy = 'star' | { flat: string } | 'none'
let _strategyCache: SchemaStrategy | null = null

async function detectSchemaStrategy(): Promise<SchemaStrategy> {
  if (_strategyCache !== null) return _strategyCache
  const pool = await getPool()
  const res = await pool.query<{ table_name: string }>(
    `SELECT table_name FROM information_schema.tables WHERE table_schema = $1`,
    [DB_SCHEMA],
  )
  const tables = new Set(res.rows.map(r => r.table_name))
  if (tables.has('dim_facility')) {
    _strategyCache = 'star'
  } else {
    const flat = ['silver_facilities', 'facilities', 'kie_facilities'].find(t => tables.has(t))
    _strategyCache = flat ? { flat } : 'none'
  }
  console.log(`[schema] ${DB_SCHEMA} →`, JSON.stringify(_strategyCache),
    '| tables:', [...tables].sort().join(', '))
  return _strategyCache
}

// ---------------------------------------------------------------------------
// Helper: postgres TEXT[] → string[]  (handles both real arrays and JSON strings)
// ---------------------------------------------------------------------------
function pgArr(v: unknown): string[] {
  if (Array.isArray(v)) return (v as unknown[]).map(String).filter(s => s && s !== 'null' && s.trim() !== '')
  if (typeof v !== 'string' || !v.trim() || v === 'null') return []
  try {
    const p = JSON.parse(v) as unknown
    return Array.isArray(p) ? (p as unknown[]).map(String).filter(s => s && s !== 'null') : []
  } catch { return [] }
}

// ---------------------------------------------------------------------------
// dim_facility normalisation  (wide denormalized table with _arr columns)
//
// The actual dim_facility has specialties_arr / procedure_arr / equipment_arr /
// capability_arr as TEXT[] plus flat contact columns — no separate joined tables.
// We convert these into the FacilityRow shape the frontend expects.
// ---------------------------------------------------------------------------
function normalizeStarRow(row: Record<string, unknown>): Record<string, unknown> {
  const str = (v: unknown): string | null => {
    if (v == null) return null; const s = String(v).trim()
    return s === '' || s === 'null' ? null : s
  }
  const confBase = typeof row.evidence_strength === 'number'
    ? (row.evidence_strength as number) : 0.7

  const officialPhone   = str(row.official_phone)
  const officialWebsite = str(row.official_website)

  const contacts: object[] = []
  if (officialPhone)   contacts.push({ channel: 'phone', value: officialPhone,   is_official: true })
  for (const ph of pgArr(row.phones_arr))
    if (ph !== officialPhone) contacts.push({ channel: 'phone', value: ph, is_official: false })
  const email = str(row.email)
  if (email) contacts.push({ channel: 'email', value: email, is_official: true })
  if (officialWebsite) contacts.push({ channel: 'web',   value: officialWebsite, is_official: true })
  for (const url of pgArr(row.websites_arr))
    if (url !== officialWebsite) contacts.push({ channel: 'web', value: url, is_official: false })
  const fb = str(row.facebook_link)
  if (fb) contacts.push({ channel: 'fb', value: fb, is_official: false })

  const specialties = pgArr(row.specialties_arr).map(code => ({
    specialty_code: code, display_name: code, mention_count: 1, confidence: confBase,
  }))

  const UNVERIFIED = { reliability: 'Uncertain',
    reliability_reason: 'Catalog array field — verify availability by phone',
    url: null, is_reliable: false }
  const procedures   = pgArr(row.procedure_arr).filter(t => t.length > 2)
    .map(text => ({ text, tag: null, confidence: 0.6, ...UNVERIFIED }))
  const equipment    = pgArr(row.equipment_arr).filter(t => t.length > 2)
    .map(text => ({ text, tag: null, confidence: 0.6, ...UNVERIFIED }))
  const capabilities = pgArr(row.capability_arr).filter(t => t.length > 2)
    .map(text => ({ text, tag: null, confidence: 0.7, ...UNVERIFIED }))

  // Sources come from the facility_source JOIN (_src_urls / _src_officials arrays).
  // Falls back to source_urls_arr (denormalized column) if the join returned nothing.
  const joinedUrls     = pgArr(row._src_urls)
  const joinedOfficials = Array.isArray(row._src_officials)
    ? (row._src_officials as unknown[]).map(v => v === true || v === 't' || v === 'true')
    : []
  let sources: { url: string; is_official: boolean }[]
  if (joinedUrls.length > 0) {
    sources = joinedUrls.map((url, i) => ({ url, is_official: joinedOfficials[i] ?? false }))
  } else {
    // Fallback: denormalized array, no official info available
    sources = pgArr(row.source_urls_arr).map(url => ({ url, is_official: false }))
  }

  return {
    facility_id:        row.facility_id,
    cluster_id:         row.cluster_key ?? null,
    name_clean:         row.name_clean,
    facility_type:      row.facility_type,
    operator_type:      row.operator_type,
    year_established:   row.year_established,
    capacity_beds:      row.capacity_beds,
    number_doctors:     row.number_doctors,
    city:               row.city,
    state:              row.state,
    pincode:            row.pincode,
    latitude_clean:     row.latitude_clean,
    longitude_clean:    row.longitude_clean,
    geo_is_valid:       row.geo_is_valid,
    geo_source:         row.geo_source,
    evidence_band:      row.evidence_band,
    data_quality_score: row.data_quality_score,
    contacts, specialties, procedures, equipment, capabilities, sources,
  }
}

// ---------------------------------------------------------------------------
// Flat-row normalisation  (legacy KIE source table → FacilityRow wire format)
//
// The raw KIE/Silver layer uses:
//   unique_id, name, facilityTypeId, address_city, address_stateOrRegion,
//   latitude/longitude as strings, specialties as JSON string of CODE strings, etc.
// ---------------------------------------------------------------------------

function normalizeFlatRow(row: Record<string, unknown>): Record<string, unknown> {
  const str = (v: unknown): string | null => {
    if (v == null) return null
    const s = String(v).trim()
    return s === '' || s === 'null' ? null : s
  }
  const num = (v: unknown): number | null => {
    if (v == null) return null
    const s = String(v).trim()
    if (!s || s === 'null') return null
    const n = parseFloat(s)
    return isNaN(n) ? null : n
  }
  const trunc = (v: unknown): number | null => {
    const n = num(v)
    return n != null ? Math.trunc(n) : null
  }
  const parseArr = (v: unknown): string[] => {
    if (!v) return []
    if (Array.isArray(v)) return (v as unknown[]).map(String).filter(s => s && s !== 'null')
    if (typeof v !== 'string' || !v.trim() || v === 'null') return []
    try {
      const p = JSON.parse(v) as unknown
      return Array.isArray(p) ? (p as unknown[]).map(String).filter(s => s && s !== 'null') : []
    } catch { return [] }
  }

  const lat = num(row.latitude)
  const lng = num(row.longitude)
  // India bounding box sanity check
  const geoValid = lat != null && lng != null
    && lat >= 6 && lat <= 38 && lng >= 68 && lng <= 98

  // Build contacts array from flat phone/email/website fields
  const officialPhone   = str(row.officialPhone)
  const officialWebsite = str(row.officialWebsite)
  const contacts: object[] = []
  if (officialPhone) contacts.push({ channel: 'phone', value: officialPhone, is_official: true })
  for (const ph of parseArr(row.phone_numbers)) {
    if (ph !== officialPhone) contacts.push({ channel: 'phone', value: ph, is_official: false })
  }
  const email = str(row.email)
  if (email) contacts.push({ channel: 'email', value: email, is_official: true })
  if (officialWebsite) contacts.push({ channel: 'web', value: officialWebsite, is_official: true })
  for (const url of parseArr(row.websites)) {
    if (url !== officialWebsite) contacts.push({ channel: 'web', value: url, is_official: false })
  }

  // Specialty codes ("dialysis", "gynecologyAndObstetrics", …) become SpecialtyRow objects.
  // display_name = code so keyword matching ("gynecolog".includes works on "gynecologyAndObstetrics").
  const specialties = parseArr(row.specialties).map(code => ({
    specialty_code: code, display_name: code, mention_count: 1, confidence: 0.7,
  }))

  const UNVERIFIED = { reliability: 'Uncertain', reliability_reason: 'Flat catalog record — verify by phone', url: null, is_reliable: false }
  const procedures  = parseArr(row.procedure).filter(t => t.length > 2).map(text =>
    ({ text, tag: null, confidence: 0.6, ...UNVERIFIED }))
  const equipment   = parseArr(row.equipment).filter(t => t.length > 2).map(text =>
    ({ text, tag: null, confidence: 0.6, ...UNVERIFIED }))
  const capabilities = parseArr(row.capability).filter(t => t.length > 2).map(text =>
    ({ text, tag: null, confidence: 0.7, ...UNVERIFIED }))

  return {
    // ID — source table uses "unique_id", gold layer uses "facility_id"
    facility_id:        str(row.unique_id) ?? str(row.facility_id) ?? '',
    cluster_id:         str(row.cluster_id),
    name_clean:         str(row.name) ?? str(row.name_clean) ?? 'Unknown',
    facility_type:      str(row.facilityTypeId) ?? str(row.facility_type),
    operator_type:      str(row.organization_type) ?? str(row.operator_type),
    year_established:   trunc(row.yearEstablished),
    capacity_beds:      trunc(row.capacity),
    number_doctors:     trunc(row.numberDoctors),
    city:               str(row.address_city)         ?? str(row.city),
    state:              str(row.address_stateOrRegion) ?? str(row.state),
    pincode:            str(row.address_zipOrPostcode) ?? str(row.pincode),
    latitude_clean:     lat,
    longitude_clean:    lng,
    geo_is_valid:       geoValid,
    geo_source:         geoValid ? 'raw' : 'none',
    evidence_band:      null,   // not in flat schema
    data_quality_score: null,   // not in flat schema
    contacts, specialties, procedures, equipment, capabilities,
    sources: parseArr(row.websites).map(url => ({ url, is_official: url === officialWebsite })),
  }
}

/**
 * Search facilities by location (city, state or pincode).
 *
 * GET /api/facilities/search?location=Jaipur&limit=200
 */
app.get('/api/facilities/search', async (req, res) => {
  const location = String(req.query.location ?? '').trim()
  const limit = Math.min(parseInt(String(req.query.limit ?? '200'), 10), 500)

  if (!location) { res.json([]); return }

  try {
    const pool     = await getPool()
    const strategy = await detectSchemaStrategy()
    const likeParam = `%${location}%`

    if (strategy === 'none') { res.json([]); return }

    // ── Flat-table path ────────────────────────────────────────────────────
    if (strategy !== 'star') {
      const tbl = strategy.flat
      const result = await pool.query(
        `SELECT * FROM ${DB_SCHEMA}."${tbl}"
         WHERE LOWER("address_city")            LIKE LOWER($1)
            OR LOWER("address_stateOrRegion")   LIKE LOWER($1)
            OR "address_zipOrPostcode" = $2
         LIMIT $3`,
        [likeParam, location, limit],
      )
      res.json(result.rows.map(normalizeFlatRow))
      return
    }

    // ── dim_facility path (wide denormalized table) ────────────────────────
    // Correlated subqueries fetch facility_source rows without needing GROUP BY.
    const result = await pool.query(
      `SELECT f.*,
              (SELECT array_agg(fs.source_url)  FROM ${DB_SCHEMA}.facility_source fs WHERE fs.facility_id = f.facility_id AND fs.source_url IS NOT NULL) AS _src_urls,
              (SELECT array_agg(fs.is_official) FROM ${DB_SCHEMA}.facility_source fs WHERE fs.facility_id = f.facility_id AND fs.source_url IS NOT NULL) AS _src_officials
       FROM ${DB_SCHEMA}.dim_facility f
       WHERE LOWER(f.city)         LIKE LOWER($1)
          OR LOWER(f.state)        LIKE LOWER($1)
          OR LOWER(f.pin_district) LIKE LOWER($1)
          OR f.pincode = $2
       LIMIT $3`,
      [likeParam, location, limit],
    )
    res.json(result.rows.map(normalizeStarRow))
  } catch (err) {
    console.error('[/api/facilities/search]', err)
    res.status(500).json({ error: String(err) })
  }
})

/**
 * Geocode a city / district name to lat/lng using MEDIAN coordinates.
 *
 * Tier 1: dim_pincode — median of postal centroid_lat/centroid_long per district
 *         (165k records, purpose-built geo reference, outlier-resistant).
 * Tier 2: dim_facility — median of facility coords where city matches exactly.
 * Tier 3: dim_facility — median where pin_district matches exactly.
 * Tier 4: dim_facility — LIKE fallback on city/pin_district.
 *
 * GET /api/geocode-city?q=Jaipur
 */
app.get('/api/geocode-city', async (req, res) => {
  const q = String(req.query.q ?? '').trim()
  if (!q) { res.json(null); return }
  try {
    const pool     = await getPool()
    const strategy = await detectSchemaStrategy()
    if (strategy !== 'star') { res.json(null); return }

    // Helper: get the median value from an ordered array at the middle index.
    // Uses OFFSET n/2 LIMIT 1 which works on all PostgreSQL-compatible engines.
    async function medianGeo(
      table: string,
      latCol: string,
      lngCol: string,
      whereClause: string,
      params: string[],
    ): Promise<{ lat: number; lng: number } | null> {
      const countRes = await pool.query<{ cnt: number }>(
        `SELECT COUNT(*) AS cnt FROM ${DB_SCHEMA}.${table}
         WHERE ${latCol} IS NOT NULL AND ${lngCol} IS NOT NULL AND (${whereClause})`,
        params,
      )
      const cnt = Number(countRes.rows[0]?.cnt ?? 0)
      if (cnt < 3) return null
      const mid = Math.floor(cnt / 2)

      const latRes = await pool.query<{ v: number }>(
        `SELECT ${latCol} AS v FROM ${DB_SCHEMA}.${table}
         WHERE ${latCol} IS NOT NULL AND ${lngCol} IS NOT NULL AND (${whereClause})
         ORDER BY ${latCol} OFFSET ${mid} LIMIT 1`,
        params,
      )
      const lngRes = await pool.query<{ v: number }>(
        `SELECT ${lngCol} AS v FROM ${DB_SCHEMA}.${table}
         WHERE ${latCol} IS NOT NULL AND ${lngCol} IS NOT NULL AND (${whereClause})
         ORDER BY ${lngCol} OFFSET ${mid} LIMIT 1`,
        params,
      )
      const lat = Number(latRes.rows[0]?.v)
      const lng = Number(lngRes.rows[0]?.v)
      if (isNaN(lat) || isNaN(lng)) return null
      return { lat, lng }
    }

    // ── Tier 1: dim_pincode district centroid (purpose-built geo reference) ──
    const t1 = await medianGeo(
      'dim_pincode', 'centroid_lat', 'centroid_long',
      `LOWER(district) = LOWER($1)`, [q],
    )
    if (t1) { res.json(t1); return }

    // ── Tier 2+: dim_facility median coordinates ──
    const tiers: [string, string[]][] = [
      [`LOWER(city) = LOWER($1) AND geo_is_valid = true`, [q]],
      [`LOWER(pin_district) = LOWER($1) AND geo_is_valid = true`, [q]],
      [`(LOWER(city) LIKE LOWER($1) OR LOWER(pin_district) LIKE LOWER($1)) AND geo_is_valid = true`, [`%${q}%`]],
    ]

    for (const [condition, params] of tiers) {
      const result = await medianGeo(
        'dim_facility', 'latitude_clean', 'longitude_clean',
        condition, params,
      )
      if (result) { res.json(result); return }
    }
    res.json(null)
  } catch {
    res.json(null)
  }
})

/**
 * Geocode a PIN code to lat/lng using the India Post Pincodes table.
 *
 * GET /api/pincodes/:code
 */
app.get('/api/pincodes/:code', async (req, res) => {
  const code = String(req.params.code).trim()
  try {
    const pool = await getPool()
    const result = await pool.query<{ lat: number; lng: number }>(
      `SELECT centroid_lat AS lat, centroid_long AS lng
       FROM ${DB_SCHEMA}.dim_pincode
       WHERE pincode = $1
       LIMIT 1`,
      [code],
    )
    if (result.rows.length === 0) { res.json(null); return }
    res.json(result.rows[0])
  } catch {
    res.json(null)
  }
})

/**
 * Shortlist persistence (best-effort — silent if user_* tables not yet created)
 *
 * GET    /api/shortlist?user_id=xxx
 * POST   /api/shortlist/item          { user_id, facility_id, distance_km }
 * DELETE /api/shortlist/item/:id?user_id=xxx
 */
app.get('/api/shortlist', async (req, res) => {
  const user_id = String(req.query.user_id ?? '').trim()
  if (!user_id) { res.json([]); return }
  try {
    const pool = await getPool()
    const result = await pool.query(
      `SELECT i.facility_id, i.distance_km, i.added_at
       FROM ${DB_SCHEMA}.user_shortlist_item i
       JOIN ${DB_SCHEMA}.user_shortlist s ON s.shortlist_id = i.shortlist_id
       WHERE s.user_id = $1`,
      [user_id],
    )
    res.json(result.rows)
  } catch { res.json([]) }
})

app.post('/api/shortlist/item', async (req, res) => {
  const { user_id, facility_id, distance_km } = req.body as Record<string, unknown>
  if (!user_id || !facility_id) { res.status(400).json({ error: 'user_id and facility_id required' }); return }
  try {
    const pool = await getPool()
    // Ensure shortlist row exists
    const sl = await pool.query(
      `SELECT shortlist_id FROM ${DB_SCHEMA}.user_shortlist WHERE user_id = $1 LIMIT 1`,
      [user_id],
    )
    let shortlist_id: string
    if (sl.rows.length === 0) {
      shortlist_id = `sl_${String(user_id).slice(0, 8)}_${Date.now()}`
      await pool.query(
        `INSERT INTO ${DB_SCHEMA}.user_shortlist (shortlist_id, user_id, name, created_at)
         VALUES ($1, $2, 'My Shortlist', NOW())`,
        [shortlist_id, user_id],
      )
    } else {
      shortlist_id = sl.rows[0].shortlist_id as string
    }
    // Delete existing then insert (avoids relying on specific UNIQUE constraint)
    await pool.query(
      `DELETE FROM ${DB_SCHEMA}.user_shortlist_item WHERE shortlist_id = $1 AND facility_id = $2`,
      [shortlist_id, facility_id],
    )
    await pool.query(
      `INSERT INTO ${DB_SCHEMA}.user_shortlist_item (shortlist_id, facility_id, distance_km, added_at)
       VALUES ($1, $2, $3, NOW())`,
      [shortlist_id, facility_id, distance_km ?? null],
    )
    res.json({ ok: true })
  } catch (err) { res.status(500).json({ error: String(err) }) }
})

app.delete('/api/shortlist/item/:facilityId', async (req, res) => {
  const user_id    = String(req.query.user_id ?? '').trim()
  const facility_id = String(req.params.facilityId).trim()
  if (!user_id) { res.status(400).json({ error: 'user_id required' }); return }
  try {
    const pool = await getPool()
    await pool.query(
      `DELETE FROM ${DB_SCHEMA}.user_shortlist_item
       WHERE facility_id = $2
         AND shortlist_id IN (
           SELECT shortlist_id FROM ${DB_SCHEMA}.user_shortlist WHERE user_id = $1
         )`,
      [user_id, facility_id],
    )
    res.json({ ok: true })
  } catch (err) { res.status(500).json({ error: String(err) }) }
})

// ---------------------------------------------------------------------------
// Serve built Vue frontend + SPA fallback
// ---------------------------------------------------------------------------
app.use(express.static(DIST))

app.get('*', (_req, res) => {
  res.sendFile(path.join(DIST, 'index.html'))
})

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------
app.listen(PORT, '0.0.0.0', () => {
  console.log(`CareMap server listening on port ${PORT}`)
  console.log(`Database schema: ${DB_SCHEMA}`)
})
