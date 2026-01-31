<template>
  <AccordionItem :value="name">
    <AccordionTrigger>
      {{ title }}
    </AccordionTrigger>
    <AccordionContent>
      <slot />
    </AccordionContent>
  </AccordionItem>
</template>

<script setup lang="ts">
import { AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'

defineProps<{ title: string; name: string }>()
</script>
