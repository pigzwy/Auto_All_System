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
            <div class="text-2xl font-bold text-blue-700 dark:text-blue-300">{{ stats.motherCount }}</div>
            <div class="text-xs text-blue-600/70 dark:text-blue-400/70">母号总数</div>
          </div>
        </div>
      </div>
      <div class="rounded-xl border border-border bg-gradient-to-br from-violet-50 to-violet-100/50 dark:from-violet-950/30 dark:to-violet-900/20 p-4">
        <div class="flex items-center gap-3">
          <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-violet-500/10">
            <UserPlus class="h-5 w-5 text-violet-600 dark:text-violet-400" />
          </div>
          <div>
            <div class="text-2xl font-bold text-violet-700 dark:text-violet-300">{{ stats.childCount }}</div>
            <div class="text-xs text-violet-600/70 dark:text-violet-400/70">子号总数</div>
          </div>
        </div>
      </div>
      <div class="rounded-xl border border-border bg-gradient-to-br from-emerald-50 to-emerald-100/50 dark:from-emerald-950/30 dark:to-emerald-900/20 p-4">
        <div class="flex items-center gap-3">
          <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-500/10">
            <Monitor class="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
          </div>
          <div>
            <div class="text-2xl font-bold text-emerald-700 dark:text-emerald-300">{{ stats.envCount }}</div>
            <div class="text-xs text-emerald-600/70 dark:text-emerald-400/70">已创建环境</div>
          </div>
        </div>
      </div>
      <div class="rounded-xl border border-border bg-gradient-to-br from-amber-50 to-amber-100/50 dark:from-amber-950/30 dark:to-amber-900/20 p-4">
        <div class="flex items-center gap-3">
          <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-500/10">
            <Armchair class="h-5 w-5 text-amber-600 dark:text-amber-400" />
          </div>
          <div>
            <div class="text-2xl font-bold text-amber-700 dark:text-amber-300">{{ stats.seatUsed }}/{{ stats.seatTotal }}</div>
            <div class="text-xs text-amber-600/70 dark:text-amber-400/70">座位使用</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 搜索和筛选 -->
    <div class="flex flex-wrap items-center gap-3">
      <div class="relative flex-1 min-w-[200px] max-w-sm">
        <Search class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input 
          v-model="searchQuery" 
          placeholder="搜索邮箱..." 
          class="pl-9 h-9"
        />
        <button v-if="searchQuery" class="absolute right-3 top-1/2 -translate-y-1/2" @click="searchQuery = ''">
          <X class="h-4 w-4 text-muted-foreground hover:text-foreground" />
        </button>
      </div>
      <Select v-model="envFilter">
        <SelectTrigger class="w-[140px] h-9">
          <SelectValue placeholder="环境状态" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">全部状态</SelectItem>
          <SelectItem value="created">已创建环境</SelectItem>
          <SelectItem value="not_created">未创建环境</SelectItem>
        </SelectContent>
      </Select>

      <div class="text-sm text-muted-foreground ml-auto">
        共 <span class="font-medium text-foreground">{{ filteredMothers.length }}</span> 条结果
      </div>
    </div>

    <Card class="bg-card text-card-foreground">
      <CardContent class="p-0">
        <div class="overflow-x-auto rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead class="w-10">
                  <Checkbox v-model="selectAllState" />
                </TableHead>
                <TableHead class="w-10"></TableHead>
                <TableHead class="min-w-[220px]">母号邮箱</TableHead>
                <TableHead class="w-20">座位</TableHead>
                <TableHead class="w-24">备注</TableHead>
                <TableHead class="min-w-[280px]">状态</TableHead>
                <TableHead class="w-44">进度</TableHead>
                <TableHead class="w-36">创建时间</TableHead>
                <TableHead class="w-64 text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <!-- 加载中 -->
              <TableRow v-if="loading && mothers.length === 0">
                <TableCell colspan="9" class="py-10 text-center">
                  <div class="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                    <Loader2 class="h-4 w-4 animate-spin" />
                    加载中...
                  </div>
                </TableCell>
              </TableRow>

              <!-- 空状态 -->
              <TableRow v-else-if="!loading && mothers.length === 0">
                <TableCell colspan="9" class="py-16">
                  <div class="flex flex-col items-center justify-center gap-4 text-center">
                    <div class="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
                      <Users class="h-8 w-8 text-muted-foreground" />
                    </div>
                    <div>
                      <h3 class="text-lg font-medium text-foreground">还没有账号</h3>
                      <p class="mt-1 text-sm text-muted-foreground">点击上方「生成母号」按钮创建你的第一个 GPT 母号</p>
                    </div>
                    <Button class="gap-2" @click="openCreateMother">
                      <Plus class="h-4 w-4" />
                      生成母号
                    </Button>
                    <div class="mt-4 rounded-lg border border-dashed border-border bg-muted/30 p-4 text-left text-sm">
                      <p class="font-medium text-foreground mb-2">💡 快捷操作提示</p>
                      <ul class="space-y-1 text-muted-foreground">
                        <li><kbd class="px-1.5 py-0.5 rounded bg-muted text-xs">↑</kbd> <kbd class="px-1.5 py-0.5 rounded bg-muted text-xs">↓</kbd> 上下切换选中行</li>
                        <li><kbd class="px-1.5 py-0.5 rounded bg-muted text-xs">Enter</kbd> 打开/创建环境</li>
                        <li><kbd class="px-1.5 py-0.5 rounded bg-muted text-xs">⌘</kbd> + <kbd class="px-1.5 py-0.5 rounded bg-muted text-xs">Delete</kbd> 删除选中项</li>
                        <li><kbd class="px-1.5 py-0.5 rounded bg-muted text-xs">Esc</kbd> 取消选择</li>
                      </ul>
                    </div>
                  </div>
                </TableCell>
              </TableRow>

              <!-- 搜索无结果 -->
              <TableRow v-else-if="filteredMothers.length === 0">
                <TableCell colspan="9" class="py-12">
                  <div class="flex flex-col items-center justify-center gap-3 text-center">
                    <Search class="h-10 w-10 text-muted-foreground/50" />
                    <div>
                      <h3 class="font-medium text-foreground">没有找到匹配的账号</h3>
                      <p class="mt-1 text-sm text-muted-foreground">尝试调整搜索条件或筛选器</p>
                    </div>
                    <Button variant="outline" size="sm" @click="searchQuery = ''; envFilter = 'all'">
                      清除筛选
                    </Button>
                  </div>
                </TableCell>
              </TableRow>

              <!-- 数据列表 -->
              <template v-else v-for="(mother, index) in filteredMothers" :key="mother.id">
                <TableRow
                  class="cursor-pointer transition-colors"
                  :class="[
                    selectedIds.has(mother.id)
                      ? 'bg-primary/15 hover:bg-primary/20 border-l-2 border-l-primary'
                      : selectedMotherId === mother.id
                        ? 'bg-primary/10 hover:bg-primary/15 border-l-2 border-l-primary'
                        : index % 2 === 0 ? 'bg-background hover:bg-muted/50' : 'bg-muted/20 hover:bg-muted/50'
                  ]"
                  @click="onCurrentChange(mother)"
                >
                  <TableCell @click.stop>
                    <Checkbox
                      :model-value="selectedIds.has(mother.id)"
                      @update:modelValue="(val: boolean | 'indeterminate') => handleRowSelect(mother.id, val)"
                    />
                  </TableCell>
                  <TableCell>
                    <Button variant="ghost" size="xs" class="h-6 w-6 p-0" @click.stop="toggleExpand(mother.id)">
                      <LayoutList class="h-4 w-4 transition-transform" :class="{ 'rotate-90': expandedRows.has(mother.id) }" />
                    </Button>
                  </TableCell>
                  <TableCell class="font-medium">
                    <button class="text-left text-primary hover:text-primary/70 transition-colors cursor-pointer" @click.stop="openAccountDetail(mother)">
                      {{ mother.email }}
                    </button>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" class="font-mono">
                      {{ mother.seat_used || 0 }}/{{ mother.seat_total || 0 }}
                    </Badge>
                  </TableCell>
                  <TableCell class="text-muted-foreground text-xs truncate max-w-[120px]">{{ mother.note }}</TableCell>
                  <TableCell>
                    <div class="flex flex-wrap gap-1">
                      <Badge 
                        :class="getEnvStatusClass(mother.geekez_profile_exists)"
                        variant="outline" 
                        class="text-xs"
                      >
                        创建
                      </Badge>
                      <Badge
                        v-for="b in getAccountStatusBadges(mother)"
                        :key="b.key"
                        variant="outline"
                        class="text-[11px] leading-4"
                        :class="b.class"
                      >
                        {{ b.text }}
                      </Badge>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div v-if="mother.active_task && ['pending','running'].includes(mother.active_task.status || '')" class="space-y-1">
                      <div class="flex items-center gap-2">
                        <Loader2 class="h-3.5 w-3.5 animate-spin text-primary" />
                        <span class="text-xs text-muted-foreground">
                          {{ mother.active_task.progress_label || '运行中' }}
                        </span>
                        <span class="ml-auto text-xs text-muted-foreground">
                          {{ getProgressPercent(mother) }}%
                        </span>
                      </div>
                      <div class="h-1.5 w-full rounded bg-muted">
                        <div class="h-1.5 rounded bg-primary" :class="getProgressWidthClass(mother)"></div>
                      </div>
                    </div>
                    <span v-else class="text-xs text-muted-foreground">-</span>
                  </TableCell>
                  <TableCell class="text-muted-foreground text-xs">{{ formatDate(mother.created_at) }}</TableCell>
                  <TableCell class="text-right" @click.stop>
                    <div class="flex items-center justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="xs"
                        class="gap-1 text-teal-600 hover:text-teal-700 hover:bg-teal-50 dark:text-teal-400 dark:hover:bg-teal-950"
                        @click="launchGeekez(mother)"
                      >
                        <ExternalLink class="h-3.5 w-3.5" />
                        {{ getGeekezActionLabel(mother) }}
                      </Button>
                      <Button
                        variant="ghost"
                        size="xs"
                        class="gap-1 text-orange-600 hover:text-orange-700 hover:bg-orange-50 dark:text-orange-400 dark:hover:bg-orange-950"
                        @click="openCreateChild(mother)"
                      >
                        <Plus class="h-3.5 w-3.5" />
                        子号
                      </Button>
                      <Button
                        variant="ghost"
                        size="xs"
                        class="gap-1 text-sky-600 hover:text-sky-700 hover:bg-sky-50 dark:text-sky-400 dark:hover:bg-sky-950"
                        @click="editSeat(mother)"
                      >
                        <Settings class="h-3.5 w-3.5" />
                        座位
                      </Button>
                      <Button
                        variant="ghost"
                        size="xs"
                        class="gap-1 text-slate-600 hover:text-slate-700 hover:bg-slate-50 dark:text-slate-400 dark:hover:bg-slate-900"
                        @click="viewTasks(mother)"
                      >
                        <FileText class="h-3.5 w-3.5" />
                        日志
                      </Button>
                      <Button
                        variant="ghost"
                        size="xs"
                        class="gap-1 text-destructive hover:text-destructive"
                        @click="removeAccount(mother.id)"
                      >
                        <Trash2 class="h-3.5 w-3.5" />
                        删除
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>

                <!-- Expanded Child Rows -->
                <TableRow v-if="expandedRows.has(mother.id)">
                  <TableCell colspan="9" class="p-0 bg-muted/10">
                    <div class="p-4 pl-12 border-b border-border">
                      <div class="mb-2 text-xs font-semibold text-muted-foreground">子账号列表 ({{ mother.children?.length || 0 }})</div>
                      <div class="rounded-lg border border-border overflow-hidden bg-background">
                        <Table>
                          <TableHeader class="bg-muted/30">
                            <TableRow>
                              <TableHead>邮箱</TableHead>
                              <TableHead>备注</TableHead>
                              <TableHead>状态</TableHead>
                              <TableHead>创建时间</TableHead>
                              <TableHead class="text-right">操作</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            <TableRow v-for="child in mother.children || []" :key="child.id">
                              <TableCell>
                                <button class="text-left text-primary hover:text-primary/70 transition-colors cursor-pointer" @click.stop="openAccountDetail(child)">
                                  {{ child.email }}
                                </button>
                              </TableCell>
                              <TableCell class="text-muted-foreground text-xs">{{ child.note }}</TableCell>
                              <TableCell>
                                <div class="flex flex-wrap gap-1">
                                  <Badge 
                                    :class="getEnvStatusClass(child.geekez_profile_exists)"
                                    variant="outline"
                                    class="text-xs"
                                  >
                                    创建
                                  </Badge>
                                  <Badge
                                    v-for="b in getAccountStatusBadges(child)"
                                    :key="b.key"
                                    variant="outline"
                                    class="text-[11px] leading-4"
                                    :class="b.class"
                                  >
                                    {{ b.text }}
                                  </Badge>
                                </div>
                              </TableCell>
                              <TableCell class="text-muted-foreground text-xs">{{ formatDate(child.created_at) }}</TableCell>
                              <TableCell class="text-right">
                                <div class="flex items-center justify-end gap-1">
                                  <Button variant="ghost" size="xs" @click.stop="launchGeekez(child)">
                                    {{ getGeekezActionLabel(child) }}
                                  </Button>
                                  <Button variant="ghost" size="xs" class="text-destructive hover:text-destructive" @click.stop="removeAccount(child.id)">删除</Button>
                                </div>
                              </TableCell>
                            </TableRow>
                            <TableRow v-if="!mother.children?.length">
                              <TableCell colspan="5" class="text-center text-xs text-muted-foreground py-4">无子账号</TableCell>
                            </TableRow>
                          </TableBody>
                        </Table>
                      </div>
                    </div>
                  </TableCell>
                </TableRow>
              </template>
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>

    <!-- Dialogs follow (will be replaced in next step) -->
    <Dialog v-model:open="motherDialogVisible">
      <DialogContent class="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>生成母号</DialogTitle>
          <DialogDescription>配置邮箱与座位数生成新的母账号</DialogDescription>
        </DialogHeader>
        <div class="grid gap-4 py-4">
          <div class="grid gap-2">
            <label class="text-sm font-medium">邮箱配置</label>
            <Select :model-value="String(motherForm.cloudmail_config_id || '')" @update:modelValue="(v) => motherForm.cloudmail_config_id = Number(v)">
              <SelectTrigger>
                <SelectValue placeholder="请选择 admin/email 配置" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="cfg in cloudMailConfigs" :key="cfg.id" :value="String(cfg.id)">
                  {{ cfg.name }}{{ cfg.is_default ? ' (默认)' : '' }} ({{ cfg.domains_count || cfg.domains?.length || 0 }} domains)
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium">域名</label>
            <Select
              :model-value="motherForm.domain || '__random__'"
              @update:model-value="(v) => {
                const s = String(v ?? '__random__')
                motherForm.domain = s === '__random__' ? '' : s
              }"
            >
              <SelectTrigger>
                <SelectValue placeholder="留空=随机" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__random__">随机</SelectItem>
                <SelectItem v-for="d in motherDomains" :key="d" :value="d">{{ d }}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div class="grid gap-2">
              <label class="text-sm font-medium">座位数</label>
              <Input :model-value="motherForm.seat_total" @update:modelValue="(v) => motherForm.seat_total = Number(v)" type="number" :min="0" :max="500" />
            </div>
            <div class="grid gap-2">
              <label class="text-sm font-medium">生成数量</label>
              <Input :model-value="motherForm.count" @update:modelValue="(v) => motherForm.count = Number(v)" type="number" :min="1" :max="200" />
            </div>
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium">备注</label>
            <textarea
              v-model="motherForm.note"
              rows="2"
              class="min-h-[60px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              placeholder="可选"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" @click="motherDialogVisible = false">取消</Button>
          <Button :disabled="creating" @click="createMother">
            <Loader2 v-if="creating" class="mr-2 h-4 w-4 animate-spin" />
            创建
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Dialog v-model:open="childDialogVisible">
      <DialogContent class="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>生成子账号</DialogTitle>
          <DialogDescription>为 {{ activeMother?.email }} 生成子号</DialogDescription>
        </DialogHeader>
        <div class="grid gap-4 py-4">
          <div class="grid gap-2">
            <label class="text-sm font-medium">域名</label>
            <Select v-model="childForm.domain">
              <SelectTrigger>
                <SelectValue placeholder="留空=随机" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">随机</SelectItem>
                <SelectItem v-for="d in childDomains" :key="d" :value="d">{{ d }}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium">生成数量</label>
            <Input :model-value="childForm.count" @update:modelValue="(v) => childForm.count = Number(v)" type="number" :min="1" :max="500" />
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium">备注</label>
            <textarea
              v-model="childForm.note"
              rows="2"
              class="min-h-[60px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              placeholder="可选"
            />
          </div>
        </div>
        <DialogFooter>
          <DialogClose as-child>
            <Button variant="outline">取消</Button>
          </DialogClose>
          <Button :disabled="creating" @click="createChild">
            <Loader2 v-if="creating" class="mr-2 h-4 w-4 animate-spin" />
            创建
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Dialog v-model:open="sub2apiDialogVisible">
      <DialogContent class="sm:max-w-[620px]">
        <DialogHeader>
          <DialogTitle>{{ sub2apiAction === 'invite_and_pool' ? '自动邀请并入池配置' : '自动入池配置' }}</DialogTitle>
          <DialogDescription>
            保存配置后先测试连接，通过后再开始执行（当前将对 {{ sub2apiMotherIds.length }} 个母号生效）
          </DialogDescription>
        </DialogHeader>
          <div class="grid gap-4 py-4">
          <div class="rounded-lg border border-border bg-muted/30 p-3">
            <div class="text-sm font-medium">目标</div>
            <div class="mt-1 text-xs text-muted-foreground">保存配置后测试连接，通过后再开始。</div>

            <div class="mt-3 grid gap-2">
              <label class="text-sm font-medium">{{ sub2apiAction === 'invite_and_pool' ? '入到哪里' : '入池到' }}</label>
              <Select v-model="poolMode">
                <SelectTrigger>
                  <SelectValue placeholder="请选择" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem v-if="sub2apiAction !== 'invite_and_pool'" value="crs">crs</SelectItem>
                  <SelectItem value="s2a">s2a</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <template v-if="poolMode === 'crs'">
              <div class="mt-3 text-xs text-muted-foreground font-mono"># [crs] api_base = "..."  admin_token = "..."</div>
              <div class="mt-3 grid gap-2">
                <label class="text-sm font-medium">CRS API Base</label>
                <Input v-model="crsForm.api_base" placeholder="https://crs.example.com" />
              </div>
              <div class="mt-3 grid gap-2">
                <label class="text-sm font-medium">CRS Admin Token</label>
                <Input v-model="crsForm.admin_token" type="password" placeholder="留空表示不修改" />
                <div v-if="crsHint.admin_token_masked" class="text-xs text-muted-foreground">已保存：{{ crsHint.admin_token_masked }}（不需要每次输入，只有要更新 token 才粘贴）</div>
              </div>
            </template>

            <template v-if="poolMode === 's2a'">
              <div class="mt-4 grid gap-2">
                <label class="text-sm font-medium">S2A API Base</label>
                <Input v-model="sub2apiForm.api_base" placeholder="https://sub2.pigll.site/api/v1" />
              </div>

              <div class="grid gap-2">
                <label class="text-sm font-medium">Admin API Key（推荐）</label>
                <Input v-model="sub2apiForm.admin_key" type="password" placeholder="留空表示不修改" />
                <div v-if="sub2apiHint.admin_key_masked" class="text-xs text-muted-foreground">已保存：{{ sub2apiHint.admin_key_masked }}（不需要每次输入，只有要更新 key 才粘贴）</div>
              </div>

              <div class="grid gap-2">
                <label class="text-sm font-medium">JWT Token（备选）</label>
                <Input v-model="sub2apiForm.admin_token" type="password" placeholder="留空表示不修改" />
                <div v-if="sub2apiHint.admin_token_masked" class="text-xs text-muted-foreground">已保存：{{ sub2apiHint.admin_token_masked }}（不需要每次输入，只有要更新 token 才粘贴）</div>
              </div>

              <div class="grid grid-cols-2 gap-4">
                <div class="grid gap-2">
                  <label class="text-sm font-medium">并发</label>
                  <Input :model-value="sub2apiForm.concurrency" @update:modelValue="(v) => sub2apiForm.concurrency = Number(v)" type="number" :min="1" :max="50" />
                </div>
                <div class="grid gap-2">
                  <label class="text-sm font-medium">优先级</label>
                  <Input :model-value="sub2apiForm.priority" @update:modelValue="(v) => sub2apiForm.priority = Number(v)" type="number" :min="0" :max="999" />
                </div>
              </div>

              <div class="grid gap-2">
                <label class="text-sm font-medium">分组 ID 列表</label>
                <Input v-model="sub2apiForm.group_ids" placeholder="例如：2 或 2,3" />
              </div>

              <div class="grid gap-2">
                <label class="text-sm font-medium">分组名称列表（可选）</label>
                <Input v-model="sub2apiForm.group_names" placeholder="例如：默认组 或 default" />
              </div>
            </template>

            <div class="text-xs text-muted-foreground">
              流程：保存 → 测试连接 → {{ sub2apiAction === 'invite_and_pool' ? '开始邀请并入池' : '开始入池' }}
            </div>
            <div v-if="sub2apiTestMessage" class="text-xs" :class="sub2apiTestOk ? 'text-emerald-600' : 'text-rose-600'">{{ sub2apiTestMessage }}</div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" @click="sub2apiDialogVisible = false">取消</Button>
           <Button variant="outline" :disabled="sub2apiSaving" @click="saveS2aTargetConfig">
             <Loader2 v-if="sub2apiSaving" class="mr-2 h-4 w-4 animate-spin" />
             保存
           </Button>
          <Button variant="outline" :disabled="sub2apiTesting" @click="testS2aTargetConnection">
            <Loader2 v-if="sub2apiTesting" class="mr-2 h-4 w-4 animate-spin" />
            测试连接
          </Button>
          <Button :disabled="!sub2apiTestOk || sub2apiStarting" class="bg-violet-600 hover:bg-violet-700 text-white" @click="startSub2apiSink">
            <Loader2 v-if="sub2apiStarting" class="mr-2 h-4 w-4 animate-spin" />
            {{ sub2apiAction === 'invite_and_pool' ? '开始邀请并入池' : '开始入池' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Tasks Sheet -->
    <Sheet v-model:open="tasksDrawerVisible">
      <SheetContent side="right" class="w-full sm:max-w-[800px]">
        <SheetHeader>
          <div class="flex items-start justify-between gap-3">
            <div>
              <SheetTitle>任务日志</SheetTitle>
              <SheetDescription>账号：{{ tasksDrawerAccount?.email }}</SheetDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              class="text-destructive border-destructive/40 hover:bg-destructive/10"
              @click="clearTaskRecords"
            >
              清空记录
            </Button>
          </div>
        </SheetHeader>
        <div class="mt-4 h-[calc(100vh-140px)] overflow-y-auto">
          <div v-if="tasksLoading" class="py-10 text-center text-muted-foreground">
            <Loader2 class="mx-auto h-6 w-6 animate-spin" />
            <span class="mt-2 block text-sm">加载中...</span>
          </div>
          <div v-else>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>类型</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>时间</TableHead>
                  <TableHead>错误</TableHead>
                  <TableHead class="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow v-for="task in accountTasks" :key="task.id">
                  <TableCell>
                    <Badge variant="outline">{{ getTaskTypeName(task.type || '') }}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge :variant="getStatusTag(task.status || '') === 'success' ? 'default' : 'destructive'">
                      {{ task.status }}
                    </Badge>
                  </TableCell>
                  <TableCell class="text-xs text-muted-foreground">{{ formatDate(task.created_at) }}</TableCell>
                  <TableCell class="text-xs text-destructive max-w-[150px] truncate" :title="task.error">{{ task.error || '-' }}</TableCell>
                  <TableCell class="text-right">
                    <div class="flex justify-end gap-2">
                      <Button variant="ghost" size="xs" @click="viewTaskArtifacts(task)">产物</Button>
                      <Button
                        variant="ghost"
                        size="xs"
                        @click="task.celery_task_id ? openCeleryTask(String(task.celery_task_id)) : viewTaskLog(task)"
                      >
                        日志
                      </Button>
                      <Button
                        v-if="task.id && ['running', 'pending'].includes(task.status || '')"
                        variant="outline"
                        size="xs"
                        class="h-6 border-destructive/40 text-destructive hover:bg-destructive/10"
                        @click.stop="cancelTask(task.id)"
                      >
                        中断
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
                <TableRow v-if="accountTasks.length === 0">
                  <TableCell colspan="5" class="py-8 text-center text-sm text-muted-foreground">暂无记录</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>
        </div>
      </SheetContent>
    </Sheet>

    <!-- Artifacts Dialog -->
    <ArtifactsDialog
      :open="artifactsDialogVisible"
      :loading="artifactsLoading"
      :artifacts="currentTaskArtifacts"
      @update:open="artifactsDialogVisible = $event"
    />

    <!-- Account Detail Dialog -->
    <Dialog v-model:open="accountDetailDialogVisible">
      <DialogContent class="sm:max-w-[400px]">
        <DialogHeader>
          <DialogTitle>账号信息</DialogTitle>
          <DialogDescription>{{ accountDetailData?.email }}</DialogDescription>
        </DialogHeader>
        <div class="grid gap-4 py-4">
          <div class="grid gap-2">
            <label class="text-sm font-medium text-muted-foreground">邮箱</label>
            <div class="flex items-center gap-2">
              <code class="flex-1 rounded bg-muted px-3 py-2 font-mono text-sm">{{ accountDetailData?.email || '-' }}</code>
              <Button v-if="accountDetailData?.email" variant="outline" size="sm" @click="copyText(accountDetailData.email)">
                <Copy class="h-4 w-4" />
              </Button>
            </div>
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium text-muted-foreground">账号密码</label>
            <div class="flex items-center gap-2">
              <code class="flex-1 rounded bg-muted px-3 py-2 font-mono text-sm">{{ accountDetailData?.account_password || '-' }}</code>
              <Button v-if="accountDetailData?.account_password" variant="outline" size="sm" @click="copyText(accountDetailData.account_password)">
                <Copy class="h-4 w-4" />
              </Button>
            </div>
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium text-muted-foreground">邮箱密码</label>
            <div class="flex items-center gap-2">
              <code class="flex-1 rounded bg-muted px-3 py-2 font-mono text-sm">{{ accountDetailData?.email_password || '-' }}</code>
              <Button v-if="accountDetailData?.email_password" variant="outline" size="sm" @click="copyText(accountDetailData.email_password)">
                <Copy class="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" @click="accountDetailDialogVisible = false">关闭</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Log Dialog -->
    <Dialog v-model:open="taskLogDialogVisible">
      <DialogContent class="sm:max-w-[900px]">
        <DialogHeader>
          <DialogTitle>任务日志</DialogTitle>
          <DialogDescription v-if="currentLogTask">步骤、增项与日志内容（Task ID: {{ currentLogTask.id }}）</DialogDescription>
        </DialogHeader>
        <div class="py-2">
          <div class="mb-2 flex items-center justify-between">
            <span class="text-xs text-muted-foreground">{{ currentLogFilename }}</span>
            <div class="flex gap-2">
              <a v-if="currentLogDownloadUrl" :href="currentLogDownloadUrl" target="_blank" class="text-xs text-primary hover:underline">下载日志</a>
              <button class="text-xs text-primary hover:underline" @click="reloadTaskLog">刷新</button>
            </div>
          </div>
          <div v-if="!taskLogLoading">
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
                    <div v-if="step.time" class="text-xs text-muted-foreground">{{ step.time }}</div>
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
              <pre class="whitespace-pre-wrap font-mono text-xs text-foreground">{{ taskLogText || '暂无日志内容' }}</pre>
            </div>
          </div>
          <div v-else class="flex h-[400px] items-center justify-center">
            <Loader2 class="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        </div>
      </DialogContent>
    </Dialog>

    <!-- Team Push Dialog -->
    <Dialog v-model:open="teamPushDialogVisible">
      <DialogContent class="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>推送到兑换系统</DialogTitle>
          <DialogDescription>将 {{ teamPushMotherIds.length }} 个账号推送到 Team 兑换系统</DialogDescription>
        </DialogHeader>
        <div class="grid gap-4 py-4">
          <div class="grid gap-2">
            <label class="text-sm font-medium">目标系统 URL</label>
            <Input v-model="teamPushForm.target_url" placeholder="https://your-team-system.com" />
            <div class="text-xs text-muted-foreground">兑换系统的完整 URL（例如：https://team.example.com）</div>
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium">管理员密码</label>
            <Input v-model="teamPushForm.password" type="password" placeholder="输入管理员密码" />
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div class="grid gap-2">
              <label class="text-sm font-medium">座位数</label>
              <Input v-model.number="teamPushForm.seat_total" type="number" min="1" placeholder="5" />
            </div>
            <div class="flex items-center gap-2 pt-6">
              <Checkbox v-model:checked="teamPushForm.is_warranty" />
              <label class="text-sm text-muted-foreground">质保</label>
            </div>
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium">备注</label>
            <Input v-model="teamPushForm.note" placeholder="从auto推送" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" @click="teamPushDialogVisible = false">取消</Button>
          <Button :disabled="teamPushLoading || !teamPushForm.target_url || !teamPushForm.password" class="bg-purple-600 hover:bg-purple-700 text-white" @click="executeTeamPush">
            <Loader2 v-if="teamPushLoading" class="mr-2 h-4 w-4 animate-spin" />
            推送
          </Button>
        </DialogFooter>
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
                <Switch :checked="traceFollowLatest" @update:checked="traceFollowLatest = $event" />
                <span class="text-xs text-muted-foreground">自动刷新</span>
              </div>
            </div>
            <div class="rounded-lg border border-border bg-muted/20 px-4 py-3">
              <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
                <span class="font-medium text-foreground">{{ celeryEmail || '-' }}</span>
                <span
                  class="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium"
                  :title="celeryStatusText || ''"
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
  </div>
</template>

<script setup lang="ts">
import { computed, inject, nextTick, onMounted, onUnmounted, provide, reactive, ref, watch, type Ref } from 'vue'
import { ElMessage, ElMessageBox } from '@/lib/element'
import { cleanLogText, normalizeTraceLines as _normalizeTraceLines, type TraceLine } from '@/lib/log-utils'
import {
  Armchair,
  Copy,
  ExternalLink,
  FileText,
  Loader2,
  Monitor,
  Plus,
  Search,
  Settings,
  UserPlus,
  Users,
  LayoutList,
  X,
  Trash2
} from 'lucide-vue-next'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Switch } from '@/components/ui/switch'
import ArtifactsDialog from '@/components/ArtifactsDialog.vue'

import { getCloudMailConfigs, type CloudMailConfig } from '@/api/email'
import type { GptBusinessAccount, GptBusinessAccountsResponse } from '@/api/gpt_business'
import { gptBusinessApi } from '@/api/gpt_business'

type MotherRow = GptBusinessAccountsResponse['mothers'][number]

// 从父组件注入状态
const selectedMother = inject<Ref<GptBusinessAccount | null>>('selectedMother')!
const selectedMotherIds = inject<Ref<string[]>>('selectedMotherIds')!
const accountsLoading = inject<Ref<boolean>>('accountsLoading')!

const loading = ref(false)
const creating = ref(false)
const cloudMailConfigs = ref<CloudMailConfig[]>([])

const mothers = ref<any[]>([])
const selectedMotherId = computed(() => selectedMother.value?.id)

// 搜索和筛选
const searchQuery = ref('')
const envFilter = ref('all')

// 批量选择
const selectedIds = ref<Set<string>>(new Set())
const selectAllState = computed<boolean | 'indeterminate'>({
  get: () => {
    const total = filteredMothers.value.length
    if (total === 0) return false
    let selectedCount = 0
    for (const mother of filteredMothers.value) {
      if (selectedIds.value.has(mother.id)) selectedCount++
    }
    if (selectedCount === 0) return false
    if (selectedCount === total) return true
    return 'indeterminate'
  },
  set: (val) => {
    if (val === true) {
      filteredMothers.value.forEach((m: any) => selectedIds.value.add(m.id))
    } else {
      selectedIds.value.clear()
    }
    selectedIds.value = new Set(selectedIds.value) // 触发响应式
  }
})

watch(
  selectedIds,
  (val) => {
    if (!selectedMotherIds) return
    selectedMotherIds.value = Array.from(val)
  },
  { immediate: true }
)

const onSelectionClear = () => {
  selectedIds.value.clear()
  selectedIds.value = new Set(selectedIds.value)
}

const handleRowSelect = (id: string, checked: boolean | 'indeterminate') => {
  if (checked === true) {
    selectedIds.value.add(id)
  } else {
    selectedIds.value.delete(id)
  }
  selectedIds.value = new Set(selectedIds.value) // 触发响应式
}

// 批量操作
const batchRunSelfRegister = async () => {
  if (selectedIds.value.size === 0) return
  const ids = Array.from(selectedIds.value)
  try {
    await gptBusinessApi.batchSelfRegister({
      mother_ids: ids,
      concurrency: 5,
      open_geekez: true
    })
    ElMessage.success(`已启动 ${ids.length} 个母号的自动开通`)
    selectedIds.value.clear()
    refresh()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '批量操作失败')
  }
}

