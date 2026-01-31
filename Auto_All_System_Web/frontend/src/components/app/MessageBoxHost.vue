<template>
  <Dialog :open="state.open" @update:open="handleOpenChange">
    <DialogContent class="sm:max-w-[520px]">
      <DialogHeader>
        <DialogTitle v-if="state.title">{{ state.title }}</DialogTitle>
        <DialogDescription v-if="!state.dangerouslyUseHTMLString">{{ state.message }}</DialogDescription>
        <DialogDescription v-else>
          <span v-html="state.message" />
        </DialogDescription>
      </DialogHeader>

      <div v-if="state.kind === 'prompt'" class="grid gap-2">
        <Input v-model="state.inputValue" :placeholder="state.inputPlaceholder" />
      </div>

      <DialogFooter>
        <Button v-if="state.showCancel" type="button" variant="secondary" @click="cancel">
          {{ state.cancelText }}
        </Button>
        <Button
          type="button"
          :variant="state.type === 'error' ? 'destructive' : 'default'"
          @click="confirm"
        >
          {{ state.confirmText }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { useMessageBoxState } from '@/lib/element'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

const { state, confirm, cancel } = useMessageBoxState()

const handleOpenChange = (open: boolean) => {
  if (open) return

  // Backdrop/ESC close.
  if (state.kind === 'alert') {
    confirm()
    return
  }

  cancel()
}
</script>
