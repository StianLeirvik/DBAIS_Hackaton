<script setup lang="ts">
import { ref, computed } from 'vue'
import { Check, Phone, PhoneCall, Bookmark, Pencil } from '@lucide/vue'
import type { ScoredFacility, ConfidenceLevel } from '../types'
import EvidenceItem from './EvidenceItem.vue'

interface Session {
  saved: boolean
  note: string
  verified: boolean
  dismissed: boolean
}

const props = defineProps<{
  facility: ScoredFacility
  session: Session
  effConfidence: ConfidenceLevel
}>()

const emit = defineEmits<{
  (e: 'toggle-save'): void
  (e: 'toggle-verify'): void
  (e: 'toggle-dismiss'): void
  (e: 'save-note', note: string): void
}>()

const TODAY = new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
const confLabel: Record<ConfidenceLevel, string> = { high: 'High', med: 'Medium', low: 'Low' }

const showBreakdown = ref(false)
const showNoteBox = ref(false)
const noteText = ref(props.session.note)
const expandedCites = ref<Set<string>>(new Set())

function toggleCite(key: string) {
  if (expandedCites.value.has(key)) expandedCites.value.delete(key)
  else expandedCites.value.add(key)
}

function saveNote() {
  emit('save-note', noteText.value.trim())
  showNoteBox.value = false
}

const confBandStyle = computed(() => {
  if (props.effConfidence === 'high') return { background: 'var(--teal-tint)', color: 'var(--teal)' }
  if (props.effConfidence === 'med')  return { background: 'var(--amber-tint)', color: 'var(--amber)' }
  return { background: 'var(--coral-tint)', color: 'var(--coral)' }
})

const metaParts = computed(() => {
  const f = props.facility
  const parts: string[] = []
  if (f.facility_type) parts.push(f.facility_type)
  if (f.operator_type) parts.push(f.operator_type)
  if (f.year_established) parts.push(`Est. ${f.year_established}`)
  else parts.push('Year founded not on record')
  if (f.city) parts.push(f.city)
  if (f.state) parts.push(f.state)
  return parts
})

const phone = computed(() => props.facility.phone)
</script>

