<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Bookmark } from '@lucide/vue'
import SearchBar from './components/SearchBar.vue'
import CandidateCard from './components/CandidateCard.vue'
import DetailPanel from './components/DetailPanel.vue'
import ShortlistDrawer from './components/ShortlistDrawer.vue'
import FacilityMapModal from './components/FacilityMapModal.vue'
import GenieWidget from './components/GenieWidget.vue'
import { useSearch } from './composables/useSearch'
import { useSession } from './composables/useSession'
import type { ScoredFacility } from './types'

const { location, careNeedId, sortedResults, loading, error, hasSearched, userCenter, search } = useSearch()
const { sessions, getSession, toggleSave, toggleVerify, toggleDismiss, setNote, effectiveConfidence } = useSession()

const selectedId = ref<string | null>(null)
const drawerOpen = ref(false)
const mapOpen = ref(false)

const orderedResults = computed(() => {
  return [...sortedResults.value].sort((a, b) => {
    const da = getSession(a.facility_id).dismissed ? 1 : 0
    const db = getSession(b.facility_id).dismissed ? 1 : 0
    return da - db || b.overallScore - a.overallScore
  })
})

const selectedFacility = computed<ScoredFacility | null>(() =>
  sortedResults.value.find(f => f.facility_id === selectedId.value) ?? null,
)

const savedCount = computed(() =>
  Object.values(sessions).filter(s => s.saved).length,
)

const savedFacilities = computed(() =>
  sortedResults.value.filter(f => sessions[f.facility_id]?.saved),
)

function selectFacility(id: string) {
  selectedId.value = id
}

function viewFacilityMap(id: string) {
  selectedId.value = id
  mapOpen.value = true
}

function handleSearch() {
  selectedId.value = null
  search()
}

// Auto-select the top result once results load
watch(sortedResults, (results) => {
  if (results.length > 0 && selectedId.value === null) {
    selectedId.value = results[0].facility_id
  }
})
</script>

