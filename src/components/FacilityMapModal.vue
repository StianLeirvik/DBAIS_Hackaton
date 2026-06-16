<script setup lang="ts">
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import { ref, watch, onUnmounted, nextTick } from 'vue'
import { X } from '@lucide/vue'
import type { ScoredFacility } from '../types'

const props = defineProps<{
  open: boolean
  facilities: ScoredFacility[]
  selected: ScoredFacility | null
  userLat: number | null
  userLng: number | null
  locationLabel: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'select', id: string): void
}>()

const mapEl = ref<HTMLDivElement | null>(null)
let map: L.Map | null = null

// Persistent marker references — so we can update styles without rebuilding
const markerRefs = new Map<string, L.CircleMarker>()
let prevSelectedId: string | null = null

function scoreColor(score: number): { fill: string; stroke: string } {
  if (score >= 65) return { fill: '#0f7d6b', stroke: '#0a5c4e' }
  if (score >= 35) return { fill: '#b2790f', stroke: '#8a5e0c' }
  return { fill: '#cf4a26', stroke: '#a33b1e' }
}

function markerOpts(f: ScoredFacility, selected: boolean): L.CircleMarkerOptions {
  const { fill, stroke } = scoreColor(f.overallScore)
  return selected
    ? { radius: 16, color: '#16233f', fillColor: fill, fillOpacity: 0.95, weight: 3 }
    : { radius: 6,  color: stroke,    fillColor: fill, fillOpacity: 0.45, weight: 1 }
}

function popupHtml(f: ScoredFacility) {
  return (
    `<div style="min-width:150px"><strong>${f.name_clean}</strong><br>` +
    `<span style="color:#666;font-size:12px">${f.city ?? ''}, ${f.state ?? ''}</span><br>` +
    `<span style="font-size:12px">Score: <strong>${f.overallScore}</strong></span></div>`
  )
}

function buildMap() {
  if (!mapEl.value || map) return
  markerRefs.clear()
  prevSelectedId = null

  const selId    = props.selected?.facility_id ?? null
  const centerLat = props.userLat ?? 20.5937
  const centerLng = props.userLng ?? 78.9629

  map = L.map(mapEl.value, { zoomControl: true, attributionControl: false })
    .setView([centerLat, centerLng], props.userLat != null ? 6 : 5)

  L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    subdomains: 'abcd',
    maxZoom: 19,
  }).addTo(map)

  // Search-area ring — radius matches the 300 km proximity scoring horizon
  if (props.userLat != null && props.userLng != null) {
    L.circle([props.userLat, props.userLng], {
      radius: 300_000,
      color: '#16233f', fillColor: '#16233f', fillOpacity: 0.04,
      weight: 1.5, dashArray: '6 4',
    }).addTo(map)

    L.circleMarker([props.userLat, props.userLng], {
      radius: 7, color: '#fff', fillColor: '#16233f', fillOpacity: 1, weight: 2,
    })
      .bindTooltip(props.locationLabel || 'Search location', { direction: 'top' })
      .addTo(map)
  }

  // All facility markers (dimmed first, selected on top via z-index)
  for (const f of props.facilities) {
    if (f.latitude_clean == null || f.longitude_clean == null) continue
    const isSel = f.facility_id === selId
    const marker = L.circleMarker([f.latitude_clean, f.longitude_clean], markerOpts(f, isSel))
      .bindPopup(popupHtml(f))
      .on('click', () => emit('select', f.facility_id))
      .addTo(map!)
    if (isSel) {
      marker.bindTooltip(String(f.overallScore), {
        permanent: true, direction: 'center', className: 'map-score-label',
      })
    }
    markerRefs.set(f.facility_id, marker)
  }

  // Fly to selected facility on open
  const sel = props.selected
  if (sel?.latitude_clean != null && sel?.longitude_clean != null) {
    map.flyTo([sel.latitude_clean, sel.longitude_clean], 13, { animate: true, duration: 1.0 })
  }

  prevSelectedId = selId
}

// Update marker styles + fly to without rebuilding the map
function updateSelection(newId: string | null) {
  if (!map) return

  // Reset old selected marker
  if (prevSelectedId) {
    const m = markerRefs.get(prevSelectedId)
    const f = props.facilities.find(x => x.facility_id === prevSelectedId)
    if (m && f) {
      m.setStyle(markerOpts(f, false))
      m.unbindTooltip()
    }
  }

  // Apply new selected marker
  if (newId) {
    const m = markerRefs.get(newId)
    const f = props.facilities.find(x => x.facility_id === newId)
    if (m && f) {
      m.setStyle(markerOpts(f, true))
      m.bindTooltip(String(f.overallScore), {
        permanent: true, direction: 'center', className: 'map-score-label',
      })
      if (f.latitude_clean != null && f.longitude_clean != null) {
        map.flyTo([f.latitude_clean, f.longitude_clean], 13, { animate: true, duration: 0.8 })
      }
    }
  }

  prevSelectedId = newId
}

