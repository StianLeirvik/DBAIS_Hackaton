<script setup lang="ts">
import { ref } from 'vue'
import { X, MessageSquare, Minimize2 } from '@lucide/vue'

const GENIE_URL =
  'https://dbc-4b429529-04fe.cloud.databricks.com/embed/genie/rooms/01f16905c1d512708c595d8850bcd076?o=7474645297699468'

const open = ref(false)
</script>

<template>
  <div class="genie-widget">
    <!-- Floating toggle button -->
    <Transition name="btn-fade">
      <button
        v-if="!open"
        class="genie-fab"
        aria-label="Open Genie AI assistant"
        @click="open = true"
      >
        <MessageSquare :size="22" />
        <span class="genie-fab-label">Ask Genie</span>
      </button>
    </Transition>

    <!-- Chat panel -->
    <Transition name="panel-slide">
      <div v-if="open" class="genie-panel">
        <!-- Header -->
        <div class="genie-header">
          <div class="flex items-center gap-2">
            <MessageSquare :size="15" />
            <span class="font-semibold text-sm">Genie AI</span>
            <span class="text-[10px] px-1.5 py-0.5 rounded font-bold" style="background:rgba(255,255,255,0.15)">BETA</span>
          </div>
          <div class="flex items-center gap-1">
            <button class="genie-icon-btn" aria-label="Minimise" @click="open = false">
              <Minimize2 :size="14" />
            </button>
            <button class="genie-icon-btn" aria-label="Close" @click="open = false">
              <X :size="14" />
            </button>
          </div>
        </div>

        <!-- Embedded Genie iframe -->
        <iframe
          :src="GENIE_URL"
          class="genie-iframe"
          frameborder="0"
          allow="clipboard-write"
          title="Genie AI assistant"
        />
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.genie-widget {
  position: fixed;
  bottom: 24px;
  left: 24px;
  z-index: 200;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

/* ── FAB ── */
.genie-fab {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 18px;
  border-radius: 999px;
  background: var(--ink);
  color: white;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 4px 20px rgba(22, 35, 63, 0.35);
  border: none;
  transition: background 0.15s, transform 0.15s, box-shadow 0.15s;
}
.genie-fab:hover {
  background: #1e2f52;
  transform: translateY(-2px);
  box-shadow: 0 6px 24px rgba(22, 35, 63, 0.45);
}
.genie-fab-label {
  white-space: nowrap;
}

/* ── Panel ── */
.genie-panel {
  width: min(400px, calc(100vw - 48px));
  height: min(580px, calc(100vh - 100px));
  border-radius: 16px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 12px 48px rgba(22, 35, 63, 0.28);
  border: 1px solid var(--line);
  background: white;
}

.genie-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: var(--ink);
  color: white;
  flex-shrink: 0;
}

.genie-icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: none;
  background: transparent;
  color: rgba(255,255,255,0.7);
  cursor: pointer;
  transition: background 0.12s, color 0.12s;
}
.genie-icon-btn:hover {
  background: rgba(255,255,255,0.15);
  color: white;
}

.genie-iframe {
  flex: 1;
  width: 100%;
  border: none;
  display: block;
}

/* ── Transitions ── */
.btn-fade-enter-active, .btn-fade-leave-active { transition: opacity 0.15s, transform 0.15s; }
.btn-fade-enter-from, .btn-fade-leave-to { opacity: 0; transform: scale(0.9); }

.panel-slide-enter-active, .panel-slide-leave-active { transition: opacity 0.2s, transform 0.2s; }
.panel-slide-enter-from, .panel-slide-leave-to { opacity: 0; transform: translateY(16px) scale(0.97); }
</style>
