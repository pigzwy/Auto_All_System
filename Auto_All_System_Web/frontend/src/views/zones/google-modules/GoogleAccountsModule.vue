<template>
  <div class="space-y-4">
    <!-- 统计卡片 -->
    <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <div class="rounded-xl border border-border bg-gradient-to-br from-blue-50 to-blue-100/50 dark:from-blue-950/30 dark:to-blue-900/20 p-4">
        <div class="flex items-center gap-3">
          <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/10">
            <Users class="h-5 w-5 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <div class="text-2xl font-bold text-blue-700 dark:text-blue-300">{{ total }}</div>
            <div class="text-xs text-blue-600/70 dark:text-blue-400/70">账号总数</div>
          </div>
        </div>
      </div>
      <div class="rounded-xl border border-border bg-gradient-to-br from-emerald-50 to-emerald-100/50 dark:from-emerald-950/30 dark:to-emerald-900/20 p-4">
        <div class="flex items-center gap-3">
          <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-500/10">
            <CheckCircle2 class="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
          </div>
          <div>
            <div class="text-2xl font-bold text-emerald-700 dark:text-emerald-300">{{ stats.verified }}</div>
            <div class="text-xs text-emerald-600/70 dark:text-emerald-400/70">已验证</div>
          </div>
        </div>
      </div>
      <div class="rounded-xl border border-border bg-gradient-to-br from-violet-50 to-violet-100/50 dark:from-violet-950/30 dark:to-violet-900/20 p-4">
        <div class="flex items-center gap-3">
          <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-violet-500/10">
            <CreditCardIcon class="h-5 w-5 text-violet-600 dark:text-violet-400" />
          </div>
          <div>
            <div class="text-2xl font-bold text-violet-700 dark:text-violet-300">{{ stats.cardBound }}</div>
            <div class="text-xs text-violet-600/70 dark:text-violet-400/70">已绑卡</div>
          </div>
        </div>
      </div>
      <div class="rounded-xl border border-border bg-gradient-to-br from-amber-50 to-amber-100/50 dark:from-amber-950/30 dark:to-amber-900/20 p-4">
        <div class="flex items-center gap-3">
          <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-500/10">
            <MonitorIcon class="h-5 w-5 text-amber-600 dark:text-amber-400" />
          </div>
          <div>
            <div class="text-2xl font-bold text-amber-700 dark:text-amber-300">{{ stats.envCreated }}</div>
            <div class="text-xs text-amber-600/70 dark:text-amber-400/70">已创建环境</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 筛选栏 -->
    <Card class="bg-card text-card-foreground">
      <CardContent class="p-4">
        <div class="flex flex-wrap items-center gap-3">
          <Select :model-value="filterType" @update:modelValue="(v) => onFilterTypeChange(v)">
            <SelectTrigger class="h-9 w-40">
              <SelectValue placeholder="账号状态筛选" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部状态</SelectItem>
              <SelectItem value="ineligible">无资格</SelectItem>
              <SelectItem value="unbound_card">未绑卡</SelectItem>
              <SelectItem value="success">成功</SelectItem>
              <SelectItem value="other">其他</SelectItem>
            </SelectContent>
          </Select>

          <Select :model-value="filterGroup" @update:modelValue="(v) => onFilterGroupChange(v)">
            <SelectTrigger class="h-9 w-44">
              <SelectValue placeholder="分组筛选" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部分组</SelectItem>
              <SelectItem value="ungrouped">未分组</SelectItem>
              <SelectItem
                v-for="group in groupList"
                :key="String(group.id)"
                :value="String(group.id)"
              >
                {{ `${group.name} (${group.account_count})` }}
              </SelectItem>
            </SelectContent>
          </Select>

          <div class="ml-auto text-sm text-muted-foreground">
            共 <span class="font-medium text-foreground">{{ total }}</span> 条
          </div>
        </div>
      </CardContent>
    </Card>

    <Card class="bg-card text-card-foreground">
      <CardContent class="p-0">
        <div class="overflow-x-auto rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead class="w-10">
                  <Checkbox
                    :checked="allSelectedOnPage || (someSelectedOnPage ? 'indeterminate' : false)"
                    @update:checked="onToggleAllOnPage"
                  />
                </TableHead>
                <TableHead class="w-20">ID</TableHead>
                <TableHead class="min-w-[260px]">邮箱</TableHead>
                <TableHead class="min-w-[320px]">进度</TableHead>
                <TableHead class="w-24">n-2fa</TableHead>
                <TableHead class="w-28">环境</TableHead>
                <TableHead class="w-44">创建时间</TableHead>
                <TableHead class="w-28 text-right">操作</TableHead>
              </TableRow>
            </TableHeader>

            <TableBody>
              <TableRow v-if="loading">
                <TableCell colspan="9" class="py-10">
                  <div class="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                    <Loader2Icon class="h-4 w-4 animate-spin" />
                    加载中...
                  </div>
                </TableCell>
              </TableRow>

              <TableRow v-else-if="accounts.length === 0">
                <TableCell colspan="9" class="py-10 text-center text-sm text-muted-foreground">
                  暂无数据
                </TableCell>
              </TableRow>

              <TableRow 
                v-else 
                v-for="row in accounts" 
                :key="row.id" 
                class="cursor-pointer transition-colors"
                :class="isRowSelected(row) ? 'bg-primary/10 hover:bg-primary/15' : 'hover:bg-muted/30'"
                @click="onToggleRow(row, !isRowSelected(row))"
              >
                <TableCell @click.stop>
                  <Checkbox
                    :checked="isRowSelected(row)"
                    @update:checked="(v: boolean) => onToggleRow(row, v)"
                  />
                </TableCell>

                <TableCell class="font-mono text-xs text-muted-foreground">#{{ row.id }}</TableCell>

                <TableCell>
                  <button
                    type="button"
                    class="max-w-[320px] truncate text-left text-primary hover:underline underline-offset-4"
                    :title="row.email"
                    @click="viewAccount(row)"
                  >
                    {{ row.email }}
                  </button>
                </TableCell>

                <TableCell>
                  <div class="flex flex-wrap items-center gap-1">
                    <span
                      v-for="(step, index) in getMainFlowProgress(row)"
                      :key="`${row.id}-${index}`"
                      class="inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium"
                      :class="step.done ? 'border-emerald-500/40 bg-emerald-500/15 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400' : 'border-muted-foreground/20 bg-muted/30 text-muted-foreground'"
                      :title="`${index + 1}. ${step.label}`"
                    >
                      {{ step.label }}
                    </span>
                  </div>
                </TableCell>

                <TableCell>
                  <button
                    v-if="row.new_2fa_display || row.new_2fa"
                    type="button"
                    class="inline-flex items-center justify-center rounded-md p-1.5 text-primary hover:bg-primary/10 transition-colors"
                    title="查看 2FA"
                    @click.stop="open2faDialog(row)"
                  >
                    <KeyRound class="h-4 w-4" />
                  </button>
                  <span v-else class="text-xs text-muted-foreground">-</span>
                </TableCell>

                <TableCell>
                  <Button
                    :variant="row.geekez_profile_exists ? 'default' : 'outline'"
                    size="xs"
                    class="h-7"
                    :class="row.geekez_profile_exists 
                      ? 'bg-emerald-600 hover:bg-emerald-700 text-white' 
                      : 'border-violet-300 text-violet-600 hover:bg-violet-50 hover:text-violet-700 dark:border-violet-700 dark:text-violet-400 dark:hover:bg-violet-950'"
                    @click.stop="launchGeekez(row)"
                  >
                    {{ row.geekez_profile_exists ? '打开' : '创建' }}
                  </Button>
                </TableCell>

                <TableCell class="text-muted-foreground">
                  {{ formatDate(row.created_at) }}
                </TableCell>

                <TableCell class="text-right">
                  <div class="flex items-center justify-end gap-1">
                    <Button variant="ghost" size="xs" class="text-blue-600 hover:text-blue-700 hover:bg-blue-50 dark:text-blue-400 dark:hover:text-blue-300 dark:hover:bg-blue-950" @click.stop="editAccount(row)">编辑</Button>
                    <Button variant="ghost" size="xs" class="text-amber-600 hover:text-amber-700 hover:bg-amber-50 dark:text-amber-400 dark:hover:text-amber-300 dark:hover:bg-amber-950" @click.stop="openTasksDrawer(row)">任务</Button>
                    <Button variant="ghost" size="xs" class="text-destructive hover:text-destructive hover:bg-destructive/10" @click.stop="deleteAccount(row)">删除</Button>
                  </div>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>

        <div class="p-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div class="text-sm text-muted-foreground">
            共 <span class="font-medium text-foreground">{{ total }}</span> 条
          </div>

          <div v-if="total > pageSize" class="flex flex-wrap items-center justify-end gap-2">
            <Button variant="outline" size="sm" :disabled="currentPage <= 1" @click="goPrevPage">上一页</Button>
            <div class="text-sm text-muted-foreground tabular-nums">
              第 <span class="text-foreground font-medium">{{ currentPage }}</span> / {{ totalPages }} 页
            </div>
            <Button variant="outline" size="sm" :disabled="currentPage >= totalPages" @click="goNextPage">下一页</Button>

            <Select :model-value="String(pageSize)" @update:modelValue="(v) => onPageSizeChange(v)">
              <SelectTrigger class="h-9 w-[120px]">
                <SelectValue placeholder="每页" />
              </SelectTrigger>
              <SelectContent align="end">
                <SelectItem value="10">10 / 页</SelectItem>
                <SelectItem value="20">20 / 页</SelectItem>
                <SelectItem value="50">50 / 页</SelectItem>
                <SelectItem value="100">100 / 页</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- 添加账号对话框 -->
    <Dialog v-model:open="showDialog">
      <DialogContent class="sm:max-w-[520px]">
        <DialogHeader>
          <DialogTitle>添加 Google 账号</DialogTitle>
          <DialogDescription>用于批量任务的账号信息（恢复邮箱/备注可选）。</DialogDescription>
        </DialogHeader>

        <div class="grid gap-4 py-2">
          <div class="grid gap-2">
            <label class="text-sm font-medium">邮箱</label>
            <Input v-model="accountForm.email" placeholder="请输入 Google 邮箱" />
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium">密码</label>
            <Input v-model="accountForm.password" type="password" placeholder="请输入密码" />
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium">恢复邮箱</label>
            <Input v-model="accountForm.recovery_email" placeholder="选填" />
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium">备注</label>
            <textarea
              v-model="accountForm.notes"
              rows="2"
              placeholder="选填"
              class="min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            />
          </div>
        </div>

        <DialogFooter class="gap-2">
          <Button variant="outline" @click="showDialog = false">取消</Button>
          <Button :disabled="submitting" class="gap-2" @click="handleAddAccount">
            <Loader2Icon v-if="submitting" class="h-4 w-4 animate-spin" />
            添加
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- 批量导入对话框 -->
    <Dialog v-model:open="showImportDialog">
      <DialogContent class="sm:max-w-[760px]">
        <DialogHeader>
          <DialogTitle>批量导入 Google 账号</DialogTitle>
          <DialogDescription>支持导入并自动分组；可选择覆盖已存在账号。</DialogDescription>
        </DialogHeader>

        <Alert class="mt-2">
          <AlertTitle>导入格式说明</AlertTitle>
          <AlertDescription>
            <div class="space-y-1">
              <div>
                每行一个账号，格式：
                <code class="rounded bg-muted px-1.5 py-0.5 font-mono text-primary">email----password----recovery----secret</code>
              </div>
              <div>
                示例：
                <code class="rounded bg-muted px-1.5 py-0.5 font-mono text-primary">test@gmail.com----Pass123----recovery@mail.com----</code>
              </div>
              <div class="text-xs text-muted-foreground">注意：使用 ---- 分隔各字段，恢复邮箱和密钥可留空</div>
            </div>
          </AlertDescription>
        </Alert>

        <div class="grid gap-4 py-2">
          <div class="grid gap-2">
            <label class="text-sm font-medium">分组名称</label>
            <Input v-model="importForm.group_name" placeholder="可选，如：售后、2FA（留空则使用当前时间）" />
            <div class="text-xs text-muted-foreground">导入后自动创建分组，如“售后_10个”或“2025-01-25_1030_10个”</div>
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium">账号列表</label>
            <textarea
              v-model="importText"
              rows="12"
              placeholder="粘贴账号数据，每行一个账号"
              class="min-h-[240px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            />
          </div>

          <label class="flex items-center gap-3">
            <input
              v-model="importForm.overwrite_existing"
              type="checkbox"
              class="h-4 w-4 rounded border-border accent-primary"
            />
            <span class="text-sm text-muted-foreground">覆盖已存在（开启后将更新已存在的账号）</span>
          </label>
        </div>

        <DialogFooter class="gap-2">
          <Button variant="outline" @click="showImportDialog = false">取消</Button>
          <Button :disabled="importing" class="gap-2" @click="handleImportAccounts">
            <Loader2Icon v-if="importing" class="h-4 w-4 animate-spin" />
            导入 ({{ importCount }} 个账号)
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- 编辑账号对话框 -->
    <Dialog v-model:open="showEditDialog">
      <DialogContent class="sm:max-w-[520px]">
        <DialogHeader>
          <DialogTitle>编辑 Google 账号</DialogTitle>
          <DialogDescription>仅修改你填写的字段；密码留空则保持不变。</DialogDescription>
        </DialogHeader>

        <div class="grid gap-4 py-2">
          <div class="grid gap-2">
            <label class="text-sm font-medium">邮箱</label>
            <Input v-model="editForm.email" disabled />
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium">密码</label>
            <Input v-model="editForm.password" type="password" placeholder="留空则不修改" />
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium">恢复邮箱</label>
            <Input v-model="editForm.recovery_email" placeholder="选填" />
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium">2FA 密钥</label>
            <Input v-model="editForm.secret_key" placeholder="选填" />
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium">备注</label>
            <textarea
              v-model="editForm.notes"
              rows="2"
              placeholder="选填"
              class="min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            />
          </div>
        </div>

        <DialogFooter class="gap-2">
          <Button variant="outline" @click="showEditDialog = false">取消</Button>
          <Button :disabled="submitting" class="gap-2" @click="submitEditAccount">
            <Loader2Icon v-if="submitting" class="h-4 w-4 animate-spin" />
            保存
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- 查看账号详情对话框 -->
    <Dialog v-model:open="showViewDialog">
      <DialogContent class="sm:max-w-[860px]">
        <DialogHeader>
          <DialogTitle>账号详情</DialogTitle>
          <DialogDescription>查看账号关键字段与状态信息</DialogDescription>
        </DialogHeader>

        <div v-if="selectedAccount" class="grid gap-4 py-2 sm:grid-cols-2">
          <div class="space-y-1">
            <div class="text-xs text-muted-foreground">ID</div>
            <div class="font-mono text-sm">#{{ selectedAccount.id }}</div>
          </div>

          <div class="space-y-1">
            <div class="text-xs text-muted-foreground">邮箱</div>
            <div class="text-sm break-all">{{ selectedAccount.email }}</div>
          </div>

          <div class="space-y-1">
            <div class="text-xs text-muted-foreground">分组</div>
            <div>
              <Badge v-if="selectedAccount.group_name" variant="outline" class="rounded-full">{{ selectedAccount.group_name }}</Badge>
              <span v-else class="text-sm text-muted-foreground">未分组</span>
            </div>
          </div>

          <div class="space-y-1">
            <div class="text-xs text-muted-foreground">分类</div>
            <div>
              <Badge variant="secondary" class="rounded-full">
                {{ selectedAccount.type_display || selectedAccount.type_tag || '-' }}
              </Badge>
            </div>
          </div>

          <div class="space-y-1">
            <div class="text-xs text-muted-foreground">状态</div>
            <div>
              <Badge variant="secondary" class="rounded-full">
                {{ selectedAccount.status_display || selectedAccount.status }}
              </Badge>
            </div>
          </div>

          <div class="space-y-2 sm:col-span-2">
            <div class="text-xs text-muted-foreground">主线进度</div>
            <div class="flex flex-wrap gap-2">
              <div
                v-for="(step, index) in getMainFlowProgress(selectedAccount)"
                :key="`detail-${index}`"
                class="inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-xs"
                :class="step.done ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-700' : 'border-muted-foreground/20 bg-muted/20 text-muted-foreground'"
              >
                <span class="inline-flex h-5 w-5 items-center justify-center rounded-full border text-[11px] font-semibold"
                  :class="step.done ? 'border-emerald-500/40 bg-emerald-500/15 text-emerald-700' : 'border-muted-foreground/30 bg-muted/30 text-muted-foreground'"
                >
                  {{ index + 1 }}
                </span>
                <span>{{ step.label }}</span>
              </div>
            </div>
          </div>

          <div class="space-y-1">
            <div class="text-xs text-muted-foreground">SheerID 状态</div>
            <div>
              <Badge :variant="selectedAccount.sheerid_verified ? 'default' : 'secondary'" class="rounded-full">
                {{ selectedAccount.sheerid_verified ? '已验证' : '未验证' }}
              </Badge>
            </div>
          </div>

          <div class="space-y-1">
            <div class="text-xs text-muted-foreground">Gemini 状态</div>
            <div>
              <Badge variant="outline" class="rounded-full">
                {{ getGeminiStatusText(selectedAccount.gemini_status || 'not_subscribed') }}
              </Badge>
            </div>
          </div>

          <div class="space-y-1">
            <div class="text-xs text-muted-foreground">是否绑卡</div>
            <div>
              <Badge :variant="selectedAccount.card_bound ? 'default' : 'secondary'" class="rounded-full">
                {{ selectedAccount.card_bound ? '已绑卡' : '未绑卡' }}
              </Badge>
            </div>
          </div>

          <div class="space-y-1 sm:col-span-2">
            <div class="text-xs text-muted-foreground">恢复邮箱</div>
            <div class="text-sm break-all">{{ selectedAccount.recovery_email || '无' }}</div>
          </div>

          <div class="space-y-1 sm:col-span-2">
            <div class="text-xs text-muted-foreground">SheerID 链接</div>
            <div>
              <a
                v-if="selectedAccount.sheerid_link"
                :href="selectedAccount.sheerid_link"
                target="_blank"
                rel="noreferrer"
                class="text-sm text-primary hover:underline underline-offset-4 break-all"
              >
                {{ selectedAccount.sheerid_link }}
              </a>
              <span v-else class="text-sm text-muted-foreground">无</span>
            </div>
          </div>

          <div class="space-y-1 sm:col-span-2">
            <div class="text-xs text-muted-foreground">最后登录</div>
            <div class="text-sm">{{ selectedAccount.last_login_at ? formatDate(selectedAccount.last_login_at) : '从未登录' }}</div>
          </div>

          <div class="space-y-1 sm:col-span-2">
            <div class="text-xs text-muted-foreground">创建时间</div>
            <div class="text-sm">{{ formatDate(selectedAccount.created_at) }}</div>
          </div>

          <div class="space-y-1 sm:col-span-2">
            <div class="text-xs text-muted-foreground">备注</div>
            <div class="text-sm whitespace-pre-wrap">{{ selectedAccount.notes || '无' }}</div>
          </div>

          <div class="space-y-1 sm:col-span-2">
            <div class="text-xs text-muted-foreground">New-2FA</div>
            <div class="flex flex-wrap items-center gap-2">
              <template v-if="selectedAccount.new_2fa_display || selectedAccount.new_2fa">
                <code class="rounded bg-muted px-2 py-1 font-mono text-xs">{{ format2fa(selectedAccount.new_2fa_display || selectedAccount.new_2fa) }}</code>
                <span v-if="selectedAccount.new_2fa_updated_at" class="text-xs text-muted-foreground">
                  {{ formatDate(selectedAccount.new_2fa_updated_at) }}
                </span>
              </template>
              <span v-else class="text-sm text-muted-foreground">-</span>
            </div>
          </div>
        </div>

        <div v-else class="py-8 text-center text-sm text-muted-foreground">暂无账号详情</div>

        <DialogFooter class="gap-2">
          <Button variant="outline" @click="showViewDialog = false">关闭</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- 任务日志抽屉 -->
    <Sheet v-model:open="showTasksDrawer">
      <SheetContent side="right" class="w-full sm:max-w-[900px]">
        <SheetHeader>
          <SheetTitle>任务记录</SheetTitle>
          <SheetDescription>当前账号的任务与执行日志入口</SheetDescription>
        </SheetHeader>

        <div class="mt-4">
          <div v-if="drawerLoading" class="py-10 text-center text-sm text-muted-foreground">
            <span class="inline-flex items-center gap-2">
              <Loader2Icon class="h-4 w-4 animate-spin" />
              加载中...
            </span>
          </div>

          <div v-else class="space-y-6">
            <div class="overflow-x-auto rounded-xl border border-border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead class="w-24">来源</TableHead>
                    <TableHead class="min-w-[220px]">类型</TableHead>
                    <TableHead class="w-28">状态</TableHead>
                    <TableHead class="w-20">进度</TableHead>
                    <TableHead class="w-56">步骤</TableHead>
                    <TableHead class="min-w-[180px]">增项</TableHead>
                    <TableHead class="w-44">时间</TableHead>
                    <TableHead class="w-20 text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <TableRow v-for="row in accountTasks.tasks" :key="row.record_id" class="hover:bg-muted/20">
                    <TableCell>
                      <Badge :variant="row.source === 'google' ? 'default' : 'secondary'" class="rounded-full">
                        任务
                      </Badge>
                    </TableCell>
                    <TableCell class="truncate">{{ row.name }}</TableCell>
                    <TableCell>
                      <Badge
                        v-if="row.source === 'google'"
                        :variant="row.status === 'completed' ? 'default' : (row.status === 'failed' ? 'destructive' : 'secondary')"
                        class="rounded-full"
                      >
                        {{ row.status_display || row.status }}
                      </Badge>
                      <Badge
                        v-else-if="row.state"
                        :variant="row.state === 'SUCCESS' ? 'default' : (row.state === 'FAILURE' ? 'destructive' : 'secondary')"
                        class="rounded-full"
                      >
                        {{ row.state }}
                      </Badge>
                      <span v-else class="text-xs text-muted-foreground">-</span>
                    </TableCell>
                    <TableCell class="text-muted-foreground">
                      <span v-if="row.source === 'google'">{{ row.progress_percentage ?? 0 }}%</span>
                      <span v-else>-</span>
                    </TableCell>
                    <TableCell>
                      <span v-if="row.source === 'google' && row.task_type === 'one_click'">
                        <span class="font-medium">{{ row.main_flow_step_num ? `${row.main_flow_step_num}/6` : '-' }}</span>
                        <span class="ml-2 text-xs text-muted-foreground">{{ row.main_flow_step_title || '' }}</span>
                      </span>
                      <span v-else class="text-xs text-muted-foreground">-</span>
                    </TableCell>
                    <TableCell>
                      <div
                        v-if="row.source === 'google' && row.task_type === 'one_click' && Array.isArray(row.main_flow_extras) && row.main_flow_extras.length > 0"
                        class="flex flex-wrap gap-1"
                      >
                        <Badge v-for="ex in row.main_flow_extras" :key="ex" variant="outline" class="rounded-full">
                          {{ ex }}
                        </Badge>
                      </div>
                      <span v-else class="text-xs text-muted-foreground">-</span>
                    </TableCell>
                    <TableCell class="text-muted-foreground">{{ formatDate(row.created_at) }}</TableCell>
                    <TableCell class="text-right">
                      <Button
                        variant="link"
                        size="xs"
                        class="h-auto p-0"
                        @click="row.source === 'google' ? viewTaskLog(row.google_task_id) : openCeleryTask(String(row.celery_task_id), selectedAccount?.email)"
                      >
                        日志
                      </Button>
                    </TableCell>
                  </TableRow>

                  <TableRow v-if="accountTasks.tasks.length === 0">
                    <TableCell colspan="8" class="py-10 text-center text-sm text-muted-foreground">暂无任务记录</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </div>

            <div class="h-px w-full bg-border" />

            <div class="overflow-x-auto rounded-xl border border-border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead class="w-24">任务ID</TableHead>
                    <TableHead class="w-28">账号状态</TableHead>
                    <TableHead class="min-w-[260px]">结果</TableHead>
                    <TableHead class="min-w-[260px]">错误</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <TableRow v-for="row in accountTasks.task_accounts" :key="row.task_id" class="hover:bg-muted/20">
                    <TableCell class="font-mono text-xs text-muted-foreground">#{{ row.task_id }}</TableCell>
                    <TableCell class="text-muted-foreground">{{ row.status_display || '-' }}</TableCell>
                    <TableCell class="text-muted-foreground">{{ row.result_message || '-' }}</TableCell>
                    <TableCell class="text-destructive">{{ row.error_message || '-' }}</TableCell>
                  </TableRow>

                  <TableRow v-if="accountTasks.task_accounts.length === 0">
                    <TableCell colspan="4" class="py-10 text-center text-sm text-muted-foreground">暂无账号任务记录</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>

    <!-- 通用日志查看Dialog -->
    <Dialog v-model:open="showLogDialog">
      <DialogContent class="sm:max-w-[900px]">
        <DialogHeader>
          <DialogTitle>任务日志</DialogTitle>
          <DialogDescription>步骤、增项与日志内容</DialogDescription>
        </DialogHeader>

        <div v-if="currentSteps.length > 0" class="mb-4 rounded-xl border border-border bg-muted/20 p-4">
          <div class="mb-3 flex items-center justify-between">
            <div class="text-sm font-semibold">流程步骤</div>
            <div class="text-xs text-muted-foreground">
              {{ Math.min(activeStep + 1, currentSteps.length) }}/{{ currentSteps.length }}
            </div>
          </div>

          <div class="h-2 w-full rounded-full bg-muted overflow-hidden">
            <div
              class="h-full bg-primary transition-all"
              :style="{ width: `${currentSteps.length ? Math.round(((activeStep + 1) / currentSteps.length) * 100) : 0}%` }"
            />
          </div>

          <div class="mt-4 grid gap-2">
            <div
              v-for="(step, index) in currentSteps"
              :key="index"
              class="flex items-start gap-3 rounded-lg border border-border bg-background/60 px-3 py-2"
              :class="index === activeStep ? 'ring-1 ring-ring' : ''"
            >
              <div class="mt-0.5 h-6 w-6 rounded-full bg-muted flex items-center justify-center text-xs font-semibold">
                {{ index + 1 }}
              </div>
              <div class="min-w-0 flex-1">
                <div class="font-medium truncate">{{ step.title }}</div>
                <div class="text-xs text-muted-foreground">{{ step.time }}</div>
              </div>
            </div>
          </div>

          <div v-if="currentLogExtras.length > 0" class="mt-4 flex flex-wrap gap-2">
            <span
              v-for="extra in currentLogExtras"
              :key="extra"
              class="inline-flex items-center rounded-full border border-amber-500/20 bg-amber-500/10 px-2 py-0.5 text-xs text-amber-700"
            >
              {{ extra }}
            </span>
          </div>
        </div>

        <div class="max-h-[520px] overflow-auto rounded-xl border border-border bg-muted/20 p-4">
          <pre class="whitespace-pre-wrap font-mono text-xs text-foreground">{{ currentLogContent }}</pre>
        </div>
      </DialogContent>
    </Dialog>

    <!-- Celery 任务：实时 trace 日志（滚动 + 轮询） -->
    <Dialog
      :open="showCeleryDialog"
      @update:open="(open) => { showCeleryDialog = open; if (!open) onCeleryDialogClosed() }"
    >
      <DialogContent class="sm:max-w-[1000px]">
        <DialogHeader>
          <DialogTitle>{{ celeryDialogTitle }}</DialogTitle>
          <DialogDescription>实时 trace（支持上滑加载历史）</DialogDescription>
        </DialogHeader>

        <div class="rounded-xl border border-border bg-muted/20 p-4">
          <div class="grid gap-3 sm:grid-cols-2">
            <div>
              <div class="text-xs text-muted-foreground">任务ID</div>
              <div class="font-mono text-sm">{{ celeryTaskId || '-' }}</div>
            </div>
            <div>
              <div class="text-xs text-muted-foreground">账号</div>
              <div class="text-sm break-all">{{ celeryEmail || '-' }}</div>
            </div>
            <div>
              <div class="text-xs text-muted-foreground">state</div>
              <Badge variant="outline" class="rounded-full">{{ celeryState || '-' }}</Badge>
            </div>
            <div>
              <div class="text-xs text-muted-foreground">trace_file</div>
              <div class="font-mono text-xs break-all">{{ traceFile || '-' }}</div>
            </div>
          </div>

          <div class="mt-4 flex flex-wrap justify-end gap-2">
            <Button variant="outline" size="sm" @click="refreshCeleryStatus">刷新状态</Button>
            <Button size="sm" @click="reloadTrace">重载日志</Button>
          </div>

          <Accordion type="single" collapsible class="mt-4">
            <AccordionItem value="status">
              <AccordionTrigger>状态详情</AccordionTrigger>
              <AccordionContent>
                <pre class="mt-2 max-h-[200px] overflow-auto rounded-md border border-border bg-background p-3 text-xs">{{ celeryStatusText }}</pre>
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </div>

        <div class="my-4 h-px w-full bg-border" />

        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div class="flex items-center gap-3">
            <div class="flex items-center gap-2">
              <Switch :checked="traceFollowLatest" @update:checked="traceFollowLatest = $event" />
              <span class="text-sm">跟随最新</span>
            </div>
            <span class="text-xs text-muted-foreground">向上滚动加载历史；滚动离开底部会自动停止跟随</span>
          </div>
          <div class="flex items-center justify-end gap-2">
            <Button variant="outline" size="sm" @click="copyTrace">复制</Button>
            <Button variant="outline" size="sm" @click="clearTrace">清空</Button>
          </div>
        </div>

        <div
          ref="traceScrollRef"
          class="h-[520px] overflow-auto rounded-xl border border-border bg-slate-950 text-slate-100 p-3"
          @scroll="onTraceScroll"
        >
          <div
            v-if="traceLoadingOlder"
            class="sticky top-0 z-10 -mx-3 -mt-3 mb-3 border-b border-slate-700/40 bg-slate-950/80 px-3 py-2 text-xs text-slate-100/90 backdrop-blur"
          >
            加载更早日志...
          </div>
          <div
            v-else-if="traceHasMoreBackward"
            class="sticky top-0 z-10 -mx-3 -mt-3 mb-3 border-b border-slate-700/40 bg-slate-950/60 px-3 py-2 text-xs text-slate-100/60 backdrop-blur"
          >
            继续上滑加载更早日志
          </div>

          <div class="font-mono text-xs leading-relaxed whitespace-pre-wrap break-words">
            <div
              v-for="ln in traceLines"
              :key="ln.id"
              class="py-[1px]"
              :class="ln.isJson ? 'text-slate-300/60' : ''"
            >{{ ln.text }}</div>
          </div>
        </div>
      </DialogContent>
    </Dialog>

    <!-- 一键全自动配置（主流程增项） -->
    <Dialog v-model:open="showOneClickDialog">
      <DialogContent class="sm:max-w-[560px]">
        <DialogHeader>
          <DialogTitle>一键全自动</DialogTitle>
          <DialogDescription>主流程：登录 -> Google One -> 检查学生资格 -> 学生验证 -> 订阅 -> 完成</DialogDescription>
        </DialogHeader>

        <Alert class="mb-4">
          <AlertTitle>提示</AlertTitle>
          <AlertDescription>可选增项：安全设置（2FA/辅助邮箱）</AlertDescription>
        </Alert>

        <div class="grid gap-4 py-2">
          <div class="flex items-center justify-between">
            <div>
              <div class="text-sm font-medium">运行模式</div>
              <div class="text-xs text-muted-foreground">默认续跑：已完成步骤会跳过</div>
            </div>
            <Switch :checked="oneClickForm.force_rerun" @update:checked="oneClickForm.force_rerun = $event" />
          </div>
          <div class="text-xs text-muted-foreground">开启强制重跑后，会忽略已完成状态并重新执行</div>

          <div class="flex items-center justify-between">
            <div>
              <div class="text-sm font-medium">增项：修改 2FA</div>
              <div class="text-xs text-muted-foreground">开启后会执行安全更新步骤</div>
            </div>
              <Switch
                :checked="oneClickForm.security_change_2fa"
                @update:checked="oneClickForm.security_change_2fa = $event"
              />
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium">增项：修改辅助邮箱</label>
            <Input v-model="oneClickForm.security_new_recovery_email" placeholder="可选，不填则不修改" />
          </div>
        </div>

        <DialogFooter class="gap-2">
          <Button variant="outline" @click="showOneClickDialog = false">取消</Button>
          <Button @click="submitOneClickTask">开始执行</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- SheerID 验证配置 Dialog -->
    <Dialog v-model:open="showSheerIDDialog">
      <DialogContent class="sm:max-w-[560px]">
        <DialogHeader>
          <DialogTitle>SheerID 批量验证</DialogTitle>
          <DialogDescription>主线步骤 4：学生验证</DialogDescription>
        </DialogHeader>

        <div class="grid gap-4 py-2">
          <div class="grid gap-2">
            <label class="text-sm font-medium">学生姓名</label>
            <Input v-model="sheerIDForm.student_name" placeholder="如: John Doe" />
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium">学生邮箱</label>
            <Input v-model="sheerIDForm.student_email" placeholder="如: student@edu.com" />
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium">学校名称</label>
            <Input v-model="sheerIDForm.school_name" placeholder="如: University of ..." />
          </div>
        </div>

        <DialogFooter class="gap-2">
          <Button variant="outline" @click="showSheerIDDialog = false">取消</Button>
          <Button @click="submitSheerIDTask">开始验证</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- 自动绑卡配置 Dialog -->
    <Dialog v-model:open="showBindCardDialog">
      <DialogContent class="sm:max-w-[560px]">
        <DialogHeader>
          <DialogTitle>自动绑卡</DialogTitle>
          <DialogDescription>主线步骤 5：订阅服务（自动绑卡）</DialogDescription>
        </DialogHeader>

        <Alert class="mb-4" variant="destructive">
          <AlertTitle>注意</AlertTitle>
          <AlertDescription>将占用卡池资源，请确认策略与卡池选择</AlertDescription>
        </Alert>

        <div class="grid gap-4 py-2">
          <div class="grid gap-2">
            <label class="text-sm font-medium">卡池</label>
            <Select v-model="bindCardForm.card_pool">
              <SelectTrigger class="w-full">
                <SelectValue placeholder="选择卡池" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="public">公共卡池</SelectItem>
                <SelectItem value="private">私有卡池</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium">策略</label>
            <Select v-model="bindCardForm.card_strategy">
              <SelectTrigger class="w-full">
                <SelectValue placeholder="选择策略" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="sequential">顺序</SelectItem>
                <SelectItem value="parallel">并发</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <DialogFooter class="gap-2">
          <Button variant="outline" @click="showBindCardDialog = false">取消</Button>
          <Button @click="submitBindCardTask">开始绑卡</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- 安全设置 - 修改辅助邮箱 -->
    <Dialog v-model:open="showRecoveryEmailDialog">
      <DialogContent class="sm:max-w-[560px]">
        <DialogHeader>
          <DialogTitle>修改辅助邮箱</DialogTitle>
          <DialogDescription>为空则不修改</DialogDescription>
        </DialogHeader>

        <div class="grid gap-2 py-2">
          <label class="text-sm font-medium">新辅助邮箱</label>
          <Input v-model="newRecoveryEmail" placeholder="请输入新的辅助邮箱" />
        </div>

        <DialogFooter class="gap-2">
          <Button variant="outline" @click="showRecoveryEmailDialog = false">取消</Button>
          <Button @click="submitChangeRecoveryEmail">确定修改</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- 订阅验证选项 -->
    <Dialog v-model:open="showVerifySubDialog">

    <!-- 2FA 详情弹窗 -->
    <Dialog v-model:open="show2faDialog">
      <DialogContent class="sm:max-w-[400px]">
        <DialogHeader>
          <DialogTitle>2FA 信息</DialogTitle>
          <DialogDescription>{{ current2faAccount?.email }}</DialogDescription>
        </DialogHeader>
        <div class="grid gap-4 py-4">
          <div class="grid gap-2">
            <label class="text-sm font-medium text-muted-foreground">2FA 密钥</label>
            <div class="flex items-center gap-2">
              <code class="flex-1 rounded bg-muted px-3 py-2 font-mono text-sm break-all">
                {{ format2fa(current2faAccount?.new_2fa_display || current2faAccount?.new_2fa || '') }}
              </code>
              <Button
                v-if="current2faAccount?.new_2fa_display || current2faAccount?.new_2fa"
                variant="outline"
                size="sm"
                @click="copy2fa(current2faAccount)"
              >
                复制
              </Button>
            </div>
          </div>
          <div v-if="current2faAccount?.new_2fa_updated_at" class="grid gap-2">
            <label class="text-sm font-medium text-muted-foreground">更新时间</label>
            <div class="text-sm">{{ formatDate(current2faAccount.new_2fa_updated_at) }}</div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" @click="show2faDialog = false">关闭</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- 订阅验证选项 -->
      <DialogContent class="sm:max-w-[520px]">
        <DialogHeader>
          <DialogTitle>验证订阅状态</DialogTitle>
          <DialogDescription>主线步骤 5：订阅服务（校验状态，可选截图）</DialogDescription>
        </DialogHeader>

        <div class="flex items-center justify-between py-2">
          <div>
            <div class="text-sm font-medium">开启截图</div>
            <div class="text-xs text-muted-foreground">开启后将保存截图用于排查问题</div>
          </div>
            <Switch :checked="verifySubScreenshot" @update:checked="verifySubScreenshot = $event" />
        </div>

        <DialogFooter class="gap-2">
          <Button variant="outline" @click="showVerifySubDialog = false">取消</Button>
          <Button @click="submitVerifyStatus">开始验证</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

  </div>
