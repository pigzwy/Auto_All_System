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
          <Input
            :model-value="filterEmail"
            placeholder="邮箱模糊搜索"
            class="h-9 w-56"
            @update:modelValue="(v) => onFilterEmailChange(v)"
          />

          <Select :model-value="filterType" @update:modelValue="(v) => onFilterTypeChange(v)">
            <SelectTrigger class="h-9 w-36">
              <SelectValue placeholder="状态筛选" />
            </SelectTrigger>
            <SelectContent class="max-h-[400px]">
              <SelectItem value="all">
                <span class="flex items-center gap-2">
                  <span class="h-2 w-2 rounded-full bg-slate-400" />
                  全部
                </span>
              </SelectItem>

              <!-- 主线流程状态（与列表步骤一致） -->
              <div class="px-2 py-1.5 text-xs font-medium text-muted-foreground">流程状态</div>
              <SelectItem value="unopened">
                <span class="flex items-center gap-2">
                  <span class="h-2 w-2 rounded-full bg-slate-300" />
                  未开
                </span>
              </SelectItem>
              <SelectItem value="logged_in">
                <span class="flex items-center gap-2">
                  <span class="h-2 w-2 rounded-full bg-blue-400" />
                  登录账号
                </span>
              </SelectItem>
              <SelectItem value="link_ready">
                <span class="flex items-center gap-2">
                  <span class="h-2 w-2 rounded-full bg-cyan-500" />
                  检查学生资格
                </span>
              </SelectItem>
              <SelectItem value="verified">
                <span class="flex items-center gap-2">
                  <span class="h-2 w-2 rounded-full bg-violet-500" />
                  学生验证
                </span>
              </SelectItem>
              <SelectItem value="card_bound">
                <span class="flex items-center gap-2">
                  <span class="h-2 w-2 rounded-full bg-amber-500" />
                  订阅服务
                </span>
              </SelectItem>
              <SelectItem value="subscribed">
                <span class="flex items-center gap-2">
                  <span class="h-2 w-2 rounded-full bg-emerald-500" />
                  完成处理
                </span>
              </SelectItem>
            </SelectContent>
          </Select>

          <Select
            v-if="filterType === 'logged_in'"
            :model-value="filterLoginResult"
            @update:modelValue="(v) => onFilterLoginResultChange(v)"
          >
            <SelectTrigger class="h-9 w-32">
              <SelectValue placeholder="登录结果" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部结果</SelectItem>
              <SelectItem value="success">登录成功</SelectItem>
              <SelectItem value="failed">登录失败</SelectItem>
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
                    :model-value="allSelectedOnPage ? true : (someSelectedOnPage ? 'indeterminate' : false)"
                    @update:modelValue="onToggleAllOnPage"
                  />
                </TableHead>
                <TableHead class="w-20">ID</TableHead>
                <TableHead class="min-w-[260px]">邮箱</TableHead>
                <TableHead class="min-w-[320px]">状态</TableHead>
                <TableHead class="w-24">n-2fa</TableHead>
                <TableHead class="w-28">环境</TableHead>
                <TableHead class="w-28">分组</TableHead>
                <TableHead class="w-44">创建时间</TableHead>
                <TableHead class="min-w-[220px]">备注</TableHead>
                <TableHead class="w-28 text-right">操作</TableHead>
              </TableRow>
            </TableHeader>

            <TableBody>
              <TableRow v-if="loading">
                <TableCell colspan="10" class="py-10">
                  <div class="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                    <Loader2Icon class="h-4 w-4 animate-spin" />
                    加载中...
                  </div>
                </TableCell>
              </TableRow>

              <TableRow v-else-if="accounts.length === 0">
                <TableCell colspan="10" class="py-10 text-center text-sm text-muted-foreground">
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
                    :model-value="isRowSelected(row)"
                    @update:modelValue="(v: boolean | 'indeterminate') => onToggleRow(row, v === true)"
                  />
                </TableCell>

                <TableCell class="font-mono text-xs text-muted-foreground">#{{ row.id }}</TableCell>

                <TableCell>
                  <div class="flex items-center gap-2">
                    <Loader2Icon
                      v-if="isAccountRunning(row.id)"
                      class="h-3.5 w-3.5 animate-spin text-primary/70"
                      title="运行中"
                    />
                    <button
                      type="button"
                      class="max-w-[320px] truncate text-left text-primary hover:underline underline-offset-4"
                      :title="row.email"
                      @click="viewAccount(row)"
                    >
                      {{ row.email }}
                    </button>
                  </div>
                </TableCell>

                <TableCell>
                  <div class="flex flex-wrap items-center gap-1.5">
                    <Badge
                      v-for="(step, index) in getMainFlowProgress(row)"
                      :key="`${row.id}-${index}`"
                      variant="outline"
                      class="rounded-[3px] text-[11px] leading-4"
                      :class="step.state === 'success'
                        ? 'bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-400 dark:border-emerald-800'
                        : (step.state === 'failed'
                          ? 'bg-rose-100 text-rose-700 border-rose-200 dark:bg-rose-900/30 dark:text-rose-400 dark:border-rose-800'
                          : 'bg-slate-100 text-slate-600 border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700')"
                      :title="`${index + 1}. ${step.label}`"
                    >
                      {{ step.label }}
                    </Badge>
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

                <TableCell>
                  <Badge v-if="row.group_name" variant="outline" class="rounded-full text-xs">{{ row.group_name }}</Badge>
                  <span v-else class="text-xs text-muted-foreground">-</span>
                </TableCell>

                <TableCell class="text-muted-foreground">
                  {{ formatDate(row.created_at) }}
                </TableCell>

                <TableCell>
                  <span
                    class="block max-w-[280px] truncate text-xs text-muted-foreground"
                    :title="row.notes || ''"
                  >
                    {{ row.notes || '-' }}
                  </span>
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
            <div class="text-xs text-muted-foreground">密码</div>
            <div class="flex items-center gap-2">
              <code v-if="selectedAccount.password" class="flex-1 rounded bg-muted px-2 py-1 font-mono text-sm break-all">
                {{ showDetailPassword ? selectedAccount.password : '••••••••' }}
              </code>
              <span v-else class="text-sm text-muted-foreground">无</span>
              <Button
                v-if="selectedAccount.password"
                variant="ghost"
                size="sm"
                class="h-7 px-2"
                @click="showDetailPassword = !showDetailPassword"
              >
                <Eye v-if="!showDetailPassword" class="h-4 w-4" />
                <EyeOff v-else class="h-4 w-4" />
              </Button>
              <Button
                v-if="selectedAccount.password"
                variant="ghost"
                size="sm"
                class="h-7 px-2"
                @click="copyToClipboard(selectedAccount.password, '密码')"
              >
                <Copy class="h-4 w-4" />
              </Button>
            </div>
          </div>

          <div class="space-y-1 sm:col-span-2">
            <div class="text-xs text-muted-foreground">2FA 密钥</div>
            <div class="flex items-center gap-2">
              <template v-if="selectedAccount.two_fa || selectedAccount.new_2fa_display || selectedAccount.new_2fa">
                <code class="flex-1 rounded bg-muted px-2 py-1 font-mono text-sm break-all">
                  {{ format2fa(selectedAccount.two_fa || selectedAccount.new_2fa_display || selectedAccount.new_2fa) }}
                </code>
                <Button
                  variant="ghost"
                  size="sm"
                  class="h-7 px-2"
                  @click="copyToClipboard(selectedAccount.two_fa || selectedAccount.new_2fa_display || selectedAccount.new_2fa || '', '2FA 密钥')"
                >
                  <Copy class="h-4 w-4" />
                </Button>
              </template>
              <span v-else class="text-sm text-muted-foreground">无</span>
            </div>
            <div v-if="selectedAccount.new_2fa_updated_at" class="text-xs text-muted-foreground">
              更新于 {{ formatDate(selectedAccount.new_2fa_updated_at) }}
            </div>
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
              <div class="flex items-center gap-2">
                <span
                  v-for="(step, index) in getMainFlowProgress(selectedAccount)"
                  :key="`detail-${index}`"
                  class="h-3 w-3 rounded-full"
                  :class="step.state === 'success'
                    ? 'bg-emerald-500'
                    : (step.state === 'failed' ? 'bg-rose-500' : 'bg-muted-foreground/30')"
                  :title="`${index + 1}. ${step.label}`"
                />
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
                        <span
                          class="font-medium"
                          :class="{ 'text-destructive': row.status === 'failed' }"
                        >{{ row.main_flow_step_num ? `${row.main_flow_step_num}/6` : '-' }}</span>
                        <span
                          class="ml-2 text-xs"
                          :class="row.status === 'failed' ? 'text-destructive' : 'text-muted-foreground'"
                        >{{ row.main_flow_step_title || '' }}</span>
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
                      <div class="flex items-center justify-end gap-2">
                        <Button
                          variant="link"
                          size="xs"
                          class="h-auto p-0"
                          @click="row.source === 'google' ? viewTaskLog(row.google_task_id, selectedAccount) : openCeleryTask(String(row.celery_task_id), selectedAccount?.email)"
                        >
                          日志
                        </Button>
                        <Button
                          v-if="row.source === 'google' && row.google_task_id && ['running', 'pending'].includes(row.status)"
                          variant="outline"
                          size="xs"
                          class="h-6 border-destructive/40 text-destructive hover:bg-destructive/10"
                          @click.stop="cancelTask(row.google_task_id)"
                        >
                          中断
                        </Button>
                      </div>
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
          <div class="mb-3 flex flex-wrap items-center justify-between gap-3">
            <div class="text-sm font-semibold">流程步骤</div>
            <div class="flex items-center gap-4">
              <div class="text-xs text-muted-foreground">
                {{ logProgressCount }}/{{ currentSteps.length }}
              </div>
              <div class="flex items-center gap-2">
                <Switch :checked="logAutoRefresh" @update:checked="logAutoRefresh = $event" />
                <span class="text-xs text-muted-foreground">自动刷新</span>
              </div>
            </div>
          </div>

          <div class="flex items-start justify-between gap-2">
            <div
              v-for="(step, index) in currentSteps"
              :key="index"
              class="flex min-w-0 flex-1 flex-col items-center gap-2"
            >
              <span
                class="h-3 w-3 rounded-full"
                :class="step.state === 'success'
                  ? 'bg-emerald-500'
                  : (step.state === 'failed' ? 'bg-rose-500' : 'bg-muted-foreground/30')"
                :title="step.title"
              />
              <span
                class="line-clamp-2 text-[11px] leading-tight text-center"
                :class="step.state === 'success'
                  ? 'text-emerald-600'
                  : (step.state === 'failed' ? 'text-rose-600' : 'text-muted-foreground')"
              >
                {{ step.title }}
              </span>
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

        <!-- 账号摘要信息 -->
        <div v-if="currentAccountsSummary.length > 0" class="mb-4 space-y-2">
          <div class="text-sm font-semibold">账号摘要</div>
          <div
            v-for="item in currentAccountsSummary"
            :key="item.account_id"
            class="rounded-lg border border-border bg-muted/20 px-4 py-3"
          >
            <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
              <span class="font-medium text-foreground">{{ item.email }}</span>
              <span
                class="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium"
                :class="item.state === 'success' || item.state === 'completed'
                  ? 'bg-emerald-500/10 text-emerald-700'
                  : item.state === 'failed'
                    ? 'bg-rose-500/10 text-rose-700'
                    : item.state === 'running' || item.state === 'started'
                      ? 'bg-blue-500/10 text-blue-700'
                      : 'bg-muted text-muted-foreground'"
              >
                {{ item.state || '未知' }}
              </span>
            </div>
            <div v-if="item.celery_task_id" class="mt-1.5 flex flex-col gap-1 text-xs text-muted-foreground">
              <div class="flex items-center gap-1">
                <span class="shrink-0 font-medium">Celery ID:</span>
                <code class="break-all rounded bg-muted px-1 py-0.5 font-mono text-[11px]">{{ item.celery_task_id }}</code>
              </div>
              <div v-if="item.trace_file" class="flex items-center gap-1">
                <span class="shrink-0 font-medium">Trace:</span>
                <code class="break-all rounded bg-muted px-1 py-0.5 font-mono text-[11px]">{{ item.trace_file }}</code>
              </div>
            </div>
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
      <DialogContent class="sm:max-w-[1000px] max-h-[90vh] flex flex-col">
        <DialogHeader class="shrink-0">
          <DialogTitle>{{ celeryDialogTitle }}</DialogTitle>
          <DialogDescription>实时 trace（支持上滑加载历史）</DialogDescription>
        </DialogHeader>

        <div class="rounded-xl border border-border bg-muted/20 p-4">
          <!-- 账号摘要卡片 -->
          <div class="mb-4 space-y-2">
            <div class="flex items-center justify-between">
              <div class="text-sm font-semibold">账号摘要</div>
              <div class="flex items-center gap-2">
                <Switch :checked="traceAutoRefresh" @update:checked="traceAutoRefresh = $event" />
                <span class="text-xs text-muted-foreground">自动刷新</span>
              </div>
            </div>
            <div class="rounded-lg border border-border bg-muted/20 px-4 py-3">
              <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
                <span class="font-medium text-foreground">{{ celeryEmail || '-' }}</span>
                <span
                  class="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium"
                  :class="celeryState === 'SUCCESS'
                    ? 'bg-emerald-500/10 text-emerald-700'
                    : celeryState === 'FAILURE'
                      ? 'bg-rose-500/10 text-rose-700'
                      : celeryState === 'STARTED' || celeryState === 'PROGRESS'
                        ? 'bg-blue-500/10 text-blue-700'
                        : 'bg-muted text-muted-foreground'"
                >
                  {{ celeryState || '未知' }}
                </span>
              </div>
              <div v-if="celeryTaskId" class="mt-1.5 flex flex-col gap-1 text-xs text-muted-foreground">
                <div class="flex items-center gap-1">
                  <span class="shrink-0 font-medium">Celery ID:</span>
                  <code class="break-all rounded bg-muted px-1 py-0.5 font-mono text-[11px]">{{ celeryTaskId }}</code>
                </div>
                <div v-if="traceFile" class="flex items-center gap-1">
                  <span class="shrink-0 font-medium">Trace:</span>
                  <code class="break-all rounded bg-muted px-1 py-0.5 font-mono text-[11px]">{{ traceFile }}</code>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div
          ref="traceScrollRef"
          class="min-h-0 flex-1 overflow-auto rounded-xl border border-border bg-muted/20 p-4"
          @scroll="onTraceScroll"
        >
          <div class="font-mono text-xs leading-relaxed whitespace-pre-wrap break-words text-foreground">
            <div
              v-for="ln in traceLines"
              :key="ln.id"
              class="py-[1px]"
            >{{ ln.text }}</div>
          </div>
        </div>
      </DialogContent>
    </Dialog>

    <!-- 一键启动配置（主流程增项） -->
    <Dialog v-model:open="showOneClickDialog">
      <DialogContent class="sm:max-w-[560px]">
        <DialogHeader>
          <DialogTitle>一键启动</DialogTitle>
          <DialogDescription>主流程：登录 -> Google One -> 检查学生资格 -> 学生验证 -> 订阅 -> 完成</DialogDescription>
        </DialogHeader>

        <Alert class="mb-4">
          <AlertTitle>提示</AlertTitle>
          <AlertDescription>可选增项：安全设置（2FA/辅助邮箱）</AlertDescription>
        </Alert>

        <div class="grid gap-4 py-2">
          <div class="flex items-center justify-between">
            <div>
              <div class="text-sm font-medium">是否重跑</div>
              <div class="text-xs text-muted-foreground">开启后忽略已完成状态，全部重新执行</div>
            </div>
            <Switch v-model="oneClickForm.force_rerun" />
          </div>

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
            <div class="flex gap-2 mb-1">
              <Button
                size="sm" variant="outline"
                :class="{ 'bg-primary text-primary-foreground': oneClickForm.recovery_email_mode === 'manual' }"
                @click="oneClickForm.recovery_email_mode = 'manual'"
              >手动输入</Button>
              <Button
                size="sm" variant="outline"
                :class="{ 'bg-primary text-primary-foreground': oneClickForm.recovery_email_mode === 'auto' }"
                @click="oneClickForm.recovery_email_mode = 'auto'; loadCloudMailConfigs()"
              >自动创建域名邮箱</Button>
            </div>
            <Input
              v-if="oneClickForm.recovery_email_mode === 'manual'"
              v-model="oneClickForm.security_new_recovery_email"
              placeholder="可选，不填则不修改"
            />
            <Select
              v-if="oneClickForm.recovery_email_mode === 'auto'"
              v-model="oneClickForm.cloudmail_config_id"
            >
              <SelectTrigger class="w-full">
                <SelectValue placeholder="选择域名邮箱配置" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem
                  v-for="c in cloudMailConfigs"
                  :key="c.id"
                  :value="String(c.id)"
                >{{ c.name }} ({{ c.domains.join(', ') }})</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Alert>
            <AlertTitle>调度模型</AlertTitle>
            <AlertDescription>默认：并发 5，批内错峰 1 秒，批间随机休息 5-10 分钟</AlertDescription>
          </Alert>

          <div class="grid gap-2">
            <label class="text-sm font-medium">调度模型</label>
            <Select
              :model-value="oneClickForm.preset"
              @update:modelValue="(v) => onOneClickPresetChange(v)"
            >
              <SelectTrigger class="w-full">
                <SelectValue placeholder="选择模型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="recommended">推荐（稳定）</SelectItem>
                <SelectItem value="fast">快速（更高并发）</SelectItem>
                <SelectItem value="safe">稳健（更长休息）</SelectItem>
                <SelectItem value="custom">自定义</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div class="grid gap-2">
              <label class="text-sm font-medium">并发数量</label>
              <Input v-model.number="oneClickForm.max_concurrency" type="number" min="1" max="20" />
            </div>
            <div class="grid gap-2">
              <label class="text-sm font-medium">批内错峰(秒)</label>
              <Input v-model.number="oneClickForm.stagger_seconds" type="number" min="0" max="60" />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div class="grid gap-2">
              <label class="text-sm font-medium">每轮最短休息(分钟)</label>
              <Input v-model.number="oneClickForm.rest_min_minutes" type="number" min="0" max="180" />
            </div>
            <div class="grid gap-2">
              <label class="text-sm font-medium">每轮最长休息(分钟)</label>
              <Input v-model.number="oneClickForm.rest_max_minutes" type="number" min="0" max="180" />
            </div>
          </div>
        </div>

        <DialogFooter class="gap-2">
          <Button variant="outline" @click="showOneClickDialog = false">取消</Button>
          <Button @click="submitOneClickTask">开始执行</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- 安全一键更新配置（security/one_click_update） -->
    <Dialog v-model:open="showSecurityOneClickDialog">
      <DialogContent class="sm:max-w-[560px]">
        <DialogHeader>
          <DialogTitle>一键安全更新</DialogTitle>
          <DialogDescription>批次并发执行：同批账号错峰启动，批次间按区间随机休息</DialogDescription>
        </DialogHeader>

        <Alert class="mb-4">
          <AlertTitle>推荐模型</AlertTitle>
          <AlertDescription>并发 5，批内错峰 1 秒，批间随机休息 5-10 分钟</AlertDescription>
        </Alert>

        <div class="grid gap-4 py-2">
          <div class="grid gap-2">
            <label class="text-sm font-medium">调度模型</label>
            <Select
              :model-value="securityOneClickForm.preset"
              @update:modelValue="(v) => onSecurityOneClickPresetChange(v)"
            >
              <SelectTrigger class="w-full">
                <SelectValue placeholder="选择模型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="recommended">推荐（稳定）</SelectItem>
                <SelectItem value="fast">快速（更高并发）</SelectItem>
                <SelectItem value="safe">稳健（更长休息）</SelectItem>
                <SelectItem value="custom">自定义</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div class="grid gap-2">
              <label class="text-sm font-medium">并发数量</label>
              <Input v-model.number="securityOneClickForm.max_concurrency" type="number" min="1" max="20" />
            </div>
            <div class="grid gap-2">
              <label class="text-sm font-medium">批内错峰(秒)</label>
              <Input v-model.number="securityOneClickForm.stagger_seconds" type="number" min="0" max="60" />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div class="grid gap-2">
              <label class="text-sm font-medium">每轮最短休息(分钟)</label>
              <Input v-model.number="securityOneClickForm.rest_min_minutes" type="number" min="0" max="180" />
            </div>
            <div class="grid gap-2">
              <label class="text-sm font-medium">每轮最长休息(分钟)</label>
              <Input v-model.number="securityOneClickForm.rest_max_minutes" type="number" min="0" max="180" />
            </div>
          </div>
        </div>

        <DialogFooter class="gap-2">
          <Button variant="outline" @click="showSecurityOneClickDialog = false">取消</Button>
          <Button @click="submitSecurityOneClickUpdate">开始执行</Button>
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
          <DialogDescription>手动输入邮箱或自动创建域名邮箱</DialogDescription>
        </DialogHeader>

        <div class="grid gap-4 py-2">
          <!-- 模式切换 -->
          <div class="flex items-center gap-4">
            <label class="text-sm font-medium">模式</label>
            <div class="flex gap-2">
              <Button
                size="sm"
                :variant="recoveryEmailMode === 'manual' ? 'default' : 'outline'"
                @click="recoveryEmailMode = 'manual'"
              >手动输入</Button>
              <Button
                size="sm"
                :variant="recoveryEmailMode === 'auto' ? 'default' : 'outline'"
                @click="recoveryEmailMode = 'auto'"
              >自动创建域名邮箱</Button>
            </div>
          </div>

          <!-- 手动模式 -->
          <div v-if="recoveryEmailMode === 'manual'" class="grid gap-2">
            <label class="text-sm font-medium">新辅助邮箱</label>
            <Input v-model="newRecoveryEmail" placeholder="请输入新的辅助邮箱" />
          </div>

          <!-- 自动模式 -->
          <div v-else class="grid gap-2">
            <label class="text-sm font-medium">选择域名邮箱配置</label>
            <Select v-model="selectedCloudMailConfigId">
              <SelectTrigger>
                <SelectValue placeholder="请选择域名邮箱配置" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem
                  v-for="config in cloudMailConfigs"
                  :key="config.id"
                  :value="String(config.id)"
                >
                  {{ config.name }} ({{ config.domains?.join(', ') }})
                </SelectItem>
              </SelectContent>
            </Select>
            <p class="text-xs text-muted-foreground">将自动创建邮箱并换绑，验证码自动填入</p>
          </div>
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
  KeyRound,
  Eye,
  EyeOff,
  Copy,
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
  googleAccountsApi,
  googleGroupsApi,
  googleTasksApi,
  googleSecurityApi,
  googleSubscriptionApi,
  googleCeleryTasksApi,
} from '@/api/google'
import { getCloudMailConfigs } from '@/api/email'
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
const showDetailPassword = ref(false)
const selectedAccount = ref<GoogleAccount | null>(null)
const importText = ref('')
const filterType = ref('all')
const filterLoginResult = ref('all')
const filterGroup = ref('all')
const filterEmail = ref('')
const groupList = ref<Array<{ id: string; name: string; account_count: number }>>([])
const selectedAccounts = ref<GoogleAccount[]>([])
let filterEmailDebounceTimer: number | null = null

