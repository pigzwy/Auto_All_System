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

      <!-- 批量操作 -->
      <div v-if="hasSelection" class="flex items-center gap-2 rounded-lg border border-primary/30 bg-primary/5 px-3 py-1.5">
        <span class="text-sm font-medium text-primary">已选 {{ selectedIds.size }} 项</span>
        <div class="h-4 w-px bg-primary/30" />
        <Button size="xs" class="gap-1 bg-emerald-600 hover:bg-emerald-700 text-white" @click="batchRunSelfRegister">
          <UserPlus class="h-3.5 w-3.5" /> 批量开通
        </Button>
        <Button size="xs" class="gap-1 bg-blue-600 hover:bg-blue-700 text-white" @click="batchRunAutoInvite">
          <ArrowRightToLine class="h-3.5 w-3.5" /> 批量邀请
        </Button>
        <Button size="xs" class="gap-1 bg-violet-600 hover:bg-violet-700 text-white" @click="batchRunSub2apiSink">
          <LayoutList class="h-3.5 w-3.5" /> 批量入池
        </Button>
        <button class="ml-1 rounded p-1 hover:bg-primary/20" @click="selectedIds.clear(); selectedIds = new Set(selectedIds)">
          <X class="h-3.5 w-3.5 text-primary/70" />
        </button>
      </div>

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
                  <Checkbox 
                    :checked="isAllSelected" 
                    :indeterminate="hasSelection && !isAllSelected"
                    @update:checked="toggleSelectAll" 
                  />
                </TableHead>
                <TableHead class="w-10"></TableHead>
                <TableHead class="min-w-[220px]">母号邮箱</TableHead>
                <TableHead class="min-w-[180px]">账号密码</TableHead>
                <TableHead class="min-w-[180px]">邮箱密码</TableHead>
                <TableHead class="w-24">座位</TableHead>
                <TableHead class="min-w-[120px]">备注</TableHead>
                <TableHead class="w-28">环境</TableHead>
                <TableHead class="w-40">创建时间</TableHead>
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
                    selectedMotherId === mother.id 
                      ? 'bg-primary/10 hover:bg-primary/15 border-l-2 border-l-primary' 
                      : index % 2 === 0 ? 'bg-background hover:bg-muted/50' : 'bg-muted/20 hover:bg-muted/50'
                  ]"
                  @click="onCurrentChange(mother)"
                >
                  <TableCell @click.stop>
                    <Checkbox 
                      :checked="selectedIds.has(mother.id)" 
                      @update:checked="toggleSelect(mother.id)" 
                    />
                  </TableCell>
                  <TableCell>
                    <Button variant="ghost" size="xs" class="h-6 w-6 p-0" @click.stop="toggleExpand(mother.id)">
                      <LayoutList class="h-4 w-4 transition-transform" :class="{ 'rotate-90': expandedRows.has(mother.id) }" />
                    </Button>
                  </TableCell>
                  <TableCell class="font-medium">{{ mother.email }}</TableCell>
                  <TableCell>
                    <div class="flex items-center gap-2">
                      <code class="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">{{ mother.account_password || '-' }}</code>
                      <Button v-if="mother.account_password" variant="ghost" size="xs" class="h-6 w-6" @click.stop="copyAccountPassword(mother)">
                        <Copy class="h-3 w-3" />
                      </Button>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div class="flex items-center gap-2">
                      <code class="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">{{ mother.email_password || '-' }}</code>
                      <Button v-if="mother.email_password" variant="ghost" size="xs" class="h-6 w-6" @click.stop="copyEmailPassword(mother)">
                        <Copy class="h-3 w-3" />
                      </Button>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" class="font-mono">
                      {{ mother.seat_used || 0 }}/{{ mother.seat_total || 0 }}
                    </Badge>
                  </TableCell>
                  <TableCell class="text-muted-foreground text-xs truncate max-w-[120px]">{{ mother.note }}</TableCell>
                  <TableCell>
                    <div class="flex flex-col gap-1">
                      <div class="flex items-center gap-2">
                        <Badge 
                          :class="mother.geekez_profile_exists 
                            ? 'bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-400 dark:border-emerald-800' 
                            : 'bg-slate-100 text-slate-500 border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700'"
                          variant="outline" 
                          class="text-xs"
                        >
                          {{ mother.geekez_profile_exists ? '✓ 已创建' : '○ 未创建' }}
                        </Badge>
                        <Badge v-if="mother.geekez_env" class="bg-sky-100 text-sky-700 border-sky-200 dark:bg-sky-900/30 dark:text-sky-400 dark:border-sky-800 text-xs font-mono" variant="outline">
                          :{{ mother.geekez_env.debug_port || '' }}
                        </Badge>
                      </div>
                      <div class="flex flex-wrap gap-1">
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
                    </div>
                  </TableCell>
                  <TableCell class="text-muted-foreground text-xs">{{ formatDate(mother.created_at) }}</TableCell>
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
                              <TableHead>账号密码</TableHead>
                              <TableHead>邮箱密码</TableHead>
                              <TableHead>备注</TableHead>
                              <TableHead>环境</TableHead>
                              <TableHead>创建时间</TableHead>
                              <TableHead class="text-right">操作</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            <TableRow v-for="child in mother.children || []" :key="child.id">
                              <TableCell>{{ child.email }}</TableCell>
                              <TableCell>
                                <div class="flex items-center gap-2">
                                  <code class="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">{{ child.account_password || '-' }}</code>
                                  <Button v-if="child.account_password" variant="ghost" size="xs" class="h-6 w-6" @click.stop="copyAccountPassword(child)">
                                    <Copy class="h-3 w-3" />
                                  </Button>
                                </div>
                              </TableCell>
                              <TableCell>
                                <div class="flex items-center gap-2">
                                  <code class="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">{{ child.email_password || '-' }}</code>
                                  <Button v-if="child.email_password" variant="ghost" size="xs" class="h-6 w-6" @click.stop="copyEmailPassword(child)">
                                    <Copy class="h-3 w-3" />
                                  </Button>
                                </div>
                              </TableCell>
                              <TableCell class="text-muted-foreground text-xs">{{ child.note }}</TableCell>
                              <TableCell>
                                <div class="flex flex-col gap-1">
                                  <div class="flex items-center gap-1">
                                    <Badge 
                                      :class="child.geekez_profile_exists 
                                        ? 'bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-400 dark:border-emerald-800' 
                                        : 'bg-slate-100 text-slate-500 border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700'"
                                      variant="outline"
                                      class="text-xs"
                                    >
                                      {{ child.geekez_profile_exists ? '✓ 已创建' : '○ 未创建' }}
                                    </Badge>
                                    <Badge v-if="child.geekez_env" class="bg-sky-100 text-sky-700 border-sky-200 dark:bg-sky-900/30 dark:text-sky-400 dark:border-sky-800 text-xs font-mono" variant="outline">
                                      :{{ child.geekez_env.debug_port || '' }}
                                    </Badge>
                                  </div>
                                  <div class="flex flex-wrap gap-1">
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
                                </div>
                              </TableCell>
                              <TableCell class="text-muted-foreground text-xs">{{ formatDate(child.created_at) }}</TableCell>
                              <TableCell class="text-right">
                                <div class="flex items-center justify-end gap-1">
                                  <Button variant="ghost" size="xs" @click.stop="launchGeekez(child)">
                                    {{ getGeekezActionLabel(child) }}
                                  </Button>
                                  <Button variant="ghost" size="xs" @click.stop="copyFull(child)">复制</Button>
                                  <Button variant="ghost" size="xs" class="text-destructive hover:text-destructive" @click.stop="removeAccount(child.id)">删除</Button>
                                </div>
                              </TableCell>
                            </TableRow>
                            <TableRow v-if="!mother.children?.length">
                              <TableCell colspan="7" class="text-center text-xs text-muted-foreground py-4">无子账号</TableCell>
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
            <Select v-model="motherForm.domain">
              <SelectTrigger>
                <SelectValue placeholder="留空=随机" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">随机</SelectItem>
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
          <DialogDescription>为 {{ selectedMother?.email }} 生成子号</DialogDescription>
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
          <Button variant="outline" @click="childDialogVisible = false">取消</Button>
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
          <DialogTitle>自动入池配置</DialogTitle>
          <DialogDescription>
            保存配置后先测试连接，通过后再开始执行（当前将对 {{ sub2apiMotherIds.length }} 个母号生效）
          </DialogDescription>
        </DialogHeader>
          <div class="grid gap-4 py-4">
          <div class="rounded-lg border border-border bg-muted/30 p-3">
            <div class="text-sm font-medium">来源</div>
            <div v-if="poolMode === 'crs_sync'" class="mt-1 text-xs text-muted-foreground">从 CRS 拉取 OpenAI OAuth 凭据，然后写入 Sub2API。</div>
            <div v-else class="mt-1 text-xs text-muted-foreground">不依赖 CRS，直接通过 Sub2API OpenAI OAuth 自动授权入池。</div>
            <div class="mt-3 grid gap-2">
              <label class="text-sm font-medium">入池模式</label>
              <Select v-model="poolMode">
                <SelectTrigger>
                  <SelectValue placeholder="请选择" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="crs_sync">CRS 同步入池（推荐）</SelectItem>
                  <SelectItem value="s2a_oauth">S2A OAuth 入池（不依赖 CRS）</SelectItem>
                </SelectContent>
              </Select>
              <div class="text-xs text-muted-foreground">选择 S2A OAuth 时，将直接调用 Sub2API 的 OpenAI OAuth 接口生成授权 URL 并自动授权入池。</div>
            </div>

            <template v-if="poolMode === 'crs_sync'">
              <div class="mt-3 text-xs text-muted-foreground font-mono"># [crs] api_base = "..."  admin_token = "..."</div>
              <div class="mt-3 grid gap-2">
                <label class="text-sm font-medium">CRS API Base</label>
                <Input v-model="crsForm.api_base" placeholder="https://crs.example.com" />
              </div>
              <div class="mt-3 grid gap-2">
                <label class="text-sm font-medium">CRS Admin Token</label>
                <Input v-model="crsForm.admin_token" type="password" placeholder="留空表示不修改" />
                <div v-if="crsHint.admin_token_masked" class="text-xs text-muted-foreground">已保存：{{ crsHint.admin_token_masked }}</div>
              </div>
            </template>
          </div>

          <div class="rounded-lg border border-border bg-muted/30 p-3">
            <div class="text-sm font-medium">Sub2API（目标）</div>
            <div class="mt-1 text-xs text-muted-foreground">选择入到哪里，保存配置后测试连接，通过后再开始。</div>

          <div class="grid gap-2">
            <label class="text-sm font-medium">入到哪里</label>
            <Select v-model="sub2apiTargetKey">
              <SelectTrigger>
                <SelectValue placeholder="请选择" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="t in sub2apiTargets" :key="t.key" :value="t.key">
                  {{ t.label || t.key }}
                </SelectItem>
              </SelectContent>
            </Select>
            <div class="flex items-center gap-2">
              <Button size="xs" variant="outline" @click="addS2aTarget">新增目标</Button>
              <Button size="xs" variant="outline" :disabled="sub2apiTargets.length <= 1" @click="removeS2aTarget">删除当前</Button>
            </div>
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium">目标名称</label>
            <Input :model-value="getCurrentS2aTargetLabel()" @update:modelValue="(v) => setCurrentS2aTargetLabel(String(v))" placeholder="例如：sub2（生产）" />
            <div class="text-xs text-muted-foreground">仅用于展示，不影响后端逻辑（后端按 key 匹配）。</div>
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium">S2A API Base</label>
            <Input v-model="sub2apiForm.api_base" placeholder="https://sub2.pigll.site/api/v1" />
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium">Admin API Key (推荐)</label>
            <Input v-model="sub2apiForm.admin_key" type="password" placeholder="留空表示不修改" />
            <div v-if="sub2apiHint.admin_key_masked" class="text-xs text-muted-foreground">已保存：{{ sub2apiHint.admin_key_masked }}</div>
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium">JWT Token (备选)</label>
            <Input v-model="sub2apiForm.admin_token" type="password" placeholder="留空表示不修改" />
            <div v-if="sub2apiHint.admin_token_masked" class="text-xs text-muted-foreground">已保存：{{ sub2apiHint.admin_token_masked }}</div>
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

          <div class="text-xs text-muted-foreground">流程：保存 → 测试连接 → 开始入池</div>
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
            开始入池
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Tasks Sheet -->
    <Sheet v-model:open="tasksDrawerVisible">
      <SheetContent side="right" class="w-full sm:max-w-[800px]">
        <SheetHeader>
          <SheetTitle>任务日志</SheetTitle>
          <SheetDescription>账号：{{ tasksDrawerAccount?.email }}</SheetDescription>
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
                      <Button variant="ghost" size="xs" @click="viewTaskLog(task)">日志</Button>
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
    <Dialog v-model:open="artifactsDialogVisible">
      <DialogContent class="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>任务产物</DialogTitle>
        </DialogHeader>
        <div class="py-2">
          <div v-if="artifactsLoading" class="py-4 text-center">
            <Loader2 class="mx-auto h-5 w-5 animate-spin text-muted-foreground" />
          </div>
          <Table v-else>
            <TableHeader>
              <TableRow>
                <TableHead>文件</TableHead>
                <TableHead class="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="art in currentTaskArtifacts" :key="art.name">
                <TableCell class="font-mono text-xs">{{ art.name }}</TableCell>
                <TableCell class="text-right">
                  <a :href="art.download_url" target="_blank" class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 text-primary underline-offset-4 hover:underline h-9 px-3">
                    <FileDown class="mr-2 h-4 w-4" /> 下载
                  </a>
                </TableCell>
              </TableRow>
              <TableRow v-if="currentTaskArtifacts.length === 0">
                <TableCell colspan="2" class="py-4 text-center text-sm text-muted-foreground">无产物</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      </DialogContent>
    </Dialog>

    <!-- Log Dialog -->
    <Dialog v-model:open="taskLogDialogVisible">
      <DialogContent class="sm:max-w-[900px]">
        <DialogHeader>
          <DialogTitle>任务日志</DialogTitle>
          <DialogDescription v-if="currentLogTask">Task ID: {{ currentLogTask.id }}</DialogDescription>
        </DialogHeader>
        <div class="py-2">
          <div class="mb-2 flex items-center justify-between">
            <span class="text-xs text-muted-foreground">{{ currentLogFilename }}</span>
            <div class="flex gap-2">
              <a v-if="currentLogDownloadUrl" :href="currentLogDownloadUrl" target="_blank" class="text-xs text-primary hover:underline">下载日志</a>
              <button class="text-xs text-primary hover:underline" @click="reloadTaskLog">刷新</button>
            </div>
          </div>
          <textarea
            v-if="!taskLogLoading"
            class="h-[400px] w-full rounded-md border border-input bg-muted/50 p-4 font-mono text-xs text-foreground focus-visible:outline-none"
            readonly
            :value="taskLogText || '暂无日志内容'"
          ></textarea>
          <div v-else class="flex h-[400px] items-center justify-center">
            <Loader2 class="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        </div>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, inject, onMounted, onUnmounted, provide, reactive, ref, watch, type Ref } from 'vue'