</template>


<script setup lang="ts">
import { ref, reactive, onMounted, computed, nextTick, watch, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from '@/lib/element'
import {
  CheckCircle2,
  CreditCard as CreditCardIcon,
  Loader2 as Loader2Icon,
  Monitor as MonitorIcon,
  Users,
  XCircle,
  KeyRound,
} from 'lucide-vue-next'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { 
  googleAccountsApi, googleTasksApi, googleSecurityApi, 
  googleSubscriptionApi, googleCeleryTasksApi 
} from '@/api/google'
import type { GoogleAccount } from '@/types'

const loading = ref(false)
const submitting = ref(false)
const importing = ref(false)
const accounts = ref<GoogleAccount[]>([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const showDialog = ref(false)
const showImportDialog = ref(false)
const showEditDialog = ref(false)
const showViewDialog = ref(false)
const selectedAccount = ref<GoogleAccount | null>(null)
const importText = ref('')
const filterType = ref('all')
const filterGroup = ref('all')
const groupList = ref<Array<{id: string, name: string}>>([])
const selectedAccounts = ref<GoogleAccount[]>([])

const totalPages = computed(() => {
  const t = Number(total.value) || 0
  const ps = Number(pageSize.value) || 1
  return Math.max(1, Math.ceil(t / ps))
})

const selectedIds = computed(() => new Set(selectedAccounts.value.map(a => a.id)))

// 统计信息
const stats = computed(() => {
  let verified = 0
  let cardBound = 0
  let envCreated = 0
  
  accounts.value.forEach((a: GoogleAccount) => {
    if (a.sheerid_verified) verified++
    if (a.card_bound) cardBound++
    if (a.geekez_profile_exists) envCreated++
  })
  
  return { verified, cardBound, envCreated }
})

// 通知父组件选中数量变化
watch(selectedAccounts, (newVal) => {
  window.dispatchEvent(new CustomEvent('google-selection-changed', { 
    detail: { 
      count: newVal.length,
      account: newVal.length === 1 ? newVal[0] : null
    }
  }))
}, { deep: true, immediate: true })

const isRowSelected = (row: GoogleAccount) => {
  return selectedIds.value.has(row.id)
}

const allSelectedOnPage = computed(() => {
  return accounts.value.length > 0 && accounts.value.every(a => selectedIds.value.has(a.id))
})

const someSelectedOnPage = computed(() => {
  const any = accounts.value.some(a => selectedIds.value.has(a.id))
  return any && !allSelectedOnPage.value
})

const onToggleAllOnPage = (checked: boolean | 'indeterminate') => {
  const isChecked = checked === true
  const idsOnPage = new Set(accounts.value.map(a => a.id))

  if (isChecked) {
    const merged: GoogleAccount[] = []
    const seen = new Set<number>()
    for (const a of selectedAccounts.value) {
      if (!seen.has(a.id)) {
        merged.push(a)
        seen.add(a.id)
      }
    }
    for (const a of accounts.value) {
      if (!seen.has(a.id)) {
        merged.push(a)
        seen.add(a.id)
      }
    }
    selectedAccounts.value = merged
    return
  }

  selectedAccounts.value = selectedAccounts.value.filter(a => !idsOnPage.has(a.id))
}

const onToggleRow = (row: GoogleAccount, checked: boolean) => {
  if (checked) {
    if (!selectedIds.value.has(row.id)) {
      selectedAccounts.value = [...selectedAccounts.value, row]
    }
    return
  }
  selectedAccounts.value = selectedAccounts.value.filter(a => a.id !== row.id)
}

const goPrevPage = async () => {
  if (currentPage.value <= 1) return
  currentPage.value -= 1
  await fetchAccounts()
}

const goNextPage = async () => {
  if (currentPage.value >= totalPages.value) return
  currentPage.value += 1
  await fetchAccounts()
}

const onPageSizeChange = async (v: unknown) => {
  const n = Number.parseInt(String(v ?? ''), 10)
  if (!Number.isFinite(n) || n <= 0) return
  pageSize.value = n
  currentPage.value = 1
  await fetchAccounts()
}

// Dialog visibility
const showTasksDrawer = ref(false)
const showLogDialog = ref(false)
const showCeleryDialog = ref(false)
const showSheerIDDialog = ref(false)
const showBindCardDialog = ref(false)
const showRecoveryEmailDialog = ref(false)
const showVerifySubDialog = ref(false)
const showOneClickDialog = ref(false)
const show2faDialog = ref(false)
const current2faAccount = ref<GoogleAccount | null>(null)

const open2faDialog = (account: GoogleAccount) => {
  current2faAccount.value = account
  show2faDialog.value = true
}

const copy2fa = async (account: GoogleAccount | null) => {
  if (!account) return
  const text = account.new_2fa_display || account.new_2fa || ''
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制 2FA')
  } catch {
    ElMessage.error('复制失败')
  }
}

const launchGeekez = async (account: GoogleAccount) => {
  try {
    await googleAccountsApi.launchGeekez(account.id)
    ElMessage.success(account.geekez_profile_exists ? '正在打开环境...' : '正在创建环境...')
    await fetchAccounts()
  } catch (e: any) {
    ElMessage.error('操作失败: ' + e.message)
  }
}

const editAccount = (account: GoogleAccount) => {
  editForm.id = account.id
  editForm.email = account.email || ''
  editForm.password = ''
  editForm.recovery_email = account.recovery_email || ''
  editForm.secret_key = account.secret_key || ''
  editForm.notes = account.notes || ''
  showEditDialog.value = true
}

const deleteAccount = async (account: GoogleAccount) => {
  try {
    await ElMessageBox.confirm(`确定删除账号 ${account.email}？`, '删除确认', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await googleAccountsApi.deleteAccount(account.id)
    ElMessage.success('删除成功')
    await fetchAccounts()
  } catch (e: any) {
    if (e !== 'cancel' && e?.message !== 'cancel') {
      ElMessage.error('删除失败: ' + e.message)
    }
  }
}

const openTasksDrawer = (account: GoogleAccount) => {
  viewTasks(account)
}

// Data for dialogs
const drawerLoading = ref(false)
const accountTasks = reactive({
  // 统一任务列表（后端 accounts/{id}/tasks/ 返回 tasks 字段）
  tasks: [] as any[],
  // 账号在 GoogleTask 中的执行明细
  task_accounts: [] as any[]
})
const currentLogContent = ref('')
const currentSteps = ref<any[]>([])
const currentLogExtras = ref<string[]>([])
const activeStep = ref(0)

type TraceLine = { id: number; text: string; isJson: boolean }

const celeryTaskId = ref('')
const celeryEmail = ref('')
const celeryState = ref('')
const celeryMeta = ref<any>(null)
const celeryResult = ref<any>(null)
const celeryError = ref('')
const celeryTraceback = ref('')
const celeryStatusLoading = ref(false)

const traceLines = ref<TraceLine[]>([])
const traceHasMoreBackward = ref(false)
const traceCursorBackward = ref<number | null>(null)
const traceCursorForward = ref<number | null>(null)
const traceFollowLatest = ref(true)
const traceLoadingOlder = ref(false)
const tracePollingTimer = ref<number | null>(null)
let tracePollingInFlight = false
const traceFile = ref('')
const traceSize = ref(0)
const traceScrollRef = ref<HTMLElement | null>(null)
let traceLineSeq = 0

const celeryDialogTitle = computed(() => {
  const id = celeryTaskId.value ? `#${celeryTaskId.value}` : ''
  const mail = celeryEmail.value ? ` - ${celeryEmail.value}` : ''
  return `Celery 任务日志 ${id}${mail}`
})

const celeryStatusText = computed(() => {
  const parts: string[] = []
  if (celeryState.value) parts.push(`state: ${celeryState.value}`)
  if (celeryMeta.value) parts.push(`meta: ${JSON.stringify(celeryMeta.value, null, 2)}`)
  if (celeryResult.value) parts.push(`result: ${JSON.stringify(celeryResult.value, null, 2)}`)
  if (celeryError.value) parts.push(`error: ${celeryError.value}`)
  if (celeryTraceback.value) parts.push(`traceback: ${celeryTraceback.value}`)
  return parts.join('\n\n')
})

const stopTracePolling = () => {
  if (tracePollingTimer.value) {
    window.clearInterval(tracePollingTimer.value)
    tracePollingTimer.value = null
  }
  tracePollingInFlight = false
}

const startTracePolling = () => {
  stopTracePolling()
  tracePollingTimer.value = window.setInterval(async () => {
    if (!showCeleryDialog.value) return
    if (!traceFollowLatest.value) return
    if (tracePollingInFlight) return
    tracePollingInFlight = true
    try {
      await fetchTraceForward()
    } finally {
      tracePollingInFlight = false
    }
  }, 1000)
}

watch(traceFollowLatest, (v) => {
  if (!showCeleryDialog.value) return
  if (v) startTracePolling()
  else stopTracePolling()
})

watch(showCeleryDialog, (v) => {
  if (v) {
    if (traceFollowLatest.value) startTracePolling()
  } else {
    stopTracePolling()
  }
})

onBeforeUnmount(() => {
  stopTracePolling()
})

const sheerIDForm = reactive({
  student_name: '',
  student_email: '',
  school_name: '',
})

const bindCardForm = reactive({
  card_pool: 'public',
  card_strategy: 'sequential'
})

const oneClickForm = reactive({
  force_rerun: false,
  security_change_2fa: false,
  security_new_recovery_email: ''
})

const newRecoveryEmail = ref('')
const verifySubScreenshot = ref(false)

const accountForm = reactive({
  email: '',
  password: '',
  recovery_email: '',
  notes: ''
})

const editForm = reactive({
  id: 0,
  email: '',
  password: '',
  recovery_email: '',
  secret_key: '',
  notes: ''
})

const importForm = reactive({
  overwrite_existing: false,
  group_name: ''
})

const importCount = computed(() => {
  if (!importText.value.trim()) return 0
  return importText.value.trim().split('\n').filter(line => line.trim()).length
})

const normalizeSelectValue = (v: unknown, fallback: string) => {
  const s = String(v ?? '').trim()
  return s ? s : fallback
}

const onFilterTypeChange = async (v: unknown) => {
  filterType.value = normalizeSelectValue(v, 'all')
  currentPage.value = 1
  selectedAccounts.value = []
  await fetchAccounts()
}

const onFilterGroupChange = async (v: unknown) => {
  filterGroup.value = normalizeSelectValue(v, 'all')
  currentPage.value = 1
  selectedAccounts.value = []
  await fetchAccounts()
}

const fetchAccounts = async () => {
  loading.value = true
  try {
    const params: any = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    if (filterType.value && filterType.value !== 'all') {
      params.type_tag = filterType.value
    }
    if (filterGroup.value && filterGroup.value !== 'all') {
      if (filterGroup.value === 'ungrouped') {
        params.group_name = '' // 未分组（空字符串）
      } else {
        params.group_name = filterGroup.value
      }
    }
    
    const response = await googleAccountsApi.getAccounts(params)
    // 后端不分页，直接返回数组
    if (Array.isArray(response)) {
      accounts.value = response
      total.value = response.length
    } else if (response.results) {
      // 如果有分页
      accounts.value = response.results
      total.value = response.count || 0
    } else {
      accounts.value = []
      total.value = 0
    }
  } catch (error: any) {
    ElMessage.error('获取账号列表失败: ' + (error.message || '未知错误'))
    accounts.value = []
  } finally {
    loading.value = false
  }
}

const fetchGroups = async () => {
  try {
    // 从账号列表中提取唯一的 group_name 值
    const response = await googleAccountsApi.getAccounts({ page_size: 9999 })
    const allAccounts = Array.isArray(response) ? response : (response.results || [])
    
    // 提取唯一的非空 group_name
    const uniqueGroups = [...new Set(
      allAccounts
        .map((acc: any) => acc.group_name)
        .filter((name: string) => name && name.trim())
    )].sort()
    
    // 转换为下拉选项格式
    groupList.value = uniqueGroups.map((name: string) => ({
      id: name,
      name: name
    }))
    
    // 如果当前筛选的分组不存在了，重置为全部
    if (
      filterGroup.value !== 'all' &&
      filterGroup.value !== 'ungrouped' &&
      !uniqueGroups.includes(filterGroup.value)
    ) {
      filterGroup.value = 'all'
    }
  } catch (error) {
    console.error('获取分组列表失败:', error)
    groupList.value = []
  }
}

const getSelectedIds = () => {
  return selectedAccounts.value.map(acc => acc.id)
}

const handleLaunchGeekez = async (row: GoogleAccount) => {
    try {
        const res = await googleAccountsApi.launchGeekez(row.id)
        const debugPort = res.data?.debug_port || res.debug_port
        const profileId = res.data?.profile_id || res.profile_id
        const createdProfile = res.data?.created_profile ?? res.created_profile
        
        let msg = createdProfile ? '环境创建并打开成功' : '环境打开成功'
        if (debugPort) msg += `, 端口: ${debugPort}`
        if (profileId) msg += `, Profile: ${profileId}`
        
        ElMessage.success(msg)
        fetchAccounts()
    } catch (e: any) {
        ElMessage.error('操作失败: ' + (e.message || '未知错误'))
    }
}

const openOneClickDialog = async () => {
  if (selectedAccounts.value.length === 0) return
  showOneClickDialog.value = true
}

const submitOneClickTask = async () => {
  if (selectedAccounts.value.length === 0) {
    ElMessage.warning('请先选择账号')
    return
  }

  const config: any = {}
  if (oneClickForm.force_rerun) {
    config.force_rerun = true
  } else {
    config.resume = true
  }
  if (oneClickForm.security_change_2fa) {
    config.security_change_2fa = true
  }
  if (oneClickForm.security_new_recovery_email && oneClickForm.security_new_recovery_email.trim()) {
    config.security_new_recovery_email = oneClickForm.security_new_recovery_email.trim()
  }

  try {
    await googleTasksApi.createTask({
      task_type: 'one_click',
      account_ids: getSelectedIds(),
      config
    })
    ElMessage.success('任务已创建')
    showOneClickDialog.value = false
    fetchAccounts()
  } catch (e: any) {
    ElMessage.error('创建任务失败: ' + (e.message || '未知错误'))
  }
}

const handleBatchCommand = (command: string) => {
  if (selectedAccounts.value.length === 0) return
  
  if (command === 'sheerid') {
    showSheerIDDialog.value = true
  } else if (command === 'bind_card') {
    showBindCardDialog.value = true
  }
}

const handleExportCommand = async (command: string) => {
    try {
        const ids = selectedAccounts.value.length > 0 ? getSelectedIds() : []
        let response
        let filename = 'accounts'
        
        if (command === 'csv') {
            response = await googleAccountsApi.exportCsv(ids)
            filename += '.csv'
        } else if (command === 'txt') {
            response = await googleAccountsApi.exportTxt(ids)
            filename += '.txt'
        } else {
            return
        }
        
        // Handle Blob download
        const blob = response instanceof Blob ? response : new Blob([response])
        const url = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.setAttribute('download', filename)
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        window.URL.revokeObjectURL(url)
        
        ElMessage.success('导出成功')
    } catch (e: any) {
        console.error(e)
        ElMessage.error('导出失败: ' + (e.message || '未知错误'))
    }
}

const handleSecurityCommand = async (command: string) => {
  if (selectedAccounts.value.length === 0) return
  const ids = getSelectedIds()

  try {
    if (command === 'change_2fa') {
      await ElMessageBox.confirm('确定修改 2FA 密钥吗？将自动生成新密钥。', '修改 2FA')
      await googleSecurityApi.change2fa({ account_ids: ids })
      ElMessage.success('任务已提交')
    } else if (command === 'change_recovery') {
      newRecoveryEmail.value = ''
      showRecoveryEmailDialog.value = true
    } else if (command === 'get_backup_codes') {
      await ElMessageBox.confirm('确定获取备份验证码吗？', '获取备份码')
      await googleSecurityApi.getBackupCodes({ account_ids: ids })
      ElMessage.success('任务已提交')
    } else if (command === 'one_click_update') {
      await ElMessageBox.confirm('确定执行一键安全更新（修改密码/辅助邮箱/2FA）吗？', '一键安全更新', { type: 'warning' })
      await googleSecurityApi.oneClickUpdate({ account_ids: ids })
      ElMessage.success('任务已提交')
    }
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error('操作失败: ' + (e.message || '未知错误'))
  }
}

const handleSubscriptionCommand = async (command: string) => {
  if (selectedAccounts.value.length === 0) return
  const ids = getSelectedIds()
  
  try {
    if (command === 'verify_status') {
      showVerifySubDialog.value = true
    } else if (command === 'click_subscribe') {
      await ElMessageBox.confirm('确定执行点击订阅操作吗？', '点击订阅')
      await googleSubscriptionApi.clickSubscribe({ account_ids: ids })
      ElMessage.success('任务已提交')
    }
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error('操作失败: ' + (e.message || '未知错误'))
  }
}

const handleBulkDelete = async () => {
  if (selectedAccounts.value.length === 0) {
    ElMessage.warning('请先选择要删除的账号')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedAccounts.value.length} 个账号吗？此操作不可恢复！`,
      '批量删除确认',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const ids = getSelectedIds()
    await googleAccountsApi.bulkDeleteAccounts(ids)
    ElMessage.success(`成功删除 ${ids.length} 个账号`)
    selectedAccounts.value = []
    fetchAccounts()
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error('批量删除失败: ' + (e.message || '未知错误'))
    }
  }
}

// 提交任务
const submitSheerIDTask = async () => {
  if (!sheerIDForm.student_name || !sheerIDForm.student_email || !sheerIDForm.school_name) {
    ElMessage.warning('请填写必要信息')
    return
  }
  
  try {
    await googleTasksApi.createTask({
      task_type: 'verify',
      account_ids: getSelectedIds(),
      config: {
        student_name: sheerIDForm.student_name,
        student_email: sheerIDForm.student_email,
        school_name: sheerIDForm.school_name
      }
    })
    ElMessage.success('SheerID 验证任务已创建')
    showSheerIDDialog.value = false
    fetchAccounts()
  } catch (e: any) {
    ElMessage.error('创建失败: ' + e.message)
  }
}

const submitBindCardTask = async () => {
  try {
    await googleTasksApi.createTask({
      task_type: 'bind_card',
      account_ids: getSelectedIds(),
      config: { 
        card_pool: bindCardForm.card_pool,
        card_strategy: bindCardForm.card_strategy
      }
    })
    ElMessage.success('绑卡任务已创建')
    showBindCardDialog.value = false
    fetchAccounts()
  } catch (e: any) {
    ElMessage.error('创建失败: ' + e.message)
  }
}

const submitChangeRecoveryEmail = async () => {
  if (!newRecoveryEmail.value) {
    ElMessage.warning('请输入邮箱')
    return
  }
  try {
    await googleSecurityApi.changeRecoveryEmail({
      account_ids: getSelectedIds(),
      new_email: newRecoveryEmail.value
    })
    ElMessage.success('任务已提交')
    showRecoveryEmailDialog.value = false
  } catch (e: any) {
    ElMessage.error('操作失败: ' + e.message)
  }
}

const submitVerifyStatus = async () => {
  try {
    await googleSubscriptionApi.verifyStatus({
      account_ids: getSelectedIds(),
      take_screenshot: verifySubScreenshot.value
    })
    ElMessage.success('验证任务已提交')
    showVerifySubDialog.value = false
  } catch (e: any) {
    ElMessage.error('操作失败: ' + e.message)
  }
}

// 任务查看
const viewTasks = async (row: GoogleAccount) => {
  showTasksDrawer.value = true
  drawerLoading.value = true
  selectedAccount.value = row
  try {
    const res = await googleAccountsApi.getAccountTasks(row.id)

    const rawTasks = Array.isArray(res.tasks) ? res.tasks : []
    const rawTaskAccounts = Array.isArray(res.task_accounts) ? res.task_accounts : []

    // 对 celery 任务做一次轻量状态补全（仅最近 10 条，避免频繁请求）
    const tasks = [...rawTasks]
    const celeryTasks = tasks.filter(t => t?.source === 'celery' && t?.celery_task_id)
    const recent = celeryTasks.slice(0, 10)
    for (const t of recent) {
      try {
        const st = await googleCeleryTasksApi.getTask(String(t.celery_task_id))
        t.state = st.state
      } catch {
        // ignore
      }
    }

    accountTasks.tasks = tasks
    accountTasks.task_accounts = rawTaskAccounts
  } catch (e) {
    ElMessage.error('获取任务记录失败')
  } finally {
    drawerLoading.value = false
  }
}

const viewTaskLog = async (taskId: number) => {
  try {
    const res = await googleTasksApi.getTaskLog(taskId)
    // 后端返回：{ task_id, log }
    const logStr = typeof res?.log === 'string' ? res.log : JSON.stringify(res, null, 2)
    currentLogContent.value = logStr
    
    // Parse steps
    currentSteps.value = []
    currentLogExtras.value = []
    activeStep.value = 0
    
    // Define standard steps
    const standardSteps = [
        '登录账号', '打开 Google One', '检查学生资格', '学生验证', '订阅服务', '完成处理'
    ]
    
    // Find highest step reached
    let maxStep = 0
    const stepRegex = /步骤 (\d+)\/6:\s*(.*)/g
    let match
    while ((match = stepRegex.exec(logStr)) !== null) {
        const stepNum = parseInt(match[1])
        if (stepNum > maxStep) maxStep = stepNum
    }
    
    // el-steps 的 active 是索引（0-based），日志里是 1-based
    activeStep.value = maxStep > 0 ? Math.min(maxStep - 1, 5) : 0
    currentSteps.value = standardSteps.map(s => ({ title: s, time: '' }))
    
    // Check extras
    const extraRegex = /增项:\s*(.*)/g
    while ((match = extraRegex.exec(logStr)) !== null) {
        if (!currentLogExtras.value.includes(match[1])) {
            currentLogExtras.value.push(match[1])
        }
    }

    showLogDialog.value = true
  } catch (e) {
    ElMessage.error('获取日志失败')
  }
}

const refreshCeleryStatus = async () => {
  if (!celeryTaskId.value) return
  celeryStatusLoading.value = true
  try {
    const res = await googleCeleryTasksApi.getTask(celeryTaskId.value)
    celeryState.value = res?.state || ''
    celeryMeta.value = res?.meta || null
    celeryResult.value = res?.result || null
    celeryError.value = res?.error || ''
    celeryTraceback.value = res?.traceback || ''
  } catch (e) {
    ElMessage.error('查询任务状态失败')
  } finally {
    celeryStatusLoading.value = false
  }
}

const normalizeTraceLines = (raw: string[]): TraceLine[] => {
  const out: TraceLine[] = []
  for (const t of raw || []) {
    const text = String(t ?? '')
    if (!text) continue
    out.push({
      id: ++traceLineSeq,
      text,
      isJson: text.trim().startsWith('{')
    })
  }
  return out
}

const fetchTraceBackward = async (opts?: { initial?: boolean }) => {
  if (!celeryTaskId.value || !celeryEmail.value) return
  if (traceLoadingOlder.value) return
  traceLoadingOlder.value = true

  const initial = Boolean(opts?.initial)
  const scrollEl = traceScrollRef.value
  const prevHeight = scrollEl?.scrollHeight || 0
  const prevTop = scrollEl?.scrollTop || 0

  try {
    const params: any = {
      email: celeryEmail.value,
      direction: 'backward',
      limit_bytes: 262144
    }
    if (!initial && traceCursorBackward.value !== null) {
      params.cursor = traceCursorBackward.value
    }
    const res = await googleCeleryTasksApi.trace(celeryTaskId.value, params)

    traceFile.value = res?.trace_file || traceFile.value
    traceSize.value = typeof res?.size === 'number' ? res.size : traceSize.value
    traceHasMoreBackward.value = Boolean(res?.has_more)
    traceCursorBackward.value = typeof res?.cursor_out === 'number' ? res.cursor_out : traceCursorBackward.value

    // 初次加载：forward cursor 直接定位到 EOF，后续轮询只拿新增
    if (initial) {
      traceCursorForward.value = traceSize.value
    }

    const newLines = normalizeTraceLines(Array.isArray(res?.lines) ? res.lines : [])
    if (newLines.length > 0) {
      traceLines.value = [...newLines, ...traceLines.value]
    }

    await nextTick()

    if (scrollEl) {
      if (initial) {
        scrollEl.scrollTop = scrollEl.scrollHeight
      } else {
        const newHeight = scrollEl.scrollHeight
        scrollEl.scrollTop = newHeight - prevHeight + prevTop
      }
    }
  } catch (e) {
    ElMessage.error('读取 trace 日志失败')
  } finally {
    traceLoadingOlder.value = false
  }
}

const fetchTraceForward = async () => {
  if (!celeryTaskId.value || !celeryEmail.value) return
  const cursor = traceCursorForward.value
  const params: any = {
    email: celeryEmail.value,
    direction: 'forward',
    limit_bytes: 262144
  }
  if (typeof cursor === 'number') params.cursor = cursor

  try {
    const res = await googleCeleryTasksApi.trace(celeryTaskId.value, params)
    traceFile.value = res?.trace_file || traceFile.value
    traceSize.value = typeof res?.size === 'number' ? res.size : traceSize.value
    traceCursorForward.value = typeof res?.cursor_out === 'number' ? res.cursor_out : traceCursorForward.value

    const raw = Array.isArray(res?.lines) ? res.lines : []
    if (raw.length === 0) return

    const newLines = normalizeTraceLines(raw)
    if (newLines.length === 0) return

    traceLines.value = [...traceLines.value, ...newLines]
    await nextTick()

    const el = traceScrollRef.value
    if (el && traceFollowLatest.value) {
      el.scrollTop = el.scrollHeight
    }
  } catch {
    // forward polling：失败不弹窗，避免刷屏
  }
}

const clearTrace = () => {
  traceLines.value = []
}

const copyTrace = async () => {
  try {
    const text = traceLines.value.map(x => x.text).join('\n')
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制')
  } catch {
    ElMessage.warning('复制失败（浏览器限制）')
  }
}

const onTraceScroll = async () => {
  const el = traceScrollRef.value
  if (!el) return

  // 顶部：加载更早
  if (el.scrollTop <= 0 && traceHasMoreBackward.value) {
    await fetchTraceBackward({ initial: false })
  }

  // 离开底部：自动停止跟随
  const distanceToBottom = el.scrollHeight - (el.scrollTop + el.clientHeight)
  if (distanceToBottom > 80 && traceFollowLatest.value) {
    traceFollowLatest.value = false
  }
}

const reloadTrace = async () => {
  // 重置游标与内容
  traceLines.value = []
  traceHasMoreBackward.value = false
  traceCursorBackward.value = null
  traceCursorForward.value = null
  traceFile.value = ''
  traceSize.value = 0
  await fetchTraceBackward({ initial: true })
}

const openCeleryTask = async (taskId: string, email?: string | null) => {
  stopTracePolling()

  const resolvedEmail = String(email || selectedAccount.value?.email || '').trim()
  if (!resolvedEmail) {
    ElMessage.error('未找到账号邮箱，无法读取 trace（请先打开账号的任务日志）')
    return
  }

  celeryTaskId.value = taskId
  celeryEmail.value = resolvedEmail
  showCeleryDialog.value = true

  // 初始化状态
  celeryState.value = ''
  celeryMeta.value = null
  celeryResult.value = null
  celeryError.value = ''
  celeryTraceback.value = ''

  traceFollowLatest.value = true
  await refreshCeleryStatus()
  await reloadTrace()
  startTracePolling()
}

const onCeleryDialogClosed = () => {
  stopTracePolling()
}

const handleAddAccount = async () => {
  if (!accountForm.email || !accountForm.password) {
    ElMessage.warning('请填写邮箱和密码')
    return
  }

  submitting.value = true
  try {
    await googleAccountsApi.createAccount(accountForm)
    ElMessage.success('添加成功')
    showDialog.value = false
    Object.assign(accountForm, { email: '', password: '', recovery_email: '', notes: '' })
    fetchAccounts()
  } catch (error: any) {
    ElMessage.error('添加失败: ' + (error.message || '未知错误'))
  } finally {
    submitting.value = false
  }
}

const openEditDialog = (row: GoogleAccount) => {
    editForm.id = row.id
    editForm.email = row.email
    editForm.password = '' // Don't show password
    editForm.recovery_email = row.recovery_email || ''
    editForm.secret_key = '' // 2FA Secret usually not returned or hidden
    editForm.notes = row.notes || ''
    showEditDialog.value = true
}

const submitEditAccount = async () => {
    submitting.value = true
    try {
        const payload: any = {
            recovery_email: editForm.recovery_email,
            notes: editForm.notes
        }
        if (editForm.password) payload.password = editForm.password
        if (editForm.secret_key) payload.secret_key = editForm.secret_key
        
        await googleAccountsApi.editAccount(editForm.id, payload)
        ElMessage.success('更新成功')
        showEditDialog.value = false
        fetchAccounts()
    } catch (e: any) {
        ElMessage.error('更新失败: ' + (e.message || '未知错误'))
    } finally {
        submitting.value = false
    }
}

const handleImportAccounts = async () => {
  if (!importText.value.trim()) {
    ElMessage.warning('请输入账号数据')
    return
  }

  const lines = importText.value.trim().split('\n').filter(line => line.trim())
  if (lines.length === 0) {
    ElMessage.warning('没有有效的账号数据')
    return
  }

  importing.value = true
  try {
    const response = await googleAccountsApi.importAccounts({
      accounts: lines,
      format: 'email----password----recovery----secret',
      overwrite_existing: importForm.overwrite_existing,
      group_name: importForm.group_name || undefined
    })
    
    if (response.success || (response.created_count !== undefined && response.created_count >= 0)) {
      const created = response.created_count ?? response.data?.created_count ?? response.imported_count ?? 0
      const updated = response.updated_count ?? response.data?.updated_count ?? 0
      const failed = response.failed_count ?? response.data?.failed_count ?? 0
      const skipped = response.skipped_count ?? 0
      const groupInfo = response.group ? ` [分组: ${response.group.name}]` : ''
      
      ElMessage.success(
        `导入完成！新增 ${created} 个，更新 ${updated} 个，跳过 ${skipped} 个，失败 ${failed} 个${groupInfo}`
      )
      showImportDialog.value = false
      importText.value = ''
      importForm.overwrite_existing = false
      importForm.group_name = ''
      fetchAccounts()
    } else {
      ElMessage.error('导入失败: ' + (response.message || '未知错误'))
    }
  } catch (error: any) {
    ElMessage.error('导入失败: ' + (error.message || '未知错误'))
  } finally {
    importing.value = false
  }
}

const viewAccount = (account: GoogleAccount) => {
  selectedAccount.value = account
  showViewDialog.value = true
}

const MAIN_FLOW_STEPS = [
  '登录账号',
  '打开 Google One',
  '检查学生资格',
  '学生验证',
  '订阅服务',
  '完成处理'
]

const getMainFlowProgress = (account?: GoogleAccount | null) => {
  if (!account) {
    return MAIN_FLOW_STEPS.map(label => ({ label, done: false }))
  }

  const status = String(account.status || '').toLowerCase()
  const googleOneStatus = String(account.google_one_status || '').toLowerCase()
  const geminiStatus = String(account.gemini_status || '').toLowerCase()

  const statusEligible = ['link_ready', 'verified', 'subscribed', 'ineligible']
  const googleOneEligible = ['link_ready', 'verified', 'subscribed', 'ineligible']

  const hasVerify = Boolean(account.sheerid_verified)
  const hasEligibility =
    statusEligible.includes(status) ||
    googleOneEligible.includes(googleOneStatus) ||
    Boolean(account.sheerid_link) ||
    hasVerify

  const hasOpenOne = hasEligibility || Boolean(googleOneStatus)

  const hasLogin =
    Boolean(account.last_login_at) ||
    ['logged_in', ...statusEligible].includes(status) ||
    hasOpenOne ||
    hasVerify ||
    Boolean(account.card_bound)

  const hasSubscribe =
    Boolean(account.card_bound) ||
    Boolean(account.subscribed) ||
    googleOneStatus === 'subscribed' ||
    ['active', 'subscribed'].includes(geminiStatus)

  const hasComplete = hasSubscribe

  return [
    { label: MAIN_FLOW_STEPS[0], done: hasLogin },
    { label: MAIN_FLOW_STEPS[1], done: hasOpenOne },
    { label: MAIN_FLOW_STEPS[2], done: hasEligibility },
    { label: MAIN_FLOW_STEPS[3], done: hasVerify },
    { label: MAIN_FLOW_STEPS[4], done: hasSubscribe },
    { label: MAIN_FLOW_STEPS[5], done: hasComplete }
  ]
}

const getGeminiStatusText = (status: string) => {
  const texts: Record<string, string> = {
    'not_subscribed': '未订阅',
    'pending': '订阅中',
    'active': '已订阅',
    'expired': '已过期',
    'cancelled': '已取消'
  }
  return texts[status] || status
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// New-2FA 展示：去除中间空格（Google 提示 spaces don't matter）
const format2fa = (val?: string | null) => {
  return String(val || '').replace(/\s+/g, '')
}

// 单账号操作事件处理
const handleLaunchGeekezEvent = () => {
  if (selectedAccounts.value.length === 1) {
    handleLaunchGeekez(selectedAccounts.value[0])
  }
}
const handleEditAccountEvent = () => {
  if (selectedAccounts.value.length === 1) {
    openEditDialog(selectedAccounts.value[0])
  }
}
const handleViewTasksEvent = () => {
  if (selectedAccounts.value.length === 1) {
    viewTasks(selectedAccounts.value[0])
  }
}

// 事件处理函数
const handleRefreshEvent = () => fetchAccounts()
const handleAddDialogEvent = () => { showDialog.value = true }
const handleImportDialogEvent = () => { showImportDialog.value = true }
const handleOneClickDialogEvent = () => { openOneClickDialog() }
const handleClearSelectionEvent = () => { selectedAccounts.value = [] }
const handleExportEvent = (e: Event) => { handleExportCommand((e as CustomEvent).detail) }
const handleBatchCommandEvent = (e: Event) => { handleBatchCommand((e as CustomEvent).detail) }
const handleSecurityCommandEvent = (e: Event) => { handleSecurityCommand((e as CustomEvent).detail) }
const handleSubscriptionCommandEvent = (e: Event) => { handleSubscriptionCommand((e as CustomEvent).detail) }
const handleBulkDeleteEvent = () => { handleBulkDelete() }

onMounted(() => {
  fetchAccounts()
  fetchGroups()

  // 监听父组件事件
  window.addEventListener('google-accounts-refresh', handleRefreshEvent)
  window.addEventListener('google-open-add-dialog', handleAddDialogEvent)
  window.addEventListener('google-open-import-dialog', handleImportDialogEvent)
  window.addEventListener('google-open-oneclick-dialog', handleOneClickDialogEvent)
  window.addEventListener('google-clear-selection', handleClearSelectionEvent)
  window.addEventListener('google-export', handleExportEvent as EventListener)
  window.addEventListener('google-batch-command', handleBatchCommandEvent as EventListener)
  window.addEventListener('google-security-command', handleSecurityCommandEvent as EventListener)
  window.addEventListener('google-subscription-command', handleSubscriptionCommandEvent as EventListener)
  window.addEventListener('google-bulk-delete', handleBulkDeleteEvent)
  // 单账号操作
  window.addEventListener('google-launch-geekez', handleLaunchGeekezEvent)
  window.addEventListener('google-edit-account', handleEditAccountEvent)
  window.addEventListener('google-view-tasks', handleViewTasksEvent)
})

onBeforeUnmount(() => {
  // 清理事件监听
  window.removeEventListener('google-accounts-refresh', handleRefreshEvent)
  window.removeEventListener('google-open-add-dialog', handleAddDialogEvent)
  window.removeEventListener('google-open-import-dialog', handleImportDialogEvent)
  window.removeEventListener('google-open-oneclick-dialog', handleOneClickDialogEvent)
  window.removeEventListener('google-clear-selection', handleClearSelectionEvent)
  window.removeEventListener('google-export', handleExportEvent as EventListener)
  window.removeEventListener('google-batch-command', handleBatchCommandEvent as EventListener)
  window.removeEventListener('google-security-command', handleSecurityCommandEvent as EventListener)
  window.removeEventListener('google-subscription-command', handleSubscriptionCommandEvent as EventListener)
  window.removeEventListener('google-bulk-delete', handleBulkDeleteEvent)
  // 单账号操作
  window.removeEventListener('google-launch-geekez', handleLaunchGeekezEvent)
  window.removeEventListener('google-edit-account', handleEditAccountEvent)
  window.removeEventListener('google-view-tasks', handleViewTasksEvent)
})
</script>
