<script setup lang="ts">
import { ref } from 'vue'
import { X, MessageSquare, Minimize2, Sparkles } from '@lucide/vue'

const GENIE_URL =
  'https://dbc-4b429529-04fe.cloud.databricks.com/embed/genie/rooms/01f16905c1d512708c595d8850bcd076?o=7474645297699468'

const open = ref(false)
// Once true, the iframe is mounted in the DOM and won't reload on re-open
const hasOpened = ref(false)
// True once the iframe fires its load event
const iframeLoaded = ref(false)

function openPanel() {
  open.value = true
  hasOpened.value = true
}

function onIframeLoad() {
  // Small delay so the transition isn't jarring
  setTimeout(() => { iframeLoaded.value = true }, 300)
}
</script>

<template>
  <div class="genie-widget">
    <!-- Floating toggle button -->
    <Transition name="btn-fade">
      <button
        v-if="!open"
        class="genie-fab"
        aria-label="Open Genie AI assistant"
        @click="openPanel"
      >
        <Sparkles :size="18" />
        <span class="genie-fab-label">Ask Genie</span>
      </button>
    </Transition>

    <!-- Chat panel -->
    <Transition name="panel-slide">
      <div v-if="open" class="genie-panel">
        <!-- Header -->
        <div class="genie-header">
          <div class="flex items-center gap-2">
            <Sparkles :size="15" />
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

        <!-- Loading skeleton — shown while iframe is loading -->
        <Transition name="skeleton-fade">
          <div v-if="!iframeLoaded" class="genie-skeleton">
            <div class="skeleton-avatar pulse" />
            <div class="skeleton-lines">
              <div class="skeleton-line pulse" style="width:72%" />
              <div class="skeleton-line pulse" style="width:52%;margin-top:8px" />
            </div>
            <div class="skeleton-divider" />
            <div class="skeleton-line pulse" style="width:88%;margin:0 auto" />
            <div class="skeleton-line pulse" style="width:60%;margin:8px auto 0" />
            <div class="skeleton-bubble pulse" />
            <div class="skeleton-hint">Connecting to Genie…</div>
          </div>
        </Transition>

        <!-- Embedded Genie iframe — lazily mounted, fades in on load -->
        <iframe
          v-if="hasOpened"
          :src="GENIE_URL"
          class="genie-iframe"
          :class="{ 'iframe-visible': iframeLoaded }"
          frameborder="0"
          allow="clipboard-write"
          title="Genie AI assistant"
          @load="onIframeLoad"
        />
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.genie-widget {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 200;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
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
  width: min(520px, calc(100vw - 48px));
  height: min(700px, calc(100vh - 80px));
  border-radius: 16px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 12px 48px rgba(22, 35, 63, 0.28);
  border: 1px solid var(--line);
  background: white;
  position: relative;
}

.genie-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: var(--ink);
  color: white;
  flex-shrink: 0;
  position: relative;
  z-index: 2;
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

/* ── iframe ── */
.genie-iframe {
  position: absolute;
  top: 41px; /* header height */
  left: 0;
  right: 0;
  bottom: 0;
  width: 100%;
  height: calc(100% - 41px);
  border: none;
  display: block;
  opacity: 0;
  transition: opacity 0.5s ease;
}
.genie-iframe.iframe-visible {
  opacity: 1;
}

/* ── Loading skeleton ── */
.genie-skeleton {
  position: absolute;
  top: 41px;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0;
  padding: 20px 18px;
  background: #f8f9fc;
  z-index: 1;
}

.skeleton-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #e2e6ef;
  flex-shrink: 0;
  margin-bottom: 12px;
}

.skeleton-lines {
  display: flex;
  flex-direction: column;
  width: 100%;
  margin-bottom: 20px;
}

.skeleton-line {
  height: 11px;
  border-radius: 6px;
  background: #e2e6ef;
}

.skeleton-divider {
  width: 100%;
  height: 1px;
  background: #e2e6ef;
  margin: 16px 0;
}

.skeleton-bubble {
  width: 60%;
  height: 40px;
  border-radius: 12px;
  background: #e2e6ef;
  margin: 16px 0;
}

.skeleton-hint {
  margin-top: auto;
  width: 100%;
  text-align: center;
  font-size: 12px;
  color: #94a3b8;
  padding-bottom: 8px;
  letter-spacing: 0.01em;
}

/* Pulse animation */
@keyframes pulse-bg {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.45; }
}
.pulse {
  animation: pulse-bg 1.6s ease-in-out infinite;
}

/* ── Transitions ── */
.btn-fade-enter-active, .btn-fade-leave-active { transition: opacity 0.15s, transform 0.15s; }
.btn-fade-enter-from, .btn-fade-leave-to { opacity: 0; transform: scale(0.9); }

.panel-slide-enter-active, .panel-slide-leave-active { transition: opacity 0.22s, transform 0.22s; }
.panel-slide-enter-from, .panel-slide-leave-to { opacity: 0; transform: translateY(16px) scale(0.97); }

.skeleton-fade-enter-active, .skeleton-fade-leave-active { transition: opacity 0.4s ease; }
.skeleton-fade-enter-from, .skeleton-fade-leave-to { opacity: 0; }
</style>
