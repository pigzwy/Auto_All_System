<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h2 class="text-2xl font-semibold text-foreground">虚拟卡管理</h2>
      <Button variant="success" size="sm" class="gap-2" @click="showAddDialog = true">
        <Plus class="h-4 w-4" /> 添加卡片
      </Button>
    </div>

    <Card class="bg-card text-card-foreground">
      <CardContent class="p-0">
        <div class="overflow-x-auto rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>卡号</TableHead>
                <TableHead>有效期</TableHead>
                <TableHead>CVV</TableHead>
                <TableHead>余额</TableHead>
                <TableHead class="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="card in cards" :key="card.id">
                <TableCell class="font-mono">{{ card.number }}</TableCell>
                <TableCell>{{ card.exp }}</TableCell>
                <TableCell>{{ card.cvv }}</TableCell>
                <TableCell>¥{{ card.balance }}</TableCell>
                <TableCell class="text-right">
                  <Button variant="ghost" size="xs" class="text-destructive" @click="deleteCard(card)">删除</Button>
                </TableCell>
              </TableRow>
              <TableRow v-if="cards.length === 0">
                <TableCell colspan="5" class="py-8 text-center text-muted-foreground">暂无虚拟卡</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>

    <Dialog v-model:open="showAddDialog">
      <DialogContent class="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>添加虚拟卡</DialogTitle>
        </DialogHeader>
        <div class="grid gap-4 py-4">
          <div class="grid gap-2">
            <label class="text-sm font-medium">卡号</label>
            <Input v-model="form.number" />
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div class="grid gap-2">
              <label class="text-sm font-medium">有效期</label>
              <Input v-model="form.exp" placeholder="MM/YY" />
            </div>
            <div class="grid gap-2">
              <label class="text-sm font-medium">CVV</label>
              <Input v-model="form.cvv" maxlength="4" />
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" @click="showAddDialog = false">取消</Button>
          <Button @click="saveCard">保存</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { Plus } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'

const showAddDialog = ref(false)
const cards = ref<any[]>([])
const form = reactive({
  number: '',
  exp: '',
  cvv: ''
})

const saveCard = () => {
  // save logic
  showAddDialog.value = false
}

const deleteCard = (_card: any) => {
  // delete logic
}
</script>