const totalPages = computed(() => {
  const t = Number(total.value) || 0
  const ps = Number(pageSize.value) || 1
  return Math.max(1, Math.ceil(t / ps))
})

const selectedIds = computed(() => new Set(selectedAccounts.value.map(a => a.id)))

// 账号运行态（用于列表“运行中”指示）
const runningAccountCounts = reactive(new Map<number, number>())

const isAccountRunning = (accountId: number) => {
  return (runningAccountCounts.get(accountId) || 0) > 0
}

const incRunningAccounts = (ids: number[]) => {
  for (const id of ids) {
    const cur = runningAccountCounts.get(id) || 0
    runningAccountCounts.set(id, cur + 1)
  }
}

const decRunningAccounts = (ids: number[]) => {
  for (const id of ids) {
    const cur = runningAccountCounts.get(id) || 0
    if (cur <= 1) runningAccountCounts.delete(id)
    else runningAccountCounts.set(id, cur - 1)
  }
}

const taskStatusPollingTimers = new Map<number, number>()
const taskAccountIdsByTaskId = new Map<number, number[]>()
const celeryTaskStatusPollingTimers = new Map<string, number>()
const celeryTaskAccountIdsByTaskId = new Map<string, number[]>()
let taskStatusPollingInFlight = false
let celeryTaskStatusPollingInFlight = false
let lastAccountsAutoRefreshAt = 0
const ACCOUNTS_AUTO_REFRESH_MS = 5000

