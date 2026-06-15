<script setup lang="ts">
import { X } from '@lucide/vue'
import type { ScoredFacility, ConfidenceLevel } from '../types'

interface Session {
  saved: boolean
  note: string
  verified: boolean
  dismissed: boolean
}

const props = defineProps<{
  open: boolean
  facilities: ScoredFacility[]
  sessions: Record<string, Session>
  effConfidence: (f: ScoredFacility) => ConfidenceLevel
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'unsave', id: string): void
}>()

const confLabel: Record<ConfidenceLevel, string> = { high: 'High', med: 'Medium', low: 'Low' }
</script>

<template>
  <!-- Scrim -->
  <Transition name="fade">
    <div
      v-if="open"
      class="fixed inset-0 z-40"
      style="background:rgba(22,35,63,0.45)"
      @click="emit('close')"
    />
  </Transition>

  <!-- Drawer -->
  <Transition name="slide">
    <div
      v-if="open"
      class="fixed top-0 right-0 bottom-0 z-50 flex flex-col"
      style="width:360px;background:white;box-shadow:-4px 0 24px rgba(22,35,63,0.15)"
    >
      <!-- Header -->
      <div class="flex items-center justify-between px-5 py-4" style="border-bottom:1px solid var(--line)">
        <div class="font-serif text-lg font-semibold" style="color:var(--ink)">Shortlist</div>
        <button
          class="w-8 h-8 flex items-center justify-center rounded-lg"
          style="color:var(--ink-soft)"
          @click="emit('close')"
        >
          <X :size="16" />
        </button>
      </div>

      <!-- Body -->
      <div class="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        <div v-if="facilities.length === 0" class="text-center py-12 text-sm" style="color:var(--ink-soft)">
          No facilities saved yet.<br>
          Use "Save to shortlist" on a candidate to build your working list.
        </div>

        <div
          v-for="f in facilities"
          :key="f.facility_id"
          class="rounded-xl p-4"
          style="border:1px solid var(--line)"
        >
          <div class="font-serif font-semibold text-[15px] mb-1" style="color:var(--ink)">{{ f.name_clean }}</div>
          <div class="text-xs mb-2" style="color:var(--ink-soft)">
            {{ [f.city, f.state].filter(Boolean).join(', ') || 'Location unknown' }}
          </div>

          <!-- Tags -->
          <div class="flex flex-wrap gap-1.5 mb-3">
            <span class="text-[11px] px-2 py-0.5 rounded-full font-medium" style="background:var(--teal-tint);color:var(--teal)">
              Match {{ f.overallScore }}
            </span>
            <span
              class="text-[11px] px-2 py-0.5 rounded-full font-medium"
              :style="effConfidence(f) === 'high' ? { background: 'var(--teal-tint)', color: 'var(--teal)' } :
                      effConfidence(f) === 'med'  ? { background: 'var(--amber-tint)', color: 'var(--amber)' } :
                                                    { background: 'var(--coral-tint)', color: 'var(--coral)' }"
            >
              {{ confLabel[effConfidence(f)] }} confidence
            </span>
            <span v-if="sessions[f.facility_id]?.verified" class="text-[11px] px-2 py-0.5 rounded-full font-medium" style="background:var(--teal-tint);color:var(--teal)">
              Phone-verified
            </span>
          </div>

          <!-- Note -->
          <div v-if="sessions[f.facility_id]?.note" class="text-xs mb-3 px-2 py-1.5 rounded" style="background:var(--amber-tint);color:var(--ink)">
            {{ sessions[f.facility_id].note }}
          </div>

          <button
            class="text-xs font-medium px-3 py-1.5 rounded-lg transition-colors"
            style="background:var(--coral-tint);color:var(--coral)"
            @click="emit('unsave', f.facility_id)"
          >
            Remove from shortlist
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.slide-enter-active, .slide-leave-active { transition: transform 0.25s ease; }
.slide-enter-from, .slide-leave-to { transform: translateX(100%); }
</style>