const batchRunAutoInvite = async () => {
  if (selectedIds.value.size === 0) return
  const ids = Array.from(selectedIds.value)
  await openSub2apiSinkDialog(ids, 'invite_and_pool')
}

const sub2apiDialogVisible = ref(false)
const sub2apiMotherIds = ref<string[]>([])
const sub2apiAction = ref<'pool_only' | 'invite_and_pool'>('pool_only')

const sub2apiForm = reactive({
  api_base: '',
  admin_key: '',
  admin_token: '',
  concurrency: 5,
  priority: 50,
  group_ids: '2',
  group_names: ''
})

const crsForm = reactive({
  api_base: '',
  admin_token: ''
})

const crsHint = reactive({
  admin_token_masked: ''
})

const sub2apiHint = reactive({
  admin_key_masked: '',
  admin_token_masked: ''
})

const sub2apiSaving = ref(false)
const sub2apiTesting = ref(false)
const sub2apiTestOk = ref(false)
const sub2apiTestMessage = ref('')
const sub2apiStarting = ref(false)

const poolMode = ref<'crs' | 's2a'>('crs')

const _splitCsv = (raw: string) => {
  return String(raw || '')
    .split(/[,\s]+/)
    .map(s => s.trim())
    .filter(Boolean)
}

const loadSinkSettingsFromSettings = async () => {
  const settings = await gptBusinessApi.getSettings()

  const crsCfg = settings?.crs || {}
  crsForm.api_base = String(crsCfg.api_base || '')
  crsHint.admin_token_masked = String(crsCfg.admin_token || '')
  crsForm.admin_token = ''

  const s2aCfg = settings?.s2a || {}
  sub2apiForm.api_base = String(s2aCfg.api_base || '')
  sub2apiForm.concurrency = Number(s2aCfg.concurrency || 5)
  sub2apiForm.priority = Number(s2aCfg.priority || 50)
  sub2apiForm.group_ids = Array.isArray(s2aCfg.group_ids) ? s2aCfg.group_ids.join(',') : String(s2aCfg.group_ids || '2')
  sub2apiForm.group_names = Array.isArray(s2aCfg.group_names) ? s2aCfg.group_names.join(',') : String(s2aCfg.group_names || '')
  // secrets are masked by backend; do not prefill to avoid overwriting
  sub2apiHint.admin_key_masked = String(s2aCfg.admin_key || '')
  sub2apiHint.admin_token_masked = String(s2aCfg.admin_token || '')
  sub2apiForm.admin_key = ''
  sub2apiForm.admin_token = ''

  sub2apiTestOk.value = false
  sub2apiTestMessage.value = ''
}