const stopTaskStatusPolling = (taskId: number) => {
  const timer = taskStatusPollingTimers.get(taskId)
  if (timer) window.clearInterval(timer)
  taskStatusPollingTimers.delete(taskId)

  const ids = taskAccountIdsByTaskId.get(taskId) || []
  taskAccountIdsByTaskId.delete(taskId)
  if (ids.length > 0) decRunningAccounts(ids)
}

const stopAllTaskStatusPolling = () => {
  for (const [taskId] of taskStatusPollingTimers) {
    stopTaskStatusPolling(taskId)
  }
  runningAccountCounts.clear()
}

const stopCeleryTaskStatusPolling = (taskId: string) => {
  const timer = celeryTaskStatusPollingTimers.get(taskId)
  if (timer) window.clearInterval(timer)
  celeryTaskStatusPollingTimers.delete(taskId)

  const ids = celeryTaskAccountIdsByTaskId.get(taskId) || []
  celeryTaskAccountIdsByTaskId.delete(taskId)
  if (ids.length > 0) decRunningAccounts(ids)
}

const stopAllCeleryTaskStatusPolling = () => {
  for (const [taskId] of celeryTaskStatusPollingTimers) {
    stopCeleryTaskStatusPolling(taskId)
  }
}

const startTaskStatusPolling = (taskId: number, accountIds: number[]) => {
  if (!taskId || taskId <= 0) return
  if (taskStatusPollingTimers.has(taskId)) return

  taskAccountIdsByTaskId.set(taskId, accountIds)
  if (accountIds.length > 0) incRunningAccounts(accountIds)

  const timer = window.setInterval(async () => {
    if (taskStatusPollingInFlight) return
    taskStatusPollingInFlight = true
    try {
      const res: any = await googleTasksApi.getTask(taskId)
      const status = String(res?.status ?? res?.data?.status ?? '').toLowerCase()
      const ids = taskAccountIdsByTaskId.get(taskId) || accountIds

      const isTerminal = ['completed', 'failed', 'cancelled'].includes(status)
      const now = Date.now()

      // 运行中也定期刷新列表，避免用户需要手动刷新
      if (isTerminal || now - lastAccountsAutoRefreshAt >= ACCOUNTS_AUTO_REFRESH_MS) {
        lastAccountsAutoRefreshAt = now
        await fetchAccounts()
        if (showTasksDrawer.value && selectedAccount.value && ids.includes(selectedAccount.value.id)) {
          await viewTasks(selectedAccount.value)
        }
      }

      if (!isTerminal) return

      stopTaskStatusPolling(taskId)
    } catch {
      // ignore
    } finally {
      taskStatusPollingInFlight = false
    }
  }, 2000)

  taskStatusPollingTimers.set(taskId, timer)
}

