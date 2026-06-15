<script setup lang="ts">
import { Info, Link2 } from '@lucide/vue'
import { computed } from 'vue'
import type { Evidence } from '../types'

const props = defineProps<{
  item: Evidence
  marker: string
  markerColor: string
  citeId: string
  expandedCites: Set<string>
  isGrey?: boolean
}>()

const emit = defineEmits<{ (e: 'toggle-cite', id: string): void }>()

const isOpen = () => props.expandedCites.has(props.citeId)

const FIELD_LABELS: Record<string, string> = {
  'facility_specialty.display_name':                         'Specialty records',
  'facility_procedure.procedure_text':                       'Procedure records',
  'facility_procedure.reliability':                          'Quality flag',
  'facility_procedure.reliability_reason':                   'Reliability note',
  'facility_equipment.equipment_text':                       'Equipment records',
  'facility_capability.capability_text':                     'Capability records',
  'dim_facility.number_doctors':                             'Staffing data',
  'dim_facility.capacity_beds':                              'Capacity data',
  'dim_facility.geo_is_valid':                               'Location data',
  'dim_facility.pincode':                                    'Postcode data',
  'facility_specialty / facility_procedure / facility_equipment': 'Capability coverage',
  'facility_equipment':                                      'Equipment inventory',
  'not in dataset':                                          'Not in catalog',
}
const friendlyField = computed(() => FIELD_LABELS[props.item.field] ?? props.item.field)
</script>

<template>
  <div class="text-sm space-y-1">
    <div class="flex items-start gap-2">
      <span class="shrink-0 font-semibold text-[13px] leading-snug" :style="{ color: markerColor }">{{ marker }}</span>
      <span style="color:var(--ink)">{{ item.text }}</span>
    </div>

    <button
      v-if="item.raw !== undefined || item.field"
      class="ml-4 text-xs flex items-center gap-1 font-medium"
      :style="{ color: isGrey ? 'var(--grey)' : 'var(--teal)' }"
      @click.stop="emit('toggle-cite', citeId)"
    >
      <Info v-if="isGrey" :size="11" />
      <Link2 v-else :size="11" />
      {{ isGrey ? 'Why unknown' : (isOpen() ? 'Hide source text' : 'Show source text') }}
    </button>

    <div
      v-if="isOpen()"
      class="ml-4 p-3 rounded-lg text-xs"
      :style="{ background: isGrey ? 'var(--grey-tint)' : 'var(--paper)', border: '1px solid var(--line)' }"
    >
      <div class="font-semibold mb-1" style="color:var(--ink-soft)">Source: {{ friendlyField }}</div>
      <div v-if="isGrey" style="color:var(--ink-soft)">Not present anywhere in the catalog. Confirm directly with the facility.</div>
      <pre v-else-if="item.raw" class="font-mono text-xs overflow-x-auto whitespace-pre-wrap" style="color:var(--ink)">{{ item.raw }}</pre>
      <div v-if="item.urls && item.urls.length" class="mt-2 space-y-1">
        <div class="font-semibold" style="color:var(--ink-soft)">Source links</div>
        <a
          v-for="url in item.urls"
          :key="url"
          :href="url"
          target="_blank"
          rel="noopener"
          class="block text-xs truncate"
          style="color:var(--teal)"
        >{{ url }}</a>
      </div>
    </div>
  </div>
</template>