const openSub2apiSinkDialog = async (
  motherIds: string[],
  action: 'pool_only' | 'invite_and_pool' = 'pool_only'
) => {
  sub2apiMotherIds.value = motherIds
  sub2apiAction.value = action
  if (sub2apiAction.value === 'invite_and_pool') {
    poolMode.value = 's2a'
  }
  try {
    await loadSinkSettingsFromSettings()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '读取入池配置失败')
  }
  sub2apiDialogVisible.value = true
}

const saveS2aTargetConfig = async () => {
  sub2apiSaving.value = true
  try {
    // 一键保存：CRS + S2A（隐藏的字段也按当前已加载值保存，避免每次都要重输）
    const groupIds = _splitCsv(sub2apiForm.group_ids)
      .filter(x => /^\d+$/.test(x))
      .map(x => Number(x))
    const groupNames = _splitCsv(sub2apiForm.group_names)

    const payload: any = {
      crs: {
        api_base: String(crsForm.api_base || '').trim()
      },
      s2a: {
        api_base: String(sub2apiForm.api_base || '').trim(),
        concurrency: Number(sub2apiForm.concurrency || 5),
        priority: Number(sub2apiForm.priority || 50),
        group_ids: groupIds,
        group_names: groupNames
      },
      // Single-config mode: disable multi-target settings to avoid unexpected overrides
      s2a_targets: [],
      s2a_default_target: ''
    }

    if (String(crsForm.admin_token || '').trim()) {
      payload.crs.admin_token = String(crsForm.admin_token || '').trim()
    }
    if (String(sub2apiForm.admin_key || '').trim()) {
      payload.s2a.admin_key = String(sub2apiForm.admin_key || '').trim()
    }
    if (String(sub2apiForm.admin_token || '').trim()) {
      payload.s2a.admin_token = String(sub2apiForm.admin_token || '').trim()
    }

    await gptBusinessApi.updateSettings(payload)
    ElMessage.success('已保存入池配置')
    await loadSinkSettingsFromSettings()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '保存失败')
  } finally {
    sub2apiSaving.value = false
  }
}