const getCreatedTaskId = (res: any) => {
  const raw = res?.task_id ?? res?.data?.task_id ?? res?.id ?? res?.data?.id
  const n = Number(raw)
  return Number.isFinite(n) && n > 0 ? n : null
}

const getCreatedCeleryTaskId = (res: any) => {
  const raw = res?.task_id ?? res?.data?.task_id
  const s = String(raw ?? '').trim()
  return s ? s : null
}

const startCeleryTaskStatusPolling = (taskId: string, accountIds: number[]) => {
  const normalizedTaskId = String(taskId || '').trim()
  if (!normalizedTaskId) return
  if (celeryTaskStatusPollingTimers.has(normalizedTaskId)) return

  celeryTaskAccountIdsByTaskId.set(normalizedTaskId, accountIds)
  if (accountIds.length > 0) incRunningAccounts(accountIds)

  const timer = window.setInterval(async () => {
    if (celeryTaskStatusPollingInFlight) return
    celeryTaskStatusPollingInFlight = true
    try {
      const res: any = await googleCeleryTasksApi.getTask(normalizedTaskId)
      const stateRaw = String(res?.state || '').trim()
      const state = stateRaw.toUpperCase()
      const ids = celeryTaskAccountIdsByTaskId.get(normalizedTaskId) || accountIds

      const isTerminal = ['SUCCESS', 'FAILURE', 'REVOKED', 'COMPLETED', 'FAILED', 'CANCELLED'].includes(state)
      const now = Date.now()

      if (isTerminal || now - lastAccountsAutoRefreshAt >= ACCOUNTS_AUTO_REFRESH_MS) {
        lastAccountsAutoRefreshAt = now
        await fetchAccounts()
        if (showTasksDrawer.value && selectedAccount.value && ids.includes(selectedAccount.value.id)) {
          await viewTasks(selectedAccount.value)
        }
      }

      if (!isTerminal) return
      stopCeleryTaskStatusPolling(normalizedTaskId)
    } catch {
      // ignore
    } finally {
      celeryTaskStatusPollingInFlight = false
    }
  }, 2000)

  celeryTaskStatusPollingTimers.set(normalizedTaskId, timer)
}

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
const showSecurityOneClickDialog = ref(false)
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
  editForm.secret_key = account.two_fa || ''
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
      const serverMsg = e?.response?.data?.detail || e?.response?.data?.error
      ElMessage.error('删除失败: ' + (serverMsg || e.message || '未知错误'))
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
const currentLogTaskId = ref<number | null>(null)
const currentLogAccountId = ref<number | null>(null)
const currentLogEmail = ref('')
const currentAccountsSummary = ref<Array<{
  account_id: number
  email: string
  celery_task_id: string
  trace_file: string
  state: string
}>>([])
const logAutoRefresh = ref(true)
const logPollingTimer = ref<number | null>(null)
let logPollingInFlight = false

