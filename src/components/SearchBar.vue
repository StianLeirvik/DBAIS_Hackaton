<script setup lang="ts">
import { Loader2, Search } from '@lucide/vue'
import { CARE_NEEDS } from '../types'

const props = defineProps<{
  location: string
  careNeedId: string
  loading: boolean
}>()

const emit = defineEmits<{
  (e: 'update:location', value: string): void
  (e: 'update:careNeedId', value: string): void
  (e: 'search'): void
}>()
</script>

<template>
  <div class="flex flex-col gap-4">
    <!-- Inputs row -->
    <div class="flex flex-wrap gap-3 items-end">
      <!-- Care need -->
      <div class="flex flex-col gap-1.5">
        <label class="text-[11px] font-semibold tracking-widest uppercase" style="color:var(--ink-soft)">
          Care Need
        </label>
        <select
          :value="props.careNeedId"
          class="border rounded-lg px-3 py-2 text-sm font-medium outline-none"
          style="border-color:var(--line);background:white;color:var(--ink);min-width:180px"
          @change="emit('update:careNeedId', ($event.target as HTMLSelectElement).value)"
        >
          <option v-for="need in CARE_NEEDS" :key="need.id" :value="need.id">
            {{ need.icon }} {{ need.label }}
          </option>
        </select>
      </div>

      <!-- Location -->
      <div class="flex flex-col gap-1.5 flex-1" style="min-width:200px">
        <label class="text-[11px] font-semibold tracking-widest uppercase" style="color:var(--ink-soft)">
          Location
        </label>
        <input
          type="text"
          :value="props.location"
          placeholder="City, district or PIN code"
          autocomplete="off"
          class="border rounded-lg px-3 py-2 text-sm outline-none transition-all"
          style="border-color:var(--line);color:var(--ink);background:white"
          @input="emit('update:location', ($event.target as HTMLInputElement).value)"
          @keydown.enter="emit('search')"
        />
      </div>

      <!-- Search button -->
      <button
        class="flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-semibold text-white transition-opacity"
        style="background:var(--ink)"
        :style="{ opacity: props.loading || !props.location.trim() ? 0.5 : 1 }"
        :disabled="props.loading || !props.location.trim()"
        @click="emit('search')"
      >
        <Loader2 v-if="props.loading" :size="15" class="animate-spin" />
        <Search v-else :size="15" />
        {{ props.loading ? 'Searching…' : 'Search' }}
      </button>
    </div>

    <!-- Care need chip filters -->
    <div class="flex flex-wrap gap-2">
      <button
        v-for="need in CARE_NEEDS"
        :key="need.id"
        type="button"
        class="text-xs px-3 py-1 rounded-full border font-medium transition-all"
        :style="props.careNeedId === need.id
          ? 'background:var(--ink);color:white;border-color:var(--ink)'
          : 'background:white;color:var(--ink-soft);border-color:var(--line)'"
        @click="emit('update:careNeedId', need.id)"
      >
        {{ need.icon }} {{ need.label }}
      </button>
    </div>
  </div>
</template>