const testS2aTargetConnection = async () => {
  sub2apiTesting.value = true
  sub2apiTestOk.value = false
  sub2apiTestMessage.value = ''
  try {
    // 避免测试到旧配置：先保存一次（后端会保留已脱敏的 secret，不会被空值覆盖）
    await saveS2aTargetConfig()

    const s2aRes = await gptBusinessApi.testS2aConnection({})
    const s2aOk = !!s2aRes?.success

    if (poolMode.value === 'crs') {
      const crsRes = await gptBusinessApi.testCrsConnection()
      const crsOk = !!crsRes?.success
      sub2apiTestOk.value = crsOk && s2aOk
      sub2apiTestMessage.value = `CRS: ${crsOk ? 'ok' : (crsRes?.message || 'failed')} | S2A: ${s2aOk ? 'ok' : (s2aRes?.message || 'failed')}`
    } else {
      sub2apiTestOk.value = s2aOk
      sub2apiTestMessage.value = `S2A: ${s2aOk ? 'ok' : (s2aRes?.message || 'failed')}`
    }

    if (sub2apiTestOk.value) {
      ElMessage.success('连接测试通过')
    } else {
      ElMessage.error('连接测试失败')
    }
  } catch (e: any) {
    sub2apiTestOk.value = false
    sub2apiTestMessage.value = e?.response?.data?.message || e?.response?.data?.detail || e?.message || '连接测试失败'
    ElMessage.error(sub2apiTestMessage.value)
  } finally {
    sub2apiTesting.value = false
  }
}