const logProgressCount = computed(() => {
  const steps = currentSteps.value || []
  let last = -1
  for (let i = 0; i < steps.length; i++) {
    const st = String(steps[i]?.state || 'pending')
    if (st !== 'pending') last = i
  }
  return last >= 0 ? last + 1 : 0
})

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
const traceAutoRefresh = ref(true)
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

const stopLogPolling = () => {
  if (logPollingTimer.value) {
    window.clearInterval(logPollingTimer.value)
    logPollingTimer.value = null
  }
  logPollingInFlight = false
}

const startLogPolling = () => {
  stopLogPolling()
  logPollingTimer.value = window.setInterval(async () => {
    if (!showLogDialog.value) return
    if (!logAutoRefresh.value) return
    if (logPollingInFlight) return
    const taskId = currentLogTaskId.value
    if (!taskId) return
    logPollingInFlight = true
    try {
      await fetchTaskLog(
        taskId,
        {
          account_id: currentLogAccountId.value || undefined,
          email: currentLogEmail.value || undefined,
        },
        { silent: true }
      )
    } finally {
      logPollingInFlight = false
    }
  }, 1500)
}

const startTracePolling = () => {
  stopTracePolling()
  tracePollingTimer.value = window.setInterval(async () => {
    if (!showCeleryDialog.value) return
    if (!traceAutoRefresh.value) return
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
  if (v && traceAutoRefresh.value) startTracePolling()
  else stopTracePolling()
})

watch(traceAutoRefresh, (v) => {
  if (!showCeleryDialog.value) return
  if (v && traceFollowLatest.value) startTracePolling()
  else stopTracePolling()
})

watch(showCeleryDialog, (v) => {
  if (v) {
    if (traceFollowLatest.value && traceAutoRefresh.value) startTracePolling()
  } else {
    stopTracePolling()
  }
})

watch(logAutoRefresh, (v) => {
  if (!showLogDialog.value) return
  if (v) startLogPolling()
  else stopLogPolling()
})

watch(showLogDialog, (v) => {
  if (v) {
    if (logAutoRefresh.value) startLogPolling()
  } else {
    stopLogPolling()
    currentLogTaskId.value = null
    currentLogAccountId.value = null
    currentLogEmail.value = ''
    currentAccountsSummary.value = []
  }
})

onBeforeUnmount(() => {
  if (filterEmailDebounceTimer !== null) {
    window.clearTimeout(filterEmailDebounceTimer)
    filterEmailDebounceTimer = null
  }
  stopTracePolling()
  stopLogPolling()
  stopAllTaskStatusPolling()
  stopAllCeleryTaskStatusPolling()
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

type OneClickPreset = 'recommended' | 'fast' | 'safe' | 'custom'

const oneClickPresetValues: Record<Exclude<OneClickPreset, 'custom'>, {
  max_concurrency: number
  stagger_seconds: number
  rest_min_minutes: number
  rest_max_minutes: number
}> = {
  recommended: {
    max_concurrency: 5,
    stagger_seconds: 1,
    rest_min_minutes: 5,
    rest_max_minutes: 10,
  },
  fast: {
    max_concurrency: 8,
    stagger_seconds: 1,
    rest_min_minutes: 2,
    rest_max_minutes: 5,
  },
  safe: {
    max_concurrency: 3,
    stagger_seconds: 2,
    rest_min_minutes: 8,
    rest_max_minutes: 15,
  },
}

const oneClickForm = reactive<{
  force_rerun: boolean
  security_change_2fa: boolean
  security_new_recovery_email: string
  recovery_email_mode: 'manual' | 'auto'
  cloudmail_config_id: number | null
  preset: OneClickPreset
  max_concurrency: number
  stagger_seconds: number
  rest_min_minutes: number
  rest_max_minutes: number
}>({
  force_rerun: false,
  security_change_2fa: false,
  security_new_recovery_email: '',
  recovery_email_mode: 'manual',
  cloudmail_config_id: null,
  preset: 'recommended',
  max_concurrency: 5,
  stagger_seconds: 1,
  rest_min_minutes: 5,
  rest_max_minutes: 10,
})

const applyOneClickPreset = (preset: Exclude<OneClickPreset, 'custom'>) => {
  const picked = oneClickPresetValues[preset]
  oneClickForm.max_concurrency = picked.max_concurrency
  oneClickForm.stagger_seconds = picked.stagger_seconds
  oneClickForm.rest_min_minutes = picked.rest_min_minutes
  oneClickForm.rest_max_minutes = picked.rest_max_minutes
}

const onOneClickPresetChange = (v: unknown) => {
  const value = String(v ?? '').trim().toLowerCase()
  const preset: OneClickPreset =
    value === 'fast' || value === 'safe' || value === 'custom' ? (value as OneClickPreset) : 'recommended'
  oneClickForm.preset = preset
  if (preset !== 'custom') {
    applyOneClickPreset(preset)
  }
}

const normalizeOneClickConfig = () => {
  const toNum = (value: unknown, fallback: number) => {
    const n = Number(value)
    return Number.isFinite(n) ? n : fallback
  }
  const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, Math.trunc(value)))

  const max_concurrency = clamp(toNum(oneClickForm.max_concurrency, 5), 1, 20)
  const stagger_seconds = clamp(toNum(oneClickForm.stagger_seconds, 1), 0, 60)
  const rest_min_minutes = clamp(toNum(oneClickForm.rest_min_minutes, 5), 0, 180)
  const rest_max_input = clamp(toNum(oneClickForm.rest_max_minutes, 10), 0, 180)
  const rest_max_minutes = Math.max(rest_min_minutes, rest_max_input)

  oneClickForm.max_concurrency = max_concurrency
  oneClickForm.stagger_seconds = stagger_seconds
  oneClickForm.rest_min_minutes = rest_min_minutes
  oneClickForm.rest_max_minutes = rest_max_minutes

  return {
    max_concurrency,
    stagger_seconds,
    rest_min_minutes,
    rest_max_minutes,
  }
}

type SecurityOneClickPreset = 'recommended' | 'fast' | 'safe' | 'custom'

const securityPresetValues: Record<Exclude<SecurityOneClickPreset, 'custom'>, {
  max_concurrency: number
  stagger_seconds: number
  rest_min_minutes: number
  rest_max_minutes: number
}> = {
  recommended: {
    max_concurrency: 5,
    stagger_seconds: 1,
    rest_min_minutes: 5,
    rest_max_minutes: 10,
  },
  fast: {
    max_concurrency: 8,
    stagger_seconds: 1,
    rest_min_minutes: 2,
    rest_max_minutes: 5,
  },
  safe: {
    max_concurrency: 3,
    stagger_seconds: 2,
    rest_min_minutes: 8,
    rest_max_minutes: 15,
  },
}

const securityOneClickForm = reactive<{
  preset: SecurityOneClickPreset
  max_concurrency: number
  stagger_seconds: number
  rest_min_minutes: number
  rest_max_minutes: number
}>({
  preset: 'recommended',
  max_concurrency: 5,
  stagger_seconds: 1,
  rest_min_minutes: 5,
  rest_max_minutes: 10,
})

const applySecurityPreset = (preset: Exclude<SecurityOneClickPreset, 'custom'>) => {
  const picked = securityPresetValues[preset]
  securityOneClickForm.max_concurrency = picked.max_concurrency
  securityOneClickForm.stagger_seconds = picked.stagger_seconds
  securityOneClickForm.rest_min_minutes = picked.rest_min_minutes
  securityOneClickForm.rest_max_minutes = picked.rest_max_minutes
}

const onSecurityOneClickPresetChange = (v: unknown) => {
  const value = String(v ?? '').trim().toLowerCase()
  const preset: SecurityOneClickPreset =
    value === 'fast' || value === 'safe' || value === 'custom' ? (value as SecurityOneClickPreset) : 'recommended'
  securityOneClickForm.preset = preset
  if (preset !== 'custom') {
    applySecurityPreset(preset)
  }
}

const normalizeSecurityOneClickConfig = () => {
  const toNum = (value: unknown, fallback: number) => {
    const n = Number(value)
    return Number.isFinite(n) ? n : fallback
  }
  const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, Math.trunc(value)))

  const max_concurrency = clamp(toNum(securityOneClickForm.max_concurrency, 5), 1, 20)
  const stagger_seconds = clamp(toNum(securityOneClickForm.stagger_seconds, 1), 0, 60)
  const rest_min_minutes = clamp(toNum(securityOneClickForm.rest_min_minutes, 5), 0, 180)
  const rest_max_input = clamp(toNum(securityOneClickForm.rest_max_minutes, 10), 0, 180)
  const rest_max_minutes = Math.max(rest_min_minutes, rest_max_input)

  securityOneClickForm.max_concurrency = max_concurrency
  securityOneClickForm.stagger_seconds = stagger_seconds
  securityOneClickForm.rest_min_minutes = rest_min_minutes
  securityOneClickForm.rest_max_minutes = rest_max_minutes

  return {
    max_concurrency,
    stagger_seconds,
    rest_min_minutes,
    rest_max_minutes,
  }
}