import { ElMessage, ElMessageBox } from '@/lib/element'
import {
  Armchair,
  Copy,
  Loader2,
  Monitor,
  Plus,
  Search,
  UserPlus,
  Users,
  ArrowRightToLine,
  LayoutList,
  FileDown,
  X
} from 'lucide-vue-next'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import {
  Dialog,
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

import { getCloudMailConfigs, type CloudMailConfig } from '@/api/email'
import type { GptBusinessAccount, GptBusinessAccountsResponse } from '@/api/gpt_business'
import { gptBusinessApi } from '@/api/gpt_business'

type MotherRow = GptBusinessAccountsResponse['mothers'][number]

// 从父组件注入状态
const selectedMother = inject<Ref<GptBusinessAccount | null>>('selectedMother')!
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
const isAllSelected = computed(() => 
  filteredMothers.value.length > 0 && 
  filteredMothers.value.every((m: any) => selectedIds.value.has(m.id))
)
const hasSelection = computed(() => selectedIds.value.size > 0)

const toggleSelectAll = () => {
  if (isAllSelected.value) {
    selectedIds.value.clear()
  } else {
    filteredMothers.value.forEach((m: any) => selectedIds.value.add(m.id))
  }
  selectedIds.value = new Set(selectedIds.value) // 触发响应式
}

const toggleSelect = (id: string) => {
  if (selectedIds.value.has(id)) {
    selectedIds.value.delete(id)
  } else {
    selectedIds.value.add(id)
  }
  selectedIds.value = new Set(selectedIds.value) // 触发响应式
}

// 批量操作
const batchRunSelfRegister = async () => {
  if (selectedIds.value.size === 0) return
  const ids = Array.from(selectedIds.value)
  try {
    await Promise.all(ids.map(id => gptBusinessApi.selfRegister(id)))
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
  try {
    await Promise.all(ids.map(id => gptBusinessApi.autoInvite(id)))
    ElMessage.success(`已启动 ${ids.length} 个母号的自动邀请`)
    selectedIds.value.clear()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '批量操作失败')
  }
}

type S2aTarget = {
  key: string
  label?: string
  config: any
}

const sub2apiDialogVisible = ref(false)
const sub2apiMotherIds = ref<string[]>([])
const sub2apiTargets = ref<S2aTarget[]>([])
const sub2apiTargetKey = ref('sub2')

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

const poolMode = ref<'crs_sync' | 's2a_oauth'>('crs_sync')

const _splitCsv = (raw: string) => {
  return String(raw || '')
    .split(/[,\s]+/)
    .map(s => s.trim())
    .filter(Boolean)
}

const applyS2aTargetToForm = () => {
  const t = sub2apiTargets.value.find(x => x.key === sub2apiTargetKey.value) || sub2apiTargets.value[0]
  const cfg = t?.config || {}

  sub2apiForm.api_base = String(cfg.api_base || '')
  sub2apiForm.concurrency = Number(cfg.concurrency || 5)
  sub2apiForm.priority = Number(cfg.priority || 50)
  sub2apiForm.group_ids = Array.isArray(cfg.group_ids) ? cfg.group_ids.join(',') : ''
  sub2apiForm.group_names = Array.isArray(cfg.group_names) ? cfg.group_names.join(',') : ''

  // secrets are masked by backend; do not prefill to avoid overwriting
  sub2apiHint.admin_key_masked = String(cfg.admin_key || '')
  sub2apiHint.admin_token_masked = String(cfg.admin_token || '')
  sub2apiForm.admin_key = ''
  sub2apiForm.admin_token = ''

  sub2apiTestOk.value = false
  sub2apiTestMessage.value = ''
}

const getCurrentS2aTargetLabel = () => {
  const t = sub2apiTargets.value.find(x => x.key === sub2apiTargetKey.value)
  return String(t?.label || t?.key || '')
}

const setCurrentS2aTargetLabel = (label: string) => {
  const next = String(label || '').trim()
  sub2apiTargets.value = sub2apiTargets.value.map(t => {
    if (t.key !== sub2apiTargetKey.value) return t
    return { ...t, label: next }
  })
}

const addS2aTarget = async () => {
  try {
    const { value } = await ElMessageBox.prompt('请输入目标 Key（用于匹配/传参）', '新增入池目标', {
      confirmButtonText: '下一步',
      cancelButtonText: '取消',
      inputValue: '',
      inputPattern: /^[a-zA-Z0-9_-]{2,32}$/,
      inputErrorMessage: 'Key 仅允许字母/数字/_/-，长度 2-32'
    })
    const key = String(value || '').trim()
    if (!key) return
    if (sub2apiTargets.value.some(t => t.key === key)) {
      ElMessage.warning('该 Key 已存在')
      return
    }

    let label = key
    try {
      const res = await ElMessageBox.prompt('请输入显示名称（可选）', '新增入池目标', {
        confirmButtonText: '确定',
        cancelButtonText: '跳过',
        inputValue: key
      })
      label = String(res.value || '').trim() || key
    } catch {
      label = key
    }

    const groupIds = _splitCsv(sub2apiForm.group_ids)
      .filter(x => /^\d+$/.test(x))
      .map(x => Number(x))
    const groupNames = _splitCsv(sub2apiForm.group_names)

    const newTarget: S2aTarget = {
      key,
      label,
      config: {
        api_base: '',
        concurrency: Number(sub2apiForm.concurrency || 5),
        priority: Number(sub2apiForm.priority || 50),
        group_ids: groupIds,
        group_names: groupNames
      }
    }

    sub2apiTargets.value = [...sub2apiTargets.value, newTarget]
    sub2apiTargetKey.value = key
    applyS2aTargetToForm()
    ElMessage.success('已新增目标（记得保存配置）')
  } catch {
    return
  }
}

const removeS2aTarget = async () => {
  if (sub2apiTargets.value.length <= 1) {
    ElMessage.warning('至少保留一个目标')
    return
  }
  const key = sub2apiTargetKey.value
  const target = sub2apiTargets.value.find(t => t.key === key)
  const label = target?.label || key
  try {
    await ElMessageBox.confirm(`确定删除目标：${label}（${key}）？`, '删除目标', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }

  const nextTargets = sub2apiTargets.value.filter(t => t.key !== key)
  sub2apiTargets.value = nextTargets
  sub2apiTargetKey.value = nextTargets[0]?.key || 'sub2'
  applyS2aTargetToForm()
  ElMessage.success('已删除目标（记得保存配置）')
}

watch(sub2apiTargetKey, () => {
  applyS2aTargetToForm()
})

const loadS2aTargetsFromSettings = async () => {
  const settings = await gptBusinessApi.getSettings()

  const crsCfg = settings?.crs || {}
  crsForm.api_base = String(crsCfg.api_base || '')
  crsHint.admin_token_masked = String(crsCfg.admin_token || '')
  crsForm.admin_token = ''

  const rawTargets = Array.isArray(settings?.s2a_targets) ? settings.s2a_targets : []
  const rawDefaultKey = String(settings?.s2a_default_target || '').trim()

  let targets: S2aTarget[] = []
  if (rawTargets.length > 0) {
    targets = rawTargets
      .filter((t: any) => t && typeof t === 'object')
      .map((t: any) => ({
        key: String(t.key || '').trim() || 'sub2',
        label: String(t.label || '').trim(),
        config: t.config || {}
      }))
  } else {
    targets = [{
      key: 'sub2',
      label: 'sub2',
      config: settings?.s2a || {}
    }]
  }

  sub2apiTargets.value = targets
  sub2apiTargetKey.value = rawDefaultKey || targets[0]?.key || 'sub2'
  applyS2aTargetToForm()
}

const saveCrsConfig = async () => {
  const payload: any = {
    crs: {
      api_base: crsForm.api_base
    }
  }
  if (String(crsForm.admin_token || '').trim()) {
    payload.crs.admin_token = String(crsForm.admin_token || '').trim()
  }

  await gptBusinessApi.updateSettings(payload)
}

const openSub2apiSinkDialog = async (motherIds: string[]) => {
  sub2apiMotherIds.value = motherIds
  try {
    await loadS2aTargetsFromSettings()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '读取入池配置失败')
  }
  sub2apiDialogVisible.value = true
}

const saveS2aTargetConfig = async () => {
  sub2apiSaving.value = true
  try {
    // 保存按钮：CRS 同步模式下也一起保存 CRS（避免用户只点“保存”但 CRS 没落库）
    if (poolMode.value === 'crs_sync') {
      await saveCrsConfig()
    }

    const groupIds = _splitCsv(sub2apiForm.group_ids)
      .filter(x => /^\d+$/.test(x))
      .map(x => Number(x))
    const groupNames = _splitCsv(sub2apiForm.group_names)

    const cfg: any = {
      api_base: sub2apiForm.api_base,
      concurrency: Number(sub2apiForm.concurrency || 5),
      priority: Number(sub2apiForm.priority || 50),
      group_ids: groupIds,
      group_names: groupNames
    }
    if (sub2apiForm.admin_key.trim()) cfg.admin_key = sub2apiForm.admin_key.trim()
    if (sub2apiForm.admin_token.trim()) cfg.admin_token = sub2apiForm.admin_token.trim()

    const nextTargets = sub2apiTargets.value.map(t => {
      if (t.key !== sub2apiTargetKey.value) return t
      return {
        ...t,
        config: {
          ...(t.config || {}),
          ...cfg
        }
      }
    })

    await gptBusinessApi.updateSettings({
      s2a_targets: nextTargets,
      s2a_default_target: sub2apiTargetKey.value
    })
    ElMessage.success('已保存入池配置')
    await loadS2aTargetsFromSettings()
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

    const s2aRes = await gptBusinessApi.testS2aConnection({ target_key: sub2apiTargetKey.value })
    const s2aOk = !!s2aRes?.success

    if (poolMode.value === 'crs_sync') {
      const crsRes = await gptBusinessApi.testCrsConnection()
      const crsOk = !!crsRes?.success
      sub2apiTestOk.value = crsOk && s2aOk
      sub2apiTestMessage.value = `CRS: ${crsOk ? 'ok' : (crsRes?.message || 'failed')} | S2A(${sub2apiTargetKey.value}): ${s2aOk ? 'ok' : (s2aRes?.message || 'failed')}`
    } else {
      sub2apiTestOk.value = s2aOk
      sub2apiTestMessage.value = `S2A(${sub2apiTargetKey.value}): ${s2aOk ? 'ok' : (s2aRes?.message || 'failed')}`
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
    await Promise.all(ids.map(id => gptBusinessApi.sub2apiSink(id, { target_key: sub2apiTargetKey.value, mode: poolMode.value })))
    ElMessage.success(`已启动 ${ids.length} 个母号的自动入池`)
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
  await openSub2apiSinkDialog(ids)
}

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

const copyFull = (acc: GptBusinessAccount) => {
  const lines = [
    acc.email,
    acc.account_password ? `account_password: ${acc.account_password}` : '',
    acc.email_password ? `email_password: ${acc.email_password}` : ''
  ].filter(Boolean)
  copyText(lines.join('\n'))
}

const copyAccountPassword = (acc: GptBusinessAccount) => {
  if (!acc.account_password) return
  copyText(acc.account_password)
}

const copyEmailPassword = (acc: GptBusinessAccount) => {
  if (!acc.email_password) return
  copyText(acc.email_password)
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
  return account.geekez_profile_exists ? '打开环境' : '创建环境'
}

type StatusBadge = { key: string; text: string; class: string }

const getAccountStatusBadges = (account: any): StatusBadge[] => {
  const badges: StatusBadge[] = []

  const accountType = String(account?.type || '')
  const isChild = accountType === 'child'

  const registerStatus = String(account?.register_status || 'not_started')
  const loginStatus = String(account?.login_status || 'not_started')
  const poolStatus = String(account?.pool_status || '')
  const teamJoinStatus = String(account?.team_join_status || '')

  const push = (key: string, text: string, cls: string) => {
    badges.push({ key, text, class: cls })
  }

  const mapCommon = (prefix: string, status: string, labels: Record<string, string>) => {
    const text = labels[status] || labels.not_started
    const clsMap: Record<string, string> = {
      success: 'bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-400 dark:border-emerald-800',
      running: 'bg-sky-100 text-sky-700 border-sky-200 dark:bg-sky-900/30 dark:text-sky-400 dark:border-sky-800',
      failed: 'bg-rose-100 text-rose-700 border-rose-200 dark:bg-rose-900/30 dark:text-rose-400 dark:border-rose-800',
      not_started: 'bg-slate-100 text-slate-600 border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700'
    }
    push(prefix, text, clsMap[status] || clsMap.not_started)
  }

  mapCommon('register', registerStatus, {
    success: '已注册',
    running: '注册中',
    failed: '注册失败',
    not_started: '未注册'
  })

  mapCommon('login', loginStatus, {
    success: '已登录',
    running: '登录中',
    failed: '登录失败',
    not_started: '未登录'
  })

  // 入池状态（母号/子号都展示）
  if (poolStatus) {
    mapCommon('pool', poolStatus, {
      success: '已入池',
      running: '入池中',
      failed: '入池失败',
      not_started: '未入池'
    })
  }

  // 子号：入队状态
  if (isChild && teamJoinStatus) {
    mapCommon('join', teamJoinStatus, {
      success: '已入队',
      running: '入队中',
      failed: '入队失败',
      not_started: '未入队'
    })
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
  try {
    const res = await gptBusinessApi.getTaskLog(task.id, { tail: 2000 })
    currentLogFilename.value = res?.filename || 'run.log'
    currentLogDownloadUrl.value = res?.download_url || ''
    taskLogText.value = res?.text || ''
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '获取日志失败')
    taskLogText.value = ''
    currentLogDownloadUrl.value = ''
  } finally {
    taskLogLoading.value = false
  }
}

const viewTaskLog = async (task: TaskRow) => {
  if (!task?.id) return
  taskLogDialogVisible.value = true
  await loadTaskLog(task)
}

const reloadTaskLog = async () => {
  if (!currentLogTask.value) return
  await loadTaskLog(currentLogTask.value)
}

const getTaskTypeName = (type: string) => {
  const map: Record<string, string> = {
    self_register: '自动开通',
    auto_invite: '自动邀请',
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
  if (ids.length > 0) {
    openSub2apiSinkDialog(ids)
    return
  }
  if (selectedMother.value?.id) {
    openSub2apiSinkDialog([selectedMother.value.id])
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
  window.removeEventListener('keydown', handleKeydown)
})
</script>