const startSub2apiSink = async () => {
  if (!sub2apiTestOk.value) {
    ElMessage.warning('请先测试连接，通过后再开始')
    return
  }

  sub2apiStarting.value = true
  try {
    const ids = sub2apiMotherIds.value || []
    if (sub2apiAction.value === 'invite_and_pool') {
      await gptBusinessApi.batchAutoInvite({
        mother_ids: ids,
        concurrency: Number(sub2apiForm.concurrency || 5),
        mode: poolMode.value,
        open_geekez: true
      })
      ElMessage.success(`已启动 ${ids.length} 个母号的自动邀请并入池`)
    } else {
      await gptBusinessApi.batchSub2apiSink({
        mother_ids: ids,
        concurrency: Number(sub2apiForm.concurrency || 5),
        mode: poolMode.value
      })
      ElMessage.success(`已启动 ${ids.length} 个母号的自动入池`)
    }
    selectedIds.value.clear()
    selectedIds.value = new Set(selectedIds.value)
    sub2apiDialogVisible.value = false
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '启动失败')
  } finally {
    sub2apiStarting.value = false
  }
}

const batchRunSub2apiSink = async () => {
  if (selectedIds.value.size === 0) return
  const ids = Array.from(selectedIds.value)
  await openSub2apiSinkDialog(ids, 'pool_only')
}

// ========== Team Push ==========
const teamPushDialogVisible = ref(false)
const teamPushMotherIds = ref<string[]>([])
const teamPushLoading = ref(false)
const teamPushForm = reactive({
  target_url: localStorage.getItem('gpt_team_push_url') || '',
  password: '',
  is_warranty: true,
  seat_total: 5,
  note: '从auto推送'
})

const openTeamPushDialog = (motherIds: string[]) => {
  teamPushMotherIds.value = motherIds
  // URL 从 localStorage 读取，不清空
  teamPushForm.password = ''
  teamPushForm.is_warranty = true
  teamPushForm.seat_total = 5
  teamPushForm.note = '从auto推送'
  teamPushDialogVisible.value = true
}

const executeTeamPush = async () => {
  if (!teamPushMotherIds.value.length) return
  if (!teamPushForm.target_url || !teamPushForm.password) {
    ElMessage.warning('请输入目标 URL 和密码')
    return
  }
  
  teamPushLoading.value = true
  try {
    // 批量推送
    const results = await Promise.allSettled(
      teamPushMotherIds.value.map(id =>
        gptBusinessApi.teamPush(id, {
          target_url: teamPushForm.target_url,
          password: teamPushForm.password,
          is_warranty: teamPushForm.is_warranty,
          seat_total: teamPushForm.seat_total,
          note: teamPushForm.note
        })
      )
    )
    const successCount = results.filter(r => r.status === 'fulfilled').length
    const failCount = results.filter(r => r.status === 'rejected').length
    
    if (failCount === 0) {
      ElMessage.success(`已启动 ${successCount} 个账号的推送任务`)
    } else {
      ElMessage.warning(`成功 ${successCount} 个，失败 ${failCount} 个`)
    }
    // 保存 URL 到 localStorage
    localStorage.setItem('gpt_team_push_url', teamPushForm.target_url)
    teamPushDialogVisible.value = false
    await refresh()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '推送失败')
  } finally {
    teamPushLoading.value = false
  }
}