const newRecoveryEmail = ref('')
const recoveryEmailMode = ref<'manual' | 'auto'>('manual')
const selectedCloudMailConfigId = ref<string>('')
const cloudMailConfigs = ref<any[]>([])
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
  if (filterType.value !== 'logged_in') {
    filterLoginResult.value = 'all'
  }
  currentPage.value = 1
  selectedAccounts.value = []
  await fetchAccounts()
}

const onFilterLoginResultChange = async (v: unknown) => {
  filterLoginResult.value = normalizeSelectValue(v, 'all')
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

const onFilterEmailChange = (v: unknown) => {
  filterEmail.value = String(v ?? '').trim()
  currentPage.value = 1
  selectedAccounts.value = []

  if (filterEmailDebounceTimer !== null) {
    window.clearTimeout(filterEmailDebounceTimer)
  }
  filterEmailDebounceTimer = window.setTimeout(() => {
    fetchAccounts()
  }, 300)
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
    if (filterType.value === 'logged_in' && filterLoginResult.value !== 'all') {
      params.login_result = filterLoginResult.value
    }
    if (filterGroup.value && filterGroup.value !== 'all') {
      if (filterGroup.value === 'ungrouped') {
        params.group_name = '' // 未分组（空字符串）
      } else {
        params.group_name = filterGroup.value
      }
    }
    if (filterEmail.value) {
      params.email = filterEmail.value
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
    // 使用后端分组接口（按 created_at 倒序），保证分组下拉按时间顺序展示。
    // 后端返回: [{ id, name, description, account_count, created_at }]
    const response = await googleGroupsApi.getGroups()
    const raw = Array.isArray(response)
      ? response
      : (response as any)?.data || (response as any)?.results || []

    const items = (Array.isArray(raw) ? raw : [])
      .map((g: any) => ({
        name: String(g?.name || '').trim(),
        account_count: Number(g?.account_count || 0),
        created_at: String(g?.created_at || ''),
      }))
      .filter((g) => Boolean(g.name))
      .sort((a, b) => {
        const ta = Date.parse(a.created_at) || 0
        const tb = Date.parse(b.created_at) || 0
        return tb - ta
      })

    groupList.value = items.map((g) => ({
      // 分组筛选参数使用 group_name 字符串字段，这里 value 继续用 name
      id: g.name,
      name: g.name,
      account_count: g.account_count,
    }))

    const existingNames = new Set(items.map((g) => g.name))
    if (
      filterGroup.value !== 'all' &&
      filterGroup.value !== 'ungrouped' &&
      !existingNames.has(filterGroup.value)
    ) {
      filterGroup.value = 'all'
    }
  } catch (error) {
    console.error('获取分组列表失败:', error)

    // 兜底：如果分组接口异常（500/未迁移等），降级为从账号列表提取 group_name。
    // 仍按时间顺序：用该分组账号中最早的 created_at 作为近似分组时间。
    try {
      const response = await googleAccountsApi.getAccounts({ page_size: 9999 })
      const allAccounts = Array.isArray(response) ? response : ((response as any).results || [])

      const groupCounts = new Map<string, number>()
      const groupFirstSeenAt = new Map<string, number>()

      for (const acc of allAccounts) {
        const name = String((acc as any)?.group_name || '').trim()
        if (!name) continue
        groupCounts.set(name, (groupCounts.get(name) || 0) + 1)

        const createdAtRaw = String((acc as any)?.created_at || '')
        const ts = Date.parse(createdAtRaw) || 0
        const prev = groupFirstSeenAt.get(name)
        if (prev === undefined || (ts > 0 && ts < prev)) {
          groupFirstSeenAt.set(name, ts)
        }
      }

      const items = Array.from(groupCounts.keys())
        .map((name) => ({
          name,
          account_count: groupCounts.get(name) || 0,
          first_seen_at: groupFirstSeenAt.get(name) || 0,
        }))
        .sort((a, b) => b.first_seen_at - a.first_seen_at)

      groupList.value = items.map((g) => ({
        id: g.name,
        name: g.name,
        account_count: g.account_count,
      }))

      const existingNames = new Set(items.map((g) => g.name))
      if (
        filterGroup.value !== 'all' &&
        filterGroup.value !== 'ungrouped' &&
        !existingNames.has(filterGroup.value)
      ) {
        filterGroup.value = 'all'
      }
    } catch (fallbackError) {
      console.error('分组兜底也失败:', fallbackError)
      groupList.value = []
    }
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

  const ids = getSelectedIds()

  const config: any = {}
  const scheduleConfig = normalizeOneClickConfig()
  if (oneClickForm.force_rerun) {
    config.force_rerun = true
  } else {
    config.resume = true
  }
  if (oneClickForm.security_change_2fa) {
    config.security_change_2fa = true
  }
  if (oneClickForm.recovery_email_mode === 'auto' && oneClickForm.cloudmail_config_id) {
    config.cloudmail_config_id = oneClickForm.cloudmail_config_id
  } else if (oneClickForm.security_new_recovery_email && oneClickForm.security_new_recovery_email.trim()) {
    config.security_new_recovery_email = oneClickForm.security_new_recovery_email.trim()
  }
  config.max_concurrency = scheduleConfig.max_concurrency
  config.stagger_seconds = scheduleConfig.stagger_seconds
  config.rest_min_minutes = scheduleConfig.rest_min_minutes
  config.rest_max_minutes = scheduleConfig.rest_max_minutes

  console.log('[一键启动] force_rerun switch:', oneClickForm.force_rerun, '| config:', JSON.stringify(config))

  try {
    const res = await googleTasksApi.createTask({
      task_type: 'one_click',
      account_ids: ids,
      config
    })

    const createdTaskId = getCreatedTaskId(res)
    if (createdTaskId) startTaskStatusPolling(createdTaskId, ids)
    ElMessage.success('任务已创建')
    showOneClickDialog.value = false
    fetchAccounts()
  } catch (e: any) {
    ElMessage.error('创建任务失败: ' + (e.message || '未知错误'))
  }
}

const submitSecurityOneClickUpdate = async () => {
  if (selectedAccounts.value.length === 0) {
    ElMessage.warning('请先选择账号')
    return
  }

  const ids = getSelectedIds()
  const config = normalizeSecurityOneClickConfig()

  try {
    const res = await googleSecurityApi.oneClickUpdate({
      account_ids: ids,
      max_concurrency: config.max_concurrency,
      stagger_seconds: config.stagger_seconds,
      rest_min_minutes: config.rest_min_minutes,
      rest_max_minutes: config.rest_max_minutes,
    })
    const celeryTaskId = getCreatedCeleryTaskId(res)
    if (celeryTaskId) startCeleryTaskStatusPolling(celeryTaskId, ids)
    ElMessage.success('任务已提交')
    showSecurityOneClickDialog.value = false
    fetchAccounts()
  } catch (e: any) {
    ElMessage.error('操作失败: ' + (e.message || '未知错误'))
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
      const res = await googleSecurityApi.change2fa({ account_ids: ids })
      const celeryTaskId = getCreatedCeleryTaskId(res)
      if (celeryTaskId) startCeleryTaskStatusPolling(celeryTaskId, ids)
      ElMessage.success('任务已提交')
      fetchAccounts()
    } else if (command === 'change_recovery') {
      newRecoveryEmail.value = ''
      showRecoveryEmailDialog.value = true
    } else if (command === 'get_backup_codes') {
      await ElMessageBox.confirm('确定获取备份验证码吗？', '获取备份码')
      const res = await googleSecurityApi.getBackupCodes({ account_ids: ids })
      const celeryTaskId = getCreatedCeleryTaskId(res)
      if (celeryTaskId) startCeleryTaskStatusPolling(celeryTaskId, ids)
      ElMessage.success('任务已提交')
      fetchAccounts()
    } else if (command === 'one_click_update') {
      showSecurityOneClickDialog.value = true
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
      const serverMsg = e?.response?.data?.error
      const detail = e?.response?.data?.failed
      const detailText = Array.isArray(detail)
        ? detail.map((x: any) => `${x?.email || ''} ${x?.detail || ''}`.trim()).filter(Boolean).join(' | ')
        : ''
      ElMessage.error(
        '批量删除失败: ' + (serverMsg || e.message || '未知错误') + (detailText ? ` (${detailText})` : '')
      )
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
    const ids = getSelectedIds()
    const res = await googleTasksApi.createTask({
      task_type: 'verify',
      account_ids: ids,
      config: {
        student_name: sheerIDForm.student_name,
        student_email: sheerIDForm.student_email,
        school_name: sheerIDForm.school_name
      }
    })

    const createdTaskId = getCreatedTaskId(res)
    if (createdTaskId) startTaskStatusPolling(createdTaskId, ids)
    ElMessage.success('SheerID 验证任务已创建')
    showSheerIDDialog.value = false
    fetchAccounts()
  } catch (e: any) {
    ElMessage.error('创建失败: ' + e.message)
  }
}

const submitBindCardTask = async () => {
  try {
    const ids = getSelectedIds()
    const res = await googleTasksApi.createTask({
      task_type: 'bind_card',
      account_ids: ids,
      config: { 
        card_pool: bindCardForm.card_pool,
        card_strategy: bindCardForm.card_strategy
      }
    })

    const createdTaskId = getCreatedTaskId(res)
    if (createdTaskId) startTaskStatusPolling(createdTaskId, ids)
    ElMessage.success('绑卡任务已创建')
    showBindCardDialog.value = false
    fetchAccounts()
  } catch (e: any) {
    ElMessage.error('创建失败: ' + e.message)
  }
}

const loadCloudMailConfigs = async () => {
  try {
    const res = await getCloudMailConfigs()
    cloudMailConfigs.value = (res.data?.results || res.data || []).filter((c: any) => c.is_active)
  } catch {
    cloudMailConfigs.value = []
  }
}

const submitChangeRecoveryEmail = async () => {
  const ids = getSelectedIds()

  if (recoveryEmailMode.value === 'auto') {
    if (!selectedCloudMailConfigId.value) {
      ElMessage.warning('请选择域名邮箱配置')
      return
    }
    try {
      const res = await googleSecurityApi.autoChangeRecoveryEmail({
        account_ids: ids,
        cloudmail_config_id: selectedCloudMailConfigId.value
      })
      const celeryTaskId = getCreatedCeleryTaskId(res)
      if (celeryTaskId) startCeleryTaskStatusPolling(celeryTaskId, ids)
      ElMessage.success('自动换绑任务已提交')
      showRecoveryEmailDialog.value = false
      fetchAccounts()
    } catch (e: any) {
      ElMessage.error('操作失败: ' + e.message)
    }
  } else {
    if (!newRecoveryEmail.value) {
      ElMessage.warning('请输入邮箱')
      return
    }
    try {
      const res = await googleSecurityApi.changeRecoveryEmail({
        account_ids: ids,
        new_email: newRecoveryEmail.value
      })
      const celeryTaskId = getCreatedCeleryTaskId(res)
      if (celeryTaskId) startCeleryTaskStatusPolling(celeryTaskId, ids)
      ElMessage.success('任务已提交')
      showRecoveryEmailDialog.value = false
      fetchAccounts()
    } catch (e: any) {
      ElMessage.error('操作失败: ' + e.message)
    }
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

const fetchTaskLog = async (
  taskId: number,
  params?: { account_id?: number; email?: string },
  options?: { silent?: boolean }
) => {
  try {
    const res = await googleTasksApi.getTaskLog(taskId, params)
    // 后端返回：{ task_id, accounts_summary, log }
    const logStr = typeof res?.log === 'string' ? res.log : JSON.stringify(res, null, 2)
    currentLogContent.value = logStr
    currentAccountsSummary.value = Array.isArray(res?.accounts_summary) ? res.accounts_summary : []

    // Parse steps
    currentLogExtras.value = []

    // Define standard steps
    const standardSteps = [
      '登录账号', '打开 Google One', '检查学生资格', '学生验证', '订阅服务', '完成处理'
    ]

    const steps = standardSteps.map(title => ({
      title,
      state: 'pending' as FlowStepState,
      fromCompleted: false,
    }))

    // Step markers
    const stepRegex = /步骤 (\d+)\/6:\s*(.*)/g
    let match
    while ((match = stepRegex.exec(logStr)) !== null) {
      const stepNum = parseInt(match[1])
      const idx = stepNum - 1
      if (!Number.isFinite(stepNum) || idx < 0 || idx >= steps.length) continue

      const text = String(match[2] || '')
      const isCompleted = text.includes('已完成')
      const isSkip = text.includes('跳过')

      // 跳过：一律视为未执行（灰），避免出现“前面失败后面却显示完成”的错觉
      if (isSkip) {
        steps[idx].state = 'pending'
        continue
      }

      if (isCompleted) {
        steps[idx].state = 'success'
        steps[idx].fromCompleted = true
        continue
      }

      steps[idx].state = 'success'
    }

    // Failure detection (map error keywords to step)
    let failedIndex = -1
    if (
      logStr.includes('检测到机器人验证') ||
      logStr.includes('需要机器人验证') ||
      logStr.includes('机器人验证') ||
      logStr.includes('验证码')
    ) {
      failedIndex = 0
    } else if (
      logStr.includes('账号不符合学生优惠资格') ||
      logStr.includes('学生资格不符合')
    ) {
      failedIndex = 2
    } else if (logStr.includes('学生验证失败')) {
      failedIndex = 3
    } else if (
      logStr.includes('订阅失败') ||
      logStr.includes('绑卡失败') ||
      logStr.includes('绑卡过程出错')
    ) {
      failedIndex = 4
    }

    if (failedIndex >= 0 && failedIndex < steps.length) {
      steps[failedIndex].state = 'failed'
      for (let i = failedIndex + 1; i < steps.length; i++) {
        if (steps[i].fromCompleted) continue
        steps[i].state = 'pending'
      }
    }

    currentSteps.value = steps.map(({ fromCompleted, ...rest }) => rest)

    // Check extras
    const extraRegex = /增项:\s*(.*)/g
    while ((match = extraRegex.exec(logStr)) !== null) {
      if (!currentLogExtras.value.includes(match[1])) {
        currentLogExtras.value.push(match[1])
      }
    }

    showLogDialog.value = true
  } catch (e) {
    if (!options?.silent) {
      ElMessage.error('获取日志失败')
    }
  }
}

const viewTaskLog = async (taskId: number, account?: GoogleAccount | null) => {
  currentLogTaskId.value = taskId
  currentLogAccountId.value = account?.id ?? null
  currentLogEmail.value = String(account?.email || '')
  await fetchTaskLog(
    taskId,
    {
      account_id: account?.id,
      email: account?.email,
    }
  )
}

const cancelTask = async (taskId: number) => {
  try {
    await googleTasksApi.cancelTask(taskId)
    ElMessage.success('任务已中断')
    if (selectedAccount.value) {
      await viewTasks(selectedAccount.value)
    }
  } catch (e: any) {
    ElMessage.error('中断任务失败: ' + (e.message || '未知错误'))
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
  // 去除每行中与摘要卡片重复的 [kind][celery=xxx][email] step/action: 前缀
  // 原始格式: [2026-02-13T11:05:19.137959+00:00] [gpt][celery=xxx][email] step/action: message
  // 清理后:   [11:05:19] message
  const prefixRe = /^(\[[^\]]*\])\s*\[[^\]]*\]\[celery=[^\]]*\]\[[^\]]*\]\s*\S+\/\S+:\s*/
  // 简化时间戳: [2026-02-13T11:05:19.137959+00:00] → [2026-02-13 11:05:19]
  const tsRe = /^\[(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})\.\d+[^\]]*\]/
  for (const t of raw || []) {
    const text = String(t ?? '')
    if (!text) continue
    // 过滤 JSON 行（与人类可读行内容重复）
    if (text.trim().startsWith('{')) continue
    const cleaned = text.replace(prefixRe, '$1 ').replace(tsRe, '[$1 $2]')
    out.push({
      id: ++traceLineSeq,
      text: cleaned,
      isJson: false
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
  showDetailPassword.value = false
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

type FlowStepState = 'success' | 'failed' | 'pending'

const getMainFlowProgress = (account?: GoogleAccount | null) => {
  if (!account) {
    return MAIN_FLOW_STEPS.map(label => ({ label, state: 'pending' as FlowStepState }))
  }

  const status = String(account.status || '').toLowerCase()
  const googleOneStatus = String(account.google_one_status || '').toLowerCase()
  const geminiStatus = String(account.gemini_status || '').toLowerCase()
  const notes = String(account.notes || '')

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

  const loginFailed =
    status === 'locked' ||
    status === 'disabled' ||
    notes.includes('机器人验证') ||
    notes.includes('验证码') ||
    notes.includes('登录失败')

  const eligibilityFailed =
    status === 'ineligible' ||
    googleOneStatus === 'ineligible' ||
    googleOneStatus === 'timeout' ||
    googleOneStatus === 'error' ||
    notes.includes('获取链接失败') ||
    notes.includes('账号不符合学生优惠资格') ||
    notes.includes('学生资格不符合')

  const eligibilitySuccess =
    !eligibilityFailed &&
    (
      googleOneStatus === 'link_ready' ||
      googleOneStatus === 'verified' ||
      googleOneStatus === 'subscribed' ||
      Boolean(account.sheerid_link) ||
      hasVerify
    )

  const verifyFailed = notes.includes('学生验证失败')

  const hasSubscribe =
    Boolean(account.card_bound) ||
    Boolean(account.subscribed) ||
    googleOneStatus === 'subscribed' ||
    ['active', 'subscribed'].includes(geminiStatus)

  const subscribeFailed =
    notes.includes('订阅失败') ||
    notes.includes('绑卡失败') ||
    notes.includes('绑卡过程出错')

  const hasComplete = hasSubscribe

  const loginState: FlowStepState = loginFailed ? 'failed' : (hasLogin ? 'success' : 'pending')

  if (loginState !== 'success') {
    return [
      { label: MAIN_FLOW_STEPS[0], state: loginState },
      { label: MAIN_FLOW_STEPS[1], state: 'pending' },
      { label: MAIN_FLOW_STEPS[2], state: 'pending' },
      { label: MAIN_FLOW_STEPS[3], state: 'pending' },
      { label: MAIN_FLOW_STEPS[4], state: 'pending' },
      { label: MAIN_FLOW_STEPS[5], state: 'pending' },
    ]
  }

  const step3State: FlowStepState = eligibilityFailed ? 'failed' : (eligibilitySuccess ? 'success' : 'pending')
  const step2State: FlowStepState = (step3State !== 'pending' || hasOpenOne) ? 'success' : 'pending'

  if (step3State === 'failed') {
    return [
      { label: MAIN_FLOW_STEPS[0], state: 'success' },
      { label: MAIN_FLOW_STEPS[1], state: step2State },
      { label: MAIN_FLOW_STEPS[2], state: 'failed' },
      { label: MAIN_FLOW_STEPS[3], state: 'pending' },
      { label: MAIN_FLOW_STEPS[4], state: 'pending' },
      { label: MAIN_FLOW_STEPS[5], state: 'pending' },
    ]
  }

  const verifySuccess = hasVerify || googleOneStatus === 'verified' || googleOneStatus === 'subscribed' || hasSubscribe
  const step4State: FlowStepState = verifyFailed ? 'failed' : (verifySuccess ? 'success' : 'pending')

  if (step4State === 'failed') {
    return [
      { label: MAIN_FLOW_STEPS[0], state: 'success' },
      { label: MAIN_FLOW_STEPS[1], state: step2State },
      { label: MAIN_FLOW_STEPS[2], state: step3State },
      { label: MAIN_FLOW_STEPS[3], state: 'failed' },
      { label: MAIN_FLOW_STEPS[4], state: 'pending' },
      { label: MAIN_FLOW_STEPS[5], state: 'pending' },
    ]
  }

  const step5State: FlowStepState = subscribeFailed ? 'failed' : (hasSubscribe ? 'success' : 'pending')

  return [
    { label: MAIN_FLOW_STEPS[0], state: 'success' },
    { label: MAIN_FLOW_STEPS[1], state: step2State },
    { label: MAIN_FLOW_STEPS[2], state: step3State },
    { label: MAIN_FLOW_STEPS[3], state: step4State },
    { label: MAIN_FLOW_STEPS[4], state: step5State },
    { label: MAIN_FLOW_STEPS[5], state: hasComplete ? 'success' : 'pending' },
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

// 通用复制函数
const copyToClipboard = async (text: string, label: string = '内容') => {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success(`${label}已复制`)
  } catch {
    ElMessage.error('复制失败')
  }
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