function teardown() {
  if (map) { map.remove(); map = null }
  markerRefs.clear()
  prevSelectedId = null
}

// Build once on open, teardown on close
watch(
  () => props.open,
  async (open) => {
    if (open) {
      await nextTick()
      buildMap()
      map?.invalidateSize()
    } else {
      teardown()
    }
  },
)

// Selection changes while map is open: update imperatively (no rebuild)
watch(
  () => props.selected?.facility_id,
  (newId) => {
    if (props.open && map) updateSelection(newId ?? null)
  },
)

onUnmounted(teardown)
</script>

<template>
  <Teleport to="body">
    <Transition name="map-fade">
      <div
        v-if="open"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
        style="background:rgba(22,35,63,0.6)"
        @click.self="$emit('close')"
      >
        <div
          class="rounded-2xl overflow-hidden flex flex-col"
          style="width:min(680px,97vw);max-height:92vh;background:white;box-shadow:0 24px 64px rgba(0,0,0,0.28)"
        >
          <!-- Header -->
          <div class="px-5 py-4 flex items-start gap-3" style="border-bottom:1px solid var(--line)">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <h3 class="font-serif font-semibold text-lg leading-tight" style="color:var(--ink)">
                  {{ selected?.name_clean ?? 'All candidates' }}
                </h3>
                <span
                  class="shrink-0 text-xs font-bold px-2 py-0.5 rounded"
                  style="background:#fffbeb;color:#b2790f;border:1px solid #fde68a"
                >ILLUSTRATIVE</span>
              </div>
              <p v-if="selected" class="text-sm mt-0.5" style="color:var(--ink-soft)">
                {{ selected.city }}, {{ selected.state }}
                <template v-if="selected.distanceKm != null">
                  · {{ selected.distanceKm.toFixed(1) }} km
                  · ~{{ Math.round(selected.distanceKm * 3) }} min
                </template>
              </p>
            </div>
            <button
              class="shrink-0 p-1.5 rounded-lg transition-colors hover:bg-gray-100"
              @click="$emit('close')"
            >
              <X :size="18" style="color:var(--ink-soft)" />
            </button>
          </div>

          <!-- Legend -->
          <div
            class="px-5 py-2 flex items-center gap-4 text-xs flex-wrap"
            style="border-bottom:1px solid var(--line);color:var(--ink-soft)"
          >
            <span class="flex items-center gap-1.5">
              <span class="w-2.5 h-2.5 rounded-full inline-block" style="background:var(--teal)" />
              High
            </span>
            <span class="flex items-center gap-1.5">
              <span class="w-2.5 h-2.5 rounded-full inline-block" style="background:var(--amber)" />
              Medium
            </span>
            <span class="flex items-center gap-1.5">
              <span class="w-2.5 h-2.5 rounded-full inline-block" style="background:var(--coral)" />
              Low
            </span>
            <span v-if="locationLabel" class="flex items-center gap-1.5">
              <span style="color:var(--ink);font-size:15px">♦</span>
              {{ locationLabel }}
            </span>
          </div>

          <!-- Map -->
          <div ref="mapEl" style="height:480px;flex:0 0 480px" />

          <!-- Footer note -->
          <div
            class="px-5 py-3 text-xs leading-relaxed"
            style="background:#f9f9f7;border-top:1px solid var(--line);color:var(--ink-soft)"
          >
            <strong style="color:var(--ink)">Real record coordinates.</strong>
            The highlighted marker is the selected facility at its actual latitude and longitude;
            others are dimmed for context. In production results cluster inside your search area,
            but the stand-in records span India, outside the illustrative
            {{ locationLabel || 'search' }} catchment. Tap any marker to switch.
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style>
.map-score-label {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  font-weight: 700;
  font-size: 12px;
  color: white;
  padding: 0;
}
.map-score-label::before { display: none !important; }
.map-fade-enter-active, .map-fade-leave-active { transition: opacity 0.2s ease; }
.map-fade-enter-from, .map-fade-leave-to { opacity: 0; }
</style>
