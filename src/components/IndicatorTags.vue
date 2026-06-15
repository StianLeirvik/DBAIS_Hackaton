<script setup lang="ts">
defineProps<{
  green: string[]
  yellow: string[]
  red: string[]
  collapsed?: boolean
}>()
</script>

<template>
  <div class="flex flex-wrap gap-1.5">
    <span
      v-for="tag in red"
      :key="'r-' + tag"
      class="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800 whitespace-nowrap"
    >?? {{ tag }}</span>
    <span
      v-for="tag in yellow"
      :key="'y-' + tag"
      class="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full bg-amber-50 dark:bg-amber-950 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800 whitespace-nowrap"
    >?? {{ tag }}</span>
    <template v-if="!collapsed">
      <span
        v-for="tag in green"
        :key="'g-' + tag"
        class="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full bg-green-50 dark:bg-green-950 text-green-700 dark:text-green-300 border border-green-200 dark:border-green-800 whitespace-nowrap"
      >? {{ tag }}</span>
    </template>
  </div>
</template>