<template>
  <div class="rounded-2xl overflow-hidden" style="background:white;border:1px solid var(--line);max-height:calc(100vh - 120px);overflow-y:auto">

    <!-- Head -->
    <div class="px-5 pt-5 pb-4" style="border-bottom:1px solid var(--line)">
      <div class="font-serif font-semibold text-[22px] leading-snug mb-2" style="color:var(--ink)">
        {{ facility.name_clean }}
      </div>
      <div class="flex flex-wrap gap-x-3 gap-y-1 text-xs mb-3" style="color:var(--ink-soft)">
        <span v-for="part in metaParts" :key="part">
        <template v-if="facility.pinOk === false">
            <span v-if="facility.pinOk" class="font-semibold" style="color:var(--teal)">
              PIN {{ facility.pincode }} verified
            </span>
            <span v-else class="font-semibold" style="color:var(--coral)">
              PIN "{{ facility.pincode }}" invalid
            </span>
          </template>
          <template v-else>{{ part }}</template>
        </span>
      </div>
      <a
        v-if="phone"
        :href="`tel:${phone}`"
        class="inline-flex items-center gap-1.5 text-xs font-mono px-3 py-1.5 rounded-lg"
        style="background:var(--teal-tint);color:var(--teal)"
      >
        <Phone :size="12" /> {{ phone }}
      </a>
    </div>

    <!-- Phone-verified banner -->
    <div v-if="session.verified"
         class="flex items-center gap-2 px-5 py-2.5 text-sm font-medium"
         style="background:var(--teal-tint);color:var(--teal)">
      <Check :size="15" />
      <span><strong>Phone-verified by you</strong> on {{ TODAY }}. Record confidence raised to High.</span>
    </div>

    <!-- Axes grid -->
    <div class="grid grid-cols-2 gap-4 px-5 py-4" style="border-bottom:1px solid var(--line)">
      <!-- Match strength -->
      <div class="rounded-xl p-4" style="background:var(--grey-tint)">
        <div class="text-[11px] font-semibold tracking-wide uppercase mb-2" style="color:var(--ink-soft)">Match Strength</div>
        <div class="font-serif font-bold text-4xl leading-none mb-1" style="color:var(--ink)">{{ facility.overallScore }}</div>
        <div class="text-xs mb-3" style="color:var(--ink-soft)">Capability evidence, cited below. Proximity is illustrative.</div>
        <button class="text-xs font-medium" style="color:var(--teal)" @click="showBreakdown = !showBreakdown">
          {{ showBreakdown ? 'Hide breakdown' : 'Show breakdown' }}
        </button>
        <div v-if="showBreakdown" class="mt-3 space-y-1.5">
          <div class="flex justify-between text-xs">
            <span style="color:var(--ink-soft)">Capability match (45%)</span>
            <span class="font-semibold font-mono" style="color:var(--ink)">{{ facility.capabilityScore }}</span>
          </div>
          <div class="flex justify-between text-xs">
            <span style="color:var(--ink-soft)">Travel proximity (30%)</span>
            <span class="font-semibold" style="color:var(--amber)">illustrative</span>
          </div>
          <div class="flex justify-between text-xs pt-1.5" style="border-top:1px solid var(--line)">
            <span style="color:var(--ink)">Shown match</span>
            <span class="font-semibold font-mono" style="color:var(--ink)">{{ facility.overallScore }}</span>
          </div>
        </div>
      </div>

      <!-- Record confidence -->
      <div class="rounded-xl p-4" style="background:var(--grey-tint)">
        <div class="text-[11px] font-semibold tracking-wide uppercase mb-2" style="color:var(--ink-soft)">Record Confidence</div>
        <div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full font-semibold text-sm mb-2" :style="confBandStyle">
          <span class="w-2 h-2 rounded-full" :style="{ background: effConfidence === 'high' ? 'var(--teal)' : effConfidence === 'med' ? 'var(--amber)' : 'var(--coral)' }" />
          {{ confLabel[effConfidence] }}
        </div>
        <div class="text-xs leading-relaxed" style="color:var(--ink-soft)">{{ facility.confReason }}</div>
      </div>
    </div>

    <!-- Saved note -->
    <div v-if="session.note"
         class="mx-5 mt-4 p-3 rounded-xl text-sm"
         style="background:var(--amber-tint);border:1px solid var(--amber)">
      <div style="color:var(--ink)">{{ session.note }}</div>
      <div class="text-xs mt-1" style="color:var(--amber)">Note added by you · {{ TODAY }}</div>
    </div>

    <!-- Evidence body -->
    <div class="px-5 py-4 space-y-4">

      <!-- Green: matches -->
      <div v-if="facility.greenEvidence.length > 0">
        <div class="flex items-center gap-2 mb-2">
          <span class="w-2.5 h-2.5 rounded-full" style="background:var(--teal)" />
          <span class="text-xs font-semibold uppercase tracking-wide" style="color:var(--teal)">What matches your need</span>
          <span class="text-xs px-1.5 py-0.5 rounded-full font-medium" style="background:var(--teal-tint);color:var(--teal)">{{ facility.greenEvidence.length }}</span>
        </div>
        <div class="space-y-2">
          <EvidenceItem
            v-for="(ev, i) in facility.greenEvidence"
            :key="`g-${i}`"
            :item="ev"
            marker="✓"
            marker-color="var(--teal)"
            :cite-id="`g-${facility.facility_id}-${i}`"
            :expanded-cites="expandedCites"
            @toggle-cite="toggleCite"
          />
        </div>
      </div>

      <!-- Amber: cautions -->
      <div v-if="facility.amberEvidence.length > 0">
        <div class="flex items-center gap-2 mb-2">
          <span class="w-2.5 h-2.5 rounded-full" style="background:var(--amber)" />
          <span class="text-xs font-semibold uppercase tracking-wide" style="color:var(--amber)">Caution</span>
          <span class="text-xs px-1.5 py-0.5 rounded-full font-medium" style="background:var(--amber-tint);color:var(--amber)">{{ facility.amberEvidence.length }}</span>
        </div>
        <div class="space-y-2">
          <EvidenceItem
            v-for="(ev, i) in facility.amberEvidence"
            :key="`a-${i}`"
            :item="ev"
            marker="!"
            marker-color="var(--amber)"
            :cite-id="`a-${facility.facility_id}-${i}`"
            :expanded-cites="expandedCites"
            @toggle-cite="toggleCite"
          />
        </div>
      </div>

      <!-- Coral: flagged -->
      <div v-if="facility.coralEvidence.length > 0">
        <div class="flex items-center gap-2 mb-2">
          <span class="w-2.5 h-2.5 rounded-full" style="background:var(--coral)" />
          <span class="text-xs font-semibold uppercase tracking-wide" style="color:var(--coral)">Flagged in the data</span>
          <span class="text-xs px-1.5 py-0.5 rounded-full font-medium" style="background:var(--coral-tint);color:var(--coral)">{{ facility.coralEvidence.length }}</span>
        </div>
        <div class="space-y-2">
          <EvidenceItem
            v-for="(ev, i) in facility.coralEvidence"
            :key="`c-${i}`"
            :item="ev"
            marker="✕"
            marker-color="var(--coral)"
            :cite-id="`c-${facility.facility_id}-${i}`"
            :expanded-cites="expandedCites"
            @toggle-cite="toggleCite"
          />
        </div>
      </div>

      <!-- Grey: not in data -->
      <div v-if="facility.greyEvidence.length > 0">
        <div class="flex items-center gap-2 mb-2">
          <span class="w-2.5 h-2.5 rounded-full" style="background:var(--grey)" />
          <span class="text-xs font-semibold uppercase tracking-wide" style="color:var(--grey)">Not in our data, verify by phone</span>
          <span class="text-xs px-1.5 py-0.5 rounded-full font-medium" style="background:var(--grey-tint);color:var(--grey)">{{ facility.greyEvidence.length }}</span>
        </div>
        <div class="space-y-2">
          <EvidenceItem
            v-for="(ev, i) in facility.greyEvidence"
            :key="`k-${i}`"
            :item="ev"
            marker="?"
            marker-color="var(--grey)"
            :cite-id="`k-${facility.facility_id}-${i}`"
            :expanded-cites="expandedCites"
            :is-grey="true"
            @toggle-cite="toggleCite"
          />
        </div>
        <div v-if="phone" class="mt-3 text-xs px-3 py-2 rounded-lg" style="background:var(--grey-tint);color:var(--ink-soft)">
          Facility number on record: <span class="font-mono font-medium" style="color:var(--ink)">{{ phone }}</span>
        </div>
      </div>
    </div>

    <!-- Note box -->
    <div v-if="showNoteBox" class="px-5 pb-4">
      <textarea
        v-model="noteText"
        rows="3"
        placeholder="Add a note for your team (e.g. 'Called 15 Jun, dialysis confirmed, 3-day wait')"
        class="w-full text-sm px-3 py-2 rounded-lg resize-none outline-none"
        style="border:1px solid var(--line);color:var(--ink)"
      />
      <button class="mt-2 text-sm font-semibold px-4 py-2 rounded-lg text-white" style="background:var(--teal)" @click="saveNote">
        Save note
      </button>
    </div>

    <!-- Actions -->
    <div class="flex flex-wrap gap-2 px-5 pb-5">
      <button
        class="flex items-center gap-1.5 text-sm font-semibold px-4 py-2 rounded-lg text-white transition-opacity"
        style="background:var(--teal)"
        @click="emit('toggle-save')"
      >
        <Bookmark :size="14" :fill="session.saved ? 'currentColor' : 'none'" />
        {{ session.saved ? 'Saved to shortlist' : 'Save to shortlist' }}
      </button>

      <button
        class="flex items-center gap-1.5 text-sm font-medium px-4 py-2 rounded-lg transition-colors"
        style="background:var(--grey-tint);color:var(--ink)"
        @click="showNoteBox = !showNoteBox; noteText = session.note"
      >
        <Pencil :size="14" />
        {{ session.note ? 'Edit note' : 'Add note' }}
      </button>

      <button
        class="flex items-center gap-1.5 text-sm font-medium px-4 py-2 rounded-lg transition-colors"
        :style="session.verified ? { background: 'var(--teal-tint)', color: 'var(--teal)' } : { background: 'var(--grey-tint)', color: 'var(--ink)' }"
        @click="emit('toggle-verify')"
      >
        <PhoneCall :size="14" />
        {{ session.verified ? 'Phone-verified' : 'Mark confirmed by phone' }}
      </button>

      <button
        class="text-sm font-medium px-4 py-2 rounded-lg transition-colors"
        style="background:var(--coral-tint);color:var(--coral)"
        @click="emit('toggle-dismiss')"
      >
        {{ session.dismissed ? 'Restore' : 'Dismiss' }}
      </button>
    </div>
  </div>
</template>