// 监听头部工具栏的 Team Push 事件
onMounted(() => {
  const handleTeamPush = (e: Event) => {
    const detail = (e as CustomEvent).detail
    if (detail?.mother_ids?.length) {
      openTeamPushDialog(detail.mother_ids)
    }
  }
  window.addEventListener('gpt-open-team-push', handleTeamPush)
  onUnmounted(() => {
    window.removeEventListener('gpt-open-team-push', handleTeamPush)
  })
})

// 提供给父组件
provide('selectedIds', selectedIds)
provide('batchRunSelfRegister', batchRunSelfRegister)
provide('batchRunAutoInvite', batchRunAutoInvite)
provide('batchRunSub2apiSink', batchRunSub2apiSink)

// 统计信息
const stats = computed(() => {
  let motherCount = mothers.value.length
  let childCount = 0
  let envCount = 0
  let seatUsed = 0
  let seatTotal = 0

  mothers.value.forEach((m: any) => {
    childCount += m.children?.length || 0
    seatUsed += m.seat_used || 0
    seatTotal += m.seat_total || 0
    if (m.geekez_profile_exists) envCount++
    m.children?.forEach((c: any) => {
      if (c.geekez_profile_exists) envCount++
    })
  })

  return { motherCount, childCount, envCount, seatUsed, seatTotal }
})

// 过滤后的母号列表
const filteredMothers = computed(() => {
  let result = mothers.value

  // 搜索过滤
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter((m: any) => 
      m.email?.toLowerCase().includes(query) ||
      m.note?.toLowerCase().includes(query) ||
      m.children?.some((c: any) => c.email?.toLowerCase().includes(query))
    )
  }

  // 环境状态过滤
  if (envFilter.value === 'created') {
    result = result.filter((m: any) => m.geekez_profile_exists)
  } else if (envFilter.value === 'not_created') {
    result = result.filter((m: any) => !m.geekez_profile_exists)
  }

  return result
})

const formatDate = (date: string | undefined) => {
  if (!date) return '-'
  return new Date(date).toLocaleString()
}

const getProgressPercent = (mother: MotherRow) => {
  const percent = Number(mother.active_task?.progress_percent ?? 0)
  if (Number.isNaN(percent)) return 0
  return Math.max(0, Math.min(100, Math.round(percent)))
}

const getProgressWidthClass = (mother: MotherRow) => {
  const percent = getProgressPercent(mother)
  if (percent >= 100) return 'w-full'
  if (percent >= 75) return 'w-3/4'
  if (percent >= 50) return 'w-1/2'
  if (percent >= 25) return 'w-1/4'
  if (percent > 0) return 'w-1/6'
  return 'w-0'
}

const expandedRows = ref(new Set<number>())
const toggleExpand = (id: number) => {
  if (expandedRows.value.has(id)) {
    expandedRows.value.delete(id)
  } else {
    expandedRows.value.add(id)
  }
}

const motherDialogVisible = ref(false)
const childDialogVisible = ref(false)
const accountDetailDialogVisible = ref(false)
const accountDetailData = ref<GptBusinessAccount | null>(null)

const openAccountDetail = (account: GptBusinessAccount) => {
  accountDetailData.value = account
  accountDetailDialogVisible.value = true
}

const activeMother = ref<MotherRow | null>(null)

const motherForm = reactive({
  cloudmail_config_id: 0,
  domain: '',
  seat_total: 4,
  count: 1,
  note: ''
})

const childForm = reactive({
  domain: '',
  count: 1,
  note: ''
})

const selectedMotherConfig = computed(() => {
  if (!motherForm.cloudmail_config_id) return null
  return cloudMailConfigs.value.find(c => c.id === motherForm.cloudmail_config_id) || null
})

const motherDomains = computed(() => {
  return selectedMotherConfig.value?.domains || []
})

const childDomains = computed(() => {
  const configId = activeMother.value?.cloudmail_config_id
  if (!configId) return []
  const cfg = cloudMailConfigs.value.find(c => c.id === configId)
  return cfg?.domains || []
})

const fetchCloudMailConfigs = async () => {
  const res = await getCloudMailConfigs()
  const list = Array.isArray(res) ? res : res.results || []
  cloudMailConfigs.value = list.filter(c => c.is_active)
}

const refresh = async () => {
  loading.value = true
  accountsLoading.value = true
  try {
    const [accounts, _configs] = await Promise.all([gptBusinessApi.listAccounts(), fetchCloudMailConfigs()])
    mothers.value = accounts.mothers || []

    // 重新对齐当前选中
    const currentId = selectedMother.value?.id
    if (currentId) {
      const exists = mothers.value.find((m: any) => m.id === currentId)
      if (!exists) {
        selectedMother.value = null
      } else {
        selectedMother.value = exists
      }
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
    accountsLoading.value = false
  }
}

const onCurrentChange = (row: any) => {
  selectedMother.value = row || null
  activeMother.value = row || null
  if (!row?.id) return
  if (selectedIds.value.has(row.id)) {
    selectedIds.value.delete(row.id)
  } else {
    selectedIds.value.add(row.id)
  }
  selectedIds.value = new Set(selectedIds.value)
}

const openCreateMother = () => {
  const defaultCfg = cloudMailConfigs.value.find(c => c.is_default) || cloudMailConfigs.value[0]
  motherForm.cloudmail_config_id = defaultCfg?.id || 0
  motherForm.domain = ''
  motherForm.seat_total = 4
  motherForm.count = 1
  motherForm.note = ''
  motherDialogVisible.value = true
}

const createMother = async () => {
  if (!motherForm.cloudmail_config_id) {
    ElMessage.warning('请先选择邮箱配置')
    return
  }
  creating.value = true
  try {
    const res = await gptBusinessApi.createMotherAccounts({
      cloudmail_config_id: motherForm.cloudmail_config_id,
      domain: motherForm.domain || undefined,
      seat_total: motherForm.seat_total,
      count: motherForm.count,
      note: motherForm.note || undefined
    })
    ElMessage.success(`已创建母号 x${res.created?.length || 0}`)
    motherDialogVisible.value = false
    await refresh()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '创建失败')
  } finally {
    creating.value = false
  }
}

const openCreateChild = (mother: MotherRow) => {
  activeMother.value = mother
  childForm.domain = ''
  childForm.count = 1
  childForm.note = ''
  childDialogVisible.value = true
}

const editSeat = async (mother: MotherRow) => {
  try {
    const ret = await ElMessageBox.prompt('请输入母号座位数（seat_total）', '修改座位', {
      confirmButtonText: '保存',
      cancelButtonText: '取消',
      inputValue: String(mother.seat_total || 0),
      inputPattern: /^\d+$/,
      inputErrorMessage: '请输入非负整数'
    })
    if (!ret?.value) return
    const value = ret.value
    await gptBusinessApi.updateAccount(mother.id, { seat_total: Number(value) })
    ElMessage.success('已更新')
    await refresh()
  } catch (e: any) {
    if (e === 'cancel' || e?.message === 'cancel') return
    ElMessage.error(e?.response?.data?.detail || e?.message || '更新失败')
  }
}

const createChild = async () => {
  if (!activeMother.value) return
  creating.value = true
  try {
    const res = await gptBusinessApi.createChildAccounts({
      parent_id: activeMother.value.id,
      cloudmail_config_id: activeMother.value.cloudmail_config_id || undefined,
      domain: childForm.domain || undefined,
      count: childForm.count,
      note: childForm.note || undefined
    })
    ElMessage.success(`已创建子号 x${res.created?.length || 0}`)
    childDialogVisible.value = false
    await refresh()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '创建失败')
  } finally {
    creating.value = false
  }
}

const copyText = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制')
  } catch {
    ElMessage.warning('复制失败（浏览器不支持剪贴板）')
  }
}