<template>
  <div class="min-h-screen flex flex-col" style="background:var(--paper)">

    <!-- ─── Header ────────────────────────────────────────────────────────── -->
    <header class="sticky top-0 z-50 flex items-center justify-between px-5 py-3"
            style="background:var(--ink)">
      <div class="flex items-center gap-3">
        <span class="font-serif text-white text-xl font-semibold leading-none">◈ CareMap</span>
      </div>
      <button
        class="flex items-center gap-2 text-sm font-semibold px-3 py-1.5 rounded-lg transition-colors"
        style="background:rgba(255,255,255,0.12);color:white"
        @click="drawerOpen = true"
      >
        <Bookmark :size="15" />
        Shortlist {{ savedCount > 0 ? savedCount : '' }}
      </button>
    </header>

    <!-- ─── Search area ────────────────────────────────────────────────────── -->
    <div class="px-5 pt-5 pb-4" style="border-bottom:1px solid var(--line)">
      <SearchBar
        v-model:location="location"
        v-model:care-need-id="careNeedId"
        :loading="loading"
        @search="handleSearch"
      />
    </div>

    <!-- ─── Error banner ──────────────────────────────────────────────────── -->
    <div v-if="error" class="mx-5 mt-3 text-sm px-4 py-3 rounded-lg"
         style="background:#fdf0ec;color:var(--coral);border:1px solid var(--coral)">
      <span class="font-semibold">Error:</span> {{ error }}
    </div>

    <!-- ─── Results header ────────────────────────────────────────────────── -->
    <div v-if="hasSearched && !loading && orderedResults.length > 0"
         class="px-5 pt-4 pb-2 text-sm flex items-center justify-between" style="color:var(--ink-soft)">
      <span>
        <span class="font-bold" style="color:var(--ink)">{{ orderedResults.length }} candidates</span>
        · ranked by match strength · record confidence shown separately, never blended in
      </span>
    </div>

    <!-- ─── Welcome state (full-width, centered) ──────────────────────────── -->
    <div v-if="!hasSearched" class="flex-1 flex flex-col items-center justify-center py-24 text-center">
      <div class="font-serif text-6xl font-light mb-5" style="color:var(--teal)">◈</div>
      <h2 class="font-serif text-3xl font-semibold mb-3" style="color:var(--ink)">Find the right facility</h2>
      <p class="text-sm leading-relaxed max-w-sm" style="color:var(--ink-soft)">
        Select a care need and enter a location to get a ranked shortlist with transparent match scores.
      </p>
    </div>

    <!-- ─── Main body ─────────────────────────────────────────────────────── -->
    <div v-else class="flex-1 flex px-5 pb-8 pt-2 gap-5 items-start">

      <!-- Left: candidate list -->
      <div class="shrink-0 flex flex-col gap-3" style="width:min(440px,100%)">

        <!-- Skeleton loaders -->
        <template v-if="loading">
          <div v-for="i in 4" :key="i"
               class="rounded-xl overflow-hidden"
               style="background:white;border:1px solid var(--line)">
            <!-- Top row -->
            <div class="flex items-start gap-3 px-4 pt-4 pb-3">
              <div class="w-5 h-8 rounded animate-pulse shrink-0" style="background:#e8eaed" />
              <div class="flex-1 space-y-2 pt-0.5">
                <div class="h-5 rounded animate-pulse" style="background:#e8eaed;width:72%" />
                <div class="h-3 rounded animate-pulse" style="background:#f1f3f4;width:50%" />
                <div class="h-5 w-28 rounded-full animate-pulse" style="background:#f1f3f4" />
              </div>
              <div class="flex flex-col items-center gap-1 shrink-0">
                <div class="w-10 h-9 rounded animate-pulse" style="background:#e8eaed" />
                <div class="w-8 h-2 rounded animate-pulse" style="background:#f1f3f4" />
              </div>
            </div>
            <!-- Footer row -->
            <div class="flex items-center gap-3 px-4 pb-3 pt-2" style="border-top:1px solid var(--line)">
              <div class="h-3 w-20 rounded animate-pulse" style="background:#f1f3f4" />
              <div class="flex gap-2 ml-auto">
                <div class="h-3 w-6 rounded-full animate-pulse" style="background:#f1f3f4" />
                <div class="h-3 w-6 rounded-full animate-pulse" style="background:#f1f3f4" />
                <div class="h-3 w-6 rounded-full animate-pulse" style="background:#f1f3f4" />
              </div>
            </div>
          </div>
        </template>

        <!-- No results -->
        <div v-else-if="orderedResults.length === 0" class="text-center py-12 text-sm" style="color:var(--ink-soft)">
          No facilities found. Try a different location or care need.
        </div>

        <!-- Cards -->
        <template v-else>
          <CandidateCard
            v-for="(facility, index) in orderedResults"
            :key="facility.facility_id"
            :facility="facility"
            :rank="index + 1"
            :selected="selectedId === facility.facility_id"
            :eff-confidence="effectiveConfidence(facility)"
            :session="getSession(facility.facility_id)"
            @select="selectFacility(facility.facility_id)"
            @view-map="viewFacilityMap(facility.facility_id)"
          />
        </template>
      </div>

      <!-- Right: detail panel skeleton while loading -->
      <div v-if="loading" class="flex-1 sticky top-[104px]">
        <div class="rounded-2xl overflow-hidden" style="background:white;border:1px solid var(--line)">
          <!-- Head skeleton -->
          <div class="px-5 pt-5 pb-4" style="border-bottom:1px solid var(--line)">
            <div class="h-7 rounded animate-pulse mb-3" style="background:#e8eaed;width:68%" />
            <div class="flex gap-3 mb-3">
              <div class="h-3 w-16 rounded animate-pulse" style="background:#f1f3f4" />
              <div class="h-3 w-12 rounded animate-pulse" style="background:#f1f3f4" />
              <div class="h-3 w-20 rounded animate-pulse" style="background:#f1f3f4" />
              <div class="h-3 w-14 rounded animate-pulse" style="background:#f1f3f4" />
            </div>
            <div class="h-8 w-36 rounded-lg animate-pulse" style="background:#f1f3f4" />
          </div>
          <!-- Stat grid skeleton -->
          <div class="grid grid-cols-2 gap-4 px-5 py-4" style="border-bottom:1px solid var(--line)">
            <div class="rounded-xl p-4 animate-pulse" style="background:#f6f7f9">
              <div class="h-3 w-24 rounded mb-3" style="background:#e2e6ef" />
              <div class="h-10 w-14 rounded mb-2" style="background:#e2e6ef" />
              <div class="h-3 w-32 rounded" style="background:#eaecf0" />
            </div>
            <div class="rounded-xl p-4 animate-pulse" style="background:#f6f7f9">
              <div class="h-3 w-24 rounded mb-3" style="background:#e2e6ef" />
              <div class="h-7 w-20 rounded-full mb-2" style="background:#e2e6ef" />
              <div class="h-3 w-36 rounded" style="background:#eaecf0" />
            </div>
          </div>
          <!-- Evidence sections skeleton -->
          <div class="px-5 py-4 space-y-5">
            <div v-for="s in 3" :key="s">
              <div class="h-3 w-28 rounded animate-pulse mb-3" style="background:#e2e6ef" />
              <div class="space-y-2">
                <div v-for="r in 3" :key="r" class="h-8 rounded-lg animate-pulse" style="background:#f1f3f4" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="selectedFacility" class="flex-1 sticky top-[104px]">
        <DetailPanel
          :facility="selectedFacility"
          :session="getSession(selectedFacility.facility_id)"
          :eff-confidence="effectiveConfidence(selectedFacility)"
          @toggle-save="toggleSave(selectedFacility!.facility_id, selectedFacility ?? undefined)"
          @toggle-verify="toggleVerify(selectedFacility!.facility_id)"
          @toggle-dismiss="toggleDismiss(selectedFacility!.facility_id)"
          @save-note="(n) => setNote(selectedFacility!.facility_id, n)"
          @view-map="viewFacilityMap(selectedFacility!.facility_id)"
        />
      </div>

    </div>

    <!-- ─── Shortlist drawer ──────────────────────────────────────────────── -->
    <ShortlistDrawer
      :open="drawerOpen"
      :facilities="savedFacilities"
      :sessions="sessions"
      :eff-confidence="effectiveConfidence"
      @close="drawerOpen = false"
      @unsave="(id) => toggleSave(id)"
    />
    <!-- ─── Map modal ───────────────────────────────────────────── -->
    <FacilityMapModal
      :open="mapOpen"
      :facilities="sortedResults"
      :selected="selectedFacility"
      :user-lat="userCenter?.lat ?? null"
      :user-lng="userCenter?.lng ?? null"
      :location-label="location"
      @close="mapOpen = false"
      @select="(id) => { selectFacility(id); mapOpen = false }"
    />

    <!-- ─── Genie AI floating chat ───────────────────────────────── -->
    <GenieWidget />

  </div>
</template>

