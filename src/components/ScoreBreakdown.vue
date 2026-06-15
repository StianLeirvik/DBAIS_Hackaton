<script setup lang="ts">
defineProps<{
  capabilityScore: number
  proximityScore: number
  freshnessScore: number
  overallScore: number
}>()

function scoreColor(score: number): string {
  if (score >= 70) return '#16a34a'
  if (score >= 40) return '#d97706'
  return '#dc2626'
}
</script>

<template>
  <div class="bg-slate-50 dark:bg-slate-800 rounded-xl p-3 space-y-2">
    <!-- Overall score -->
    <div class="flex justify-between items-baseline">
      <span class="text-xs font-semibold text-slate-400 uppercase tracking-wide">Match Score</span>
      <span class="text-2xl font-extrabold leading-none" :style="{ color: scoreColor(overallScore) }">
        {{ overallScore }}<span class="text-sm font-semibold">%</span>
      </span>
    </div>
    <div class="h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
      <div
        class="h-full rounded-full transition-all duration-500"
        :style="{ width: overallScore + '%', background: scoreColor(overallScore) }"
      />
    </div>

    <!-- Component bars -->
    <div class="space-y-1.5 pt-1">
      <div v-for="comp in [
        { label: 'Capability', score: capabilityScore, cls: 'bg-indigo-500' },
        { label: 'Proximity', score: proximityScore, cls: 'bg-cyan-500' },
        { label: 'Freshness', score: freshnessScore, cls: 'bg-green-500' },
      ]" :key="comp.label" class="grid grid-cols-[64px_1fr_32px] items-center gap-2">
        <span class="text-xs text-slate-400">{{ comp.label }}</span>
        <div class="h-1 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
          <div class="h-full rounded-full transition-all duration-500" :class="comp.cls" :style="{ width: comp.score + '%' }" />
        </div>
        <span class="text-xs text-slate-400 text-right">{{ comp.score }}%</span>
      </div>
    </div>
  </div>
</template>
