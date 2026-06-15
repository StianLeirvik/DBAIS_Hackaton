<script setup lang="ts">
import { computed } from 'vue'
import { MapPin, Map } from '@lucide/vue'
import type { ScoredFacility, ConfidenceLevel } from '../types'

interface Session {
  saved: boolean
  note: string
  verified: boolean
  dismissed: boolean
}

const props = defineProps<{
  facility: ScoredFacility
  rank: number
  selected: boolean
  effConfidence: ConfidenceLevel
  session: Session
}>()

const emit = defineEmits<{
  (e: 'select'): void
  (e: 'view-map'): void
}>()

const confLabel: Record<ConfidenceLevel, string> = { high: 'High', med: 'Medium', low: 'Low' }

const confStyle = computed((): Record<string, string> => {
  if (props.effConfidence === 'high') return { background: 'var(--teal-tint)', color: 'var(--teal)' }
  if (props.effConfidence === 'med')  return { background: 'var(--amber-tint)', color: 'var(--amber)' }
  return { background: 'var(--coral-tint)', color: 'var(--coral)' }
})

const dotStyle = computed(() => ({
  background: props.effConfidence === 'high' ? 'var(--teal)' :
              props.effConfidence === 'med'  ? 'var(--amber)' : 'var(--coral)',
}))

const metaLine = computed(() => {
  const parts = [
    props.facility.facility_type ?? 'Facility',
    props.facility.operator_type ?? null,
    props.facility.city ?? null,
    props.facility.state ?? null,
  ].filter(Boolean)
  return parts.join(' · ')
})

const distLabel = computed(() => {
  if (props.facility.distanceKm === null) return null
  const km = props.facility.distanceKm
  if (km < 1) return `${Math.round(km * 1000)} m`
  return `${km.toFixed(1)} km`
})
</script>

<template>
  <article
    class="rounded-xl cursor-pointer transition-all select-none"
    style="background:white;border:1px solid var(--line)"
    :style="[
      selected ? { border: '2px solid var(--ink)', boxShadow: '0 2px 12px rgba(22,35,63,0.12)' } : {},
      session.dismissed ? { opacity: 0.45 } : {},
    ]"
    @click="emit('select')"
  >
    <!-- Top row -->
    <div class="flex items-start gap-3 px-4 pt-4 pb-3">
      <!-- Rank -->
      <div class="font-serif font-semibold text-2xl leading-none shrink-0 pt-0.5" style="color:var(--ink-soft);min-width:24px">
        {{ rank }}
      </div>

      <!-- Name + meta + confidence -->
      <div class="flex-1 min-w-0 space-y-1">
        <div class="font-serif font-semibold text-[17px] leading-snug" style="color:var(--ink)">
          {{ facility.name_clean || 'Unnamed Facility' }}
        </div>
        <div class="text-xs leading-snug" style="color:var(--ink-soft)">{{ metaLine }}</div>
        <div class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold mt-1" :style="confStyle">
          <span class="w-1.5 h-1.5 rounded-full shrink-0" :style="dotStyle" />
          {{ confLabel[effConfidence] }} confidence
          <template v-if="session.verified"> · phone-verified</template>
        </div>
      </div>

      <!-- Score -->
      <div class="flex flex-col items-center shrink-0">
        <div class="font-serif font-bold text-3xl leading-none" style="color:var(--ink)">{{ facility.overallScore }}</div>
        <div class="text-[10px] font-semibold tracking-widest uppercase mt-0.5" style="color:var(--ink-soft)">Match</div>
      </div>
    </div>

    <!-- Footer -->
    <div class="flex items-center gap-3 px-4 pb-3 pt-1 flex-wrap" style="border-top:1px solid var(--line)">
      <!-- Distance -->
      <span v-if="distLabel" class="flex items-center gap-1 text-xs" style="color:var(--ink-soft)">
        <MapPin :size="12" />
        {{ distLabel }}
        <span class="text-[10px] px-1.5 py-0.5 rounded font-semibold ml-1" style="background:#f0f4ff;color:#4a6fbd">ILLUSTRATIVE</span>
      </span>

      <!-- Map button -->
      <button
        class="flex items-center gap-1 text-[11px] font-medium px-2 py-1 rounded-lg transition-colors"
        style="color:var(--ink-soft);background:var(--grey-tint)"
        @click.stop="emit('view-map')"
      >
        <Map :size="11" /> Map
      </button>

      <!-- Evidence dots -->
      <div class="flex items-center gap-2 ml-auto">
        <span v-if="facility.dotGreen > 0" class="flex items-center gap-1 text-[11px]">
          <span class="w-2 h-2 rounded-full" style="background:var(--teal)" />{{ facility.dotGreen }}
        </span>
        <span v-if="facility.dotAmber > 0" class="flex items-center gap-1 text-[11px]">
          <span class="w-2 h-2 rounded-full" style="background:var(--amber)" />{{ facility.dotAmber }}
        </span>
        <span v-if="facility.dotCoral > 0" class="flex items-center gap-1 text-[11px]">
          <span class="w-2 h-2 rounded-full" style="background:var(--coral)" />{{ facility.dotCoral }}
        </span>
        <span v-if="facility.dotGrey > 0" class="flex items-center gap-1 text-[11px]">
          <span class="w-2 h-2 rounded-full" style="background:var(--grey)" />{{ facility.dotGrey }}
        </span>
      </div>
    </div>
  </article>
</template>