const removeAccount = async (accountId: string) => {
  try {
    await ElMessageBox.confirm('删除后不可恢复；删除母号会同时删除其子账号。确认删除？', '确认删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
    await gptBusinessApi.deleteAccount(accountId)
    ElMessage.success('已删除')
    await refresh()
  } catch (e: any) {
    if (e === 'cancel' || e?.message === 'cancel') return
    ElMessage.error(e?.response?.data?.detail || e?.message || '删除失败')
  }
}

const getGeekezActionLabel = (account: GptBusinessAccount) => {
  return account.geekez_profile_exists ? '打开' : '创建'
}

const getEnvStatusClass = (exists: boolean | undefined) => {
  if (exists) {
    return 'bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-400 dark:border-emerald-800'
  }
  return 'bg-slate-100 text-slate-500 border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700'
}

type StatusBadge = { key: string; text: string; class: string }

const getAccountStatusBadges = (account: any): StatusBadge[] => {
  const badges: StatusBadge[] = []

  const accountType = String(account?.type || '')
  const isChild = accountType === 'child'
  const isMother = accountType === 'mother'

  const registerStatus = String(account?.register_status || 'not_started')
  const loginStatus = String(account?.login_status || 'not_started')
  const teamJoinStatus = String(account?.team_join_status || 'not_started')
  const poolStatus = String(account?.pool_status || 'not_started')
  const teamStatus = String(account?.team_status || 'not_started')

  const push = (key: string, text: string, cls: string) => {
    badges.push({ key, text, class: cls })
  }

  const clsMap: Record<string, string> = {
    success: 'bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-400 dark:border-emerald-800',
    running: 'bg-sky-100 text-sky-700 border-sky-200 dark:bg-sky-900/30 dark:text-sky-400 dark:border-sky-800',
    failed: 'bg-rose-100 text-rose-700 border-rose-200 dark:bg-rose-900/30 dark:text-rose-400 dark:border-rose-800',
    not_started: 'bg-slate-100 text-slate-600 border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700'
  }

  const mapStatus = (prefix: string, status: string, label: string) => {
    push(prefix, label, clsMap[status] || clsMap.not_started)
  }

  // 顺序：创建(已在外部) -> 注册 -> 登录 -> 入队 -> 入池

  // 2. 注册状态
  mapStatus('register', registerStatus, '注册')

  // 3. 登录状态
  mapStatus('login', loginStatus, '登录')

  // 4. 入队状态（子号显示）
  if (isChild) {
    mapStatus('join', teamJoinStatus, '入队')
  }

  // 5. 入池状态（母号/子号都展示）
  mapStatus('pool', poolStatus, '入池')

  // 6. 母号：team 状态
  if (isMother) {
    mapStatus('team', teamStatus, 'Team')
  }

  return badges
}

const launchGeekez = async (account: GptBusinessAccount) => {
  try {
    const res = await gptBusinessApi.launchGeekez(account.id)
    if (res?.success) {
      const msg = res.created_profile ? '环境创建并打开成功' : '环境打开成功'
      ElMessage.success(msg)
      await refresh()
    } else {
      ElMessage.warning('启动失败')
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '启动失败')
  }
}




const tasksDrawerVisible = ref(false)
const tasksDrawerAccount = ref<MotherRow | null>(null)
type TaskRow = {
  id: string
  type?: string
  status?: string
  mother_id?: string
  created_at?: string
  error?: string
  source?: string
  celery_task_id?: string | number
}

type TaskArtifact = { name: string; download_url: string }

const accountTasks = ref<TaskRow[]>([])
const tasksLoading = ref(false)

const artifactsDialogVisible = ref(false)
const artifactsLoading = ref(false)
const currentTaskArtifacts = ref<TaskArtifact[]>([])

const taskLogDialogVisible = ref(false)
const taskLogLoading = ref(false)
const currentLogTask = ref<TaskRow | null>(null)
const currentLogFilename = ref('run.log')
const currentLogDownloadUrl = ref('')
const taskLogText = ref('')
const currentSteps = ref<Array<{ title: string; time: string }>>([])
const currentLogExtras = ref<string[]>([])
const activeStep = ref(0)
const currentAccountsSummary = ref<Array<{
  account_id: string
  email: string
  celery_task_id: string
  trace_file: string
  state: string
}>>([])

const showCeleryDialog = ref(false)
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
const traceUnavailable = ref(false)
const traceUnavailableNotified = ref(false)
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
  return parts.length ? parts.join('\n') : '暂无状态信息'
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
    if (traceUnavailable.value) return
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

const markTraceUnavailable = (message?: string) => {
  traceUnavailable.value = true
  stopTracePolling()
  if (!traceUnavailableNotified.value) {
    ElMessage.warning(message || 'trace 接口不可用')
    traceUnavailableNotified.value = true
  }
}

const refreshCeleryStatus = async () => {
  if (!celeryTaskId.value) return
  celeryStatusLoading.value = true
  try {
    const res = await gptBusinessApi.getCeleryTask(celeryTaskId.value)
    celeryState.value = res?.state || ''
    celeryMeta.value = res?.meta || null
    celeryResult.value = res?.result || null
    celeryError.value = res?.error || ''
    celeryTraceback.value = res?.traceback || ''
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '查询任务状态失败')
  } finally {
    celeryStatusLoading.value = false
  }
}

const normalizeTraceLines = (raw: string[]): TraceLine[] => {
  const result = _normalizeTraceLines(raw, traceLineSeq)
  traceLineSeq = result.nextId
  return result.lines
}

const fetchTraceBackward = async (opts?: { initial?: boolean }) => {
  if (!celeryTaskId.value || traceUnavailable.value) return
  if (traceLoadingOlder.value) return
  traceLoadingOlder.value = true

  const initial = Boolean(opts?.initial)
  const scrollEl = traceScrollRef.value
  const prevHeight = scrollEl?.scrollHeight || 0
  const prevTop = scrollEl?.scrollTop || 0

  try {
    const params: any = {
      direction: 'backward',
      limit_bytes: 262144
    }
    if (celeryEmail.value) params.email = celeryEmail.value
    if (!initial && traceCursorBackward.value !== null) {
      params.cursor = traceCursorBackward.value
    }

    const res = await gptBusinessApi.trace(celeryTaskId.value, params)
    traceFile.value = res?.trace_file || traceFile.value
    traceSize.value = typeof res?.size === 'number' ? res.size : traceSize.value
    traceHasMoreBackward.value = Boolean(res?.has_more)
    traceCursorBackward.value = typeof res?.cursor_out === 'number' ? res.cursor_out : traceCursorBackward.value

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
  } catch (e: any) {
    markTraceUnavailable(e?.response?.data?.detail || e?.message || '读取 trace 日志失败')
  } finally {
    traceLoadingOlder.value = false
  }
}

const fetchTraceForward = async () => {
  if (!celeryTaskId.value || traceUnavailable.value) return
  const cursor = traceCursorForward.value
  const params: any = {
    direction: 'forward',
    limit_bytes: 262144
  }
  if (celeryEmail.value) params.email = celeryEmail.value
  if (typeof cursor === 'number') params.cursor = cursor

  try {
    const res = await gptBusinessApi.trace(celeryTaskId.value, params)
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
    markTraceUnavailable('读取 trace 日志失败')
  }
}

const onTraceScroll = async () => {
  const el = traceScrollRef.value
  if (!el) return

  if (el.scrollTop <= 0 && traceHasMoreBackward.value) {
    await fetchTraceBackward({ initial: false })
  }

  const distanceToBottom = el.scrollHeight - (el.scrollTop + el.clientHeight)
  if (distanceToBottom > 80 && traceFollowLatest.value) {
    traceFollowLatest.value = false
  }
}

const reloadTrace = async () => {
  traceLines.value = []
  traceHasMoreBackward.value = false
  traceCursorBackward.value = null
  traceCursorForward.value = null
  traceFile.value = ''
  traceSize.value = 0
  traceLineSeq = 0
  traceUnavailable.value = false
  traceUnavailableNotified.value = false
  await fetchTraceBackward({ initial: true })
}

const openCeleryTask = async (taskId: string) => {
  if (!taskId) return
  stopTracePolling()

  celeryTaskId.value = taskId
  celeryEmail.value = String(tasksDrawerAccount.value?.email || '').trim()
  celeryState.value = ''
  celeryMeta.value = null
  celeryResult.value = null
  celeryError.value = ''
  celeryTraceback.value = ''
  traceUnavailable.value = false
  traceUnavailableNotified.value = false

  showCeleryDialog.value = true
  await refreshCeleryStatus()
  await reloadTrace()
  startTracePolling()
}

const onCeleryDialogClosed = () => {
  stopTracePolling()
}

const getFallbackSteps = (taskType?: string) => {
  const map: Record<string, string[]> = {
    self_register: ['创建账号', '初始化环境', '完成处理'],
    auto_invite: ['准备邀请', '邀请并入池', '完成处理'],
    sub2api_sink: ['准备入池', '推送任务', '完成处理']
  }
  return map[taskType || ''] || ['任务开始', '执行中', '任务完成']
}

const parseLogDetails = (logStr: string, taskType?: string) => {
  const stepRegex = /步骤\s*(\d+)\s*\/\s*(\d+)\s*:\s*(.*)/g
  const extraRegex = /增项:\s*(.*)/g
  const stepsMap = new Map<number, string>()
  let maxStep = 0
  let totalSteps = 0
  let match

  while ((match = stepRegex.exec(logStr)) !== null) {
    const stepNum = Number(match[1])
    const total = Number(match[2])
    const title = String(match[3] || '').trim()
    if (Number.isFinite(stepNum)) {
      maxStep = Math.max(maxStep, stepNum)
      if (title) stepsMap.set(stepNum, title)
    }
    if (Number.isFinite(total)) {
      totalSteps = Math.max(totalSteps, total)
    }
  }

  if (!totalSteps) totalSteps = maxStep

  const steps: Array<{ title: string; time: string }> = []
  if (totalSteps > 0) {
    for (let i = 1; i <= totalSteps; i += 1) {
      steps.push({ title: stepsMap.get(i) || `步骤 ${i}`, time: '' })
    }
  } else if (stepsMap.size > 0) {
    const sorted = Array.from(stepsMap.entries()).sort((a, b) => a[0] - b[0])
    for (const [, title] of sorted) {
      steps.push({ title: title || '步骤', time: '' })
    }
  }

  if (steps.length === 0) {
    const fallback = getFallbackSteps(taskType)
    fallback.forEach(title => steps.push({ title, time: '' }))
  }

  const extras: string[] = []
  while ((match = extraRegex.exec(logStr)) !== null) {
    const text = String(match[1] || '').trim()
    if (text && !extras.includes(text)) extras.push(text)
  }

  const active = steps.length > 0 ? Math.min(Math.max(maxStep - 1, 0), steps.length - 1) : 0
  return { steps, extras, active }
}

const viewTasks = async (mother: MotherRow) => {
  tasksDrawerAccount.value = mother
  tasksDrawerVisible.value = true
  tasksLoading.value = true
  try {
    const res = await gptBusinessApi.getAccountTasks(mother.id)
    const allTasks: TaskRow[] = (res?.tasks || []) as TaskRow[]
    accountTasks.value = allTasks
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '获取任务失败')
    accountTasks.value = []
  } finally {
    tasksLoading.value = false
  }
}

const clearTaskRecords = async () => {
  if (!tasksDrawerAccount.value) return
  const mother = tasksDrawerAccount.value
  try {
    await ElMessageBox.confirm(
      '确定清空该母号的历史任务记录吗？（会删除已完成/失败/取消的记录，运行中任务会保留）',
      '清空记录',
      {
        type: 'warning',
        confirmButtonText: '清空',
        cancelButtonText: '取消'
      }
    )
    const res = await gptBusinessApi.clearAccountTasks(mother.id)
    ElMessage.success(`已清空 ${res?.removed ?? 0} 条记录`)
    await viewTasks(mother)
  } catch (e: any) {
    if (e === 'cancel' || e?.message === 'cancel') return
    ElMessage.error(e?.response?.data?.detail || e?.response?.data?.error || e?.message || '清空记录失败')
  }
}

const viewTaskArtifacts = async (task: TaskRow) => {
  if (!task?.id) return
  artifactsDialogVisible.value = true
  artifactsLoading.value = true
  currentTaskArtifacts.value = []
  try {
    const artifacts = await gptBusinessApi.getTaskArtifacts(task.id)
    currentTaskArtifacts.value = artifacts || []
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '获取产物失败')
    currentTaskArtifacts.value = []
  } finally {
    artifactsLoading.value = false
  }
}

const loadTaskLog = async (task: TaskRow) => {
  if (!task?.id) return
  taskLogLoading.value = true
  currentLogTask.value = task
  taskLogText.value = ''
  currentLogFilename.value = 'run.log'
  currentLogDownloadUrl.value = ''
  currentSteps.value = []
  currentLogExtras.value = []
  activeStep.value = 0
  currentAccountsSummary.value = []
  try {
    const res = await gptBusinessApi.getTaskLog(task.id, { tail: 2000 })
    currentLogFilename.value = res?.filename || 'run.log'
    currentLogDownloadUrl.value = res?.download_url || ''
    const logStr = res?.text || ''
    taskLogText.value = cleanLogText(logStr)
    currentAccountsSummary.value = Array.isArray(res?.accounts_summary) ? res.accounts_summary : []
    const parsed = parseLogDetails(logStr, task.type)
    currentSteps.value = parsed.steps
    currentLogExtras.value = parsed.extras
    activeStep.value = parsed.active
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '获取日志失败')
    taskLogText.value = ''
    currentLogDownloadUrl.value = ''
    currentSteps.value = []
    currentLogExtras.value = []
    activeStep.value = 0
    currentAccountsSummary.value = []
  } finally {
    taskLogLoading.value = false
  }
}

const viewTaskLog = async (task: TaskRow) => {
  if (!task?.id) return
  taskLogDialogVisible.value = true
  await loadTaskLog(task)
}

const cancelTask = async (taskId: string) => {
  try {
    await gptBusinessApi.cancelTask(taskId)
    ElMessage.success('任务已中断')
    if (tasksDrawerAccount.value) {
      await viewTasks(tasksDrawerAccount.value)
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '中断任务失败')
  }
}

const reloadTaskLog = async () => {
  if (!currentLogTask.value) return
  await loadTaskLog(currentLogTask.value)
}

const getTaskTypeName = (type: string) => {
  const map: Record<string, string> = {
    self_register: '自动开通',
    auto_invite: '自动邀请并入池',
    sub2api_sink: '自动入池'
  }
  return map[type] || type
}

const getStatusTag = (status: string) => {
  const map: Record<string, string> = {
    success: 'success',
    failed: 'danger',
    running: 'primary',
    pending: 'info'
  }
  return map[status] || 'info'
}

// 事件处理函数
const handleRefresh = () => refresh()
const handleOpenCreateMother = () => openCreateMother()
const handleOpenCreateChild = (e: Event) => {
  const mother = (e as CustomEvent).detail
  if (mother) openCreateChild(mother)
}
const handleViewTasks = (e: Event) => {
  const mother = (e as CustomEvent).detail
  if (mother) viewTasks(mother)
}

const handleOpenSub2apiSink = (e: Event) => {
  const detail = (e as CustomEvent).detail || {}
  const ids = Array.isArray(detail.mother_ids) ? detail.mother_ids : []
  const action: 'pool_only' | 'invite_and_pool' = detail.action === 'invite_and_pool' ? 'invite_and_pool' : 'pool_only'
  if (ids.length > 0) {
    openSub2apiSinkDialog(ids, action)
    return
  }
  if (selectedMother.value?.id) {
    openSub2apiSinkDialog([selectedMother.value.id], action)
  }
}

// 快捷键支持
const handleKeydown = (e: KeyboardEvent) => {
  // 忽略输入框内的按键
  if ((e.target as HTMLElement).tagName === 'INPUT' || (e.target as HTMLElement).tagName === 'TEXTAREA') {
    return
  }

  const currentIndex = filteredMothers.value.findIndex((m: any) => m.id === selectedMother.value?.id)
  
  switch (e.key) {
    case 'ArrowUp':
      e.preventDefault()
      if (currentIndex > 0) {
        onCurrentChange(filteredMothers.value[currentIndex - 1])
      } else if (currentIndex === -1 && filteredMothers.value.length > 0) {
        onCurrentChange(filteredMothers.value[0])
      }
      break
    case 'ArrowDown':
      e.preventDefault()
      if (currentIndex < filteredMothers.value.length - 1) {
        onCurrentChange(filteredMothers.value[currentIndex + 1])
      } else if (currentIndex === -1 && filteredMothers.value.length > 0) {
        onCurrentChange(filteredMothers.value[0])
      }
      break
    case 'Enter':
      if (selectedMother.value) {
        e.preventDefault()
        launchGeekez(selectedMother.value)
      }
      break
    case 'Delete':
    case 'Backspace':
      if (selectedMother.value && e.metaKey) {
        e.preventDefault()
        removeAccount(selectedMother.value.id)
      }
      break
    case 'Escape':
      selectedMother.value = null
      selectedIds.value.clear()
      selectedIds.value = new Set(selectedIds.value)
      break
  }
}

onMounted(() => {
  refresh()
  
  // 监听父组件发出的事件
  window.addEventListener('gpt-accounts-refresh', handleRefresh)
  window.addEventListener('gpt-open-create-mother', handleOpenCreateMother)
  window.addEventListener('gpt-open-create-child', handleOpenCreateChild)
  window.addEventListener('gpt-view-tasks', handleViewTasks)
  window.addEventListener('gpt-open-sub2api-sink', handleOpenSub2apiSink)
  window.addEventListener('gpt-selection-clear', onSelectionClear)
  
  // 快捷键支持
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  // 清理事件监听
  window.removeEventListener('gpt-accounts-refresh', handleRefresh)
  window.removeEventListener('gpt-open-create-mother', handleOpenCreateMother)
  window.removeEventListener('gpt-open-create-child', handleOpenCreateChild)
  window.removeEventListener('gpt-view-tasks', handleViewTasks)
  window.removeEventListener('gpt-open-sub2api-sink', handleOpenSub2apiSink)
  window.removeEventListener('gpt-selection-clear', onSelectionClear)
  window.removeEventListener('keydown', handleKeydown)
  stopTracePolling()
})
</script>
