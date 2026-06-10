<template>
  <div class="alarm-config-page">
    <header class="page-header">
      <h2>告警规则配置</h2>
      <div style="display: flex; gap: 10px;">
        <router-link to="/" class="back-link">返回大屏</router-link>
      </div>
    </header>

    <el-tabs v-model="activeTab">
      <!-- Tab 1: 单规则 -->
      <el-tab-pane label="单指标规则" name="single">
        <div style="margin-bottom: 12px;">
          <el-button type="primary" @click="showDialog = true; editingId = null">新增规则</el-button>
        </div>
        <el-table :data="rules" border style="width: 100%" v-loading="loading" empty-text="暂无规则">
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="name" label="规则名称" width="180" />
          <el-table-column prop="line_id" label="产线" width="80" />
          <el-table-column prop="metric_name" label="指标" width="110" />
          <el-table-column prop="rule_type" label="类型" width="120">
            <template #default="{ row }">
              <el-tag :type="row.rule_type === 'static' ? '' : 'success'" size="small">
                {{ row.rule_type === 'static' ? '静态阈值' : '动态基线' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="阈值" width="180">
            <template #default="{ row }">
              <template v-if="row.rule_type === 'static'">
                下限: {{ row.lower_limit ?? '--' }} / 上限: {{ row.upper_limit ?? '--' }}
              </template>
              <template v-else>窗口{{ row.baseline_window }}min / ±{{ row.sigma_multiple }}σ</template>
            </template>
          </el-table-column>
          <el-table-column prop="severity" label="级别" width="100">
            <template #default="{ row }">
              <el-tag :type="severityType(row.severity)" size="small" effect="dark">
                {{ severityLabel(row.severity) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="is_active" label="状态" width="80">
            <template #default="{ row }">
              <el-switch :model-value="row.is_active" size="small" disabled />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150">
            <template #default="{ row }">
              <el-button size="small" @click="editRule(row)">编辑</el-button>
              <el-button size="small" type="danger" @click="deleteRule(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-dialog v-model="showDialog" :title="editingId ? '编辑规则' : '新增规则'" width="500px">
          <el-form :model="form" label-width="100px">
            <el-form-item label="规则名称">
              <el-input v-model="form.name" placeholder="如：产线A温度上限告警" />
            </el-form-item>
            <el-form-item label="产线">
              <el-select v-model="form.line_id" style="width: 100%">
                <el-option v-for="l in lines" :key="l.id" :label="l.name" :value="l.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="监控指标">
              <el-select v-model="form.metric_name" style="width: 100%">
                <el-option label="温度" value="temperature" />
                <el-option label="湿度" value="humidity" />
                <el-option label="压力" value="pressure" />
                <el-option label="速度" value="speed" />
              </el-select>
            </el-form-item>
            <el-form-item label="规则类型">
              <el-radio-group v-model="form.rule_type">
                <el-radio value="static">静态阈值</el-radio>
                <el-radio value="dynamic_baseline">动态基线</el-radio>
              </el-radio-group>
            </el-form-item>
            <template v-if="form.rule_type === 'static'">
              <el-form-item label="上限"><el-input-number v-model="form.upper_limit" /></el-form-item>
              <el-form-item label="下限"><el-input-number v-model="form.lower_limit" /></el-form-item>
            </template>
            <template v-else>
              <el-form-item label="基线窗口(分)"><el-input-number v-model="form.baseline_window" :min="5" :max="1440" /></el-form-item>
              <el-form-item label="标准差倍数"><el-input-number v-model="form.sigma_multiple" :min="1" :max="10" :step="0.5" /></el-form-item>
            </template>
            <el-form-item label="告警级别">
              <el-select v-model="form.severity" style="width: 100%">
                <el-option label="警告" value="warning" /><el-option label="严重" value="critical" /><el-option label="紧急" value="emergency" />
              </el-select>
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="showDialog = false">取消</el-button>
            <el-button type="primary" @click="submitForm">{{ editingId ? '更新' : '创建' }}</el-button>
          </template>
        </el-dialog>
      </el-tab-pane>

      <!-- Tab 2: 组合规则 -->
      <el-tab-pane label="组合规则" name="composite">
        <div style="margin-bottom: 12px;">
          <el-button type="primary" @click="showCompositeDialog = true; editingCompositeId = null">新增组合规则</el-button>
          <span style="color: #888; margin-left: 12px; font-size: 12px;">当多个指标满足条件时触发联合告警</span>
        </div>
        <el-table :data="compositeRules" border style="width: 100%" v-loading="compositeLoading" empty-text="暂无组合规则">
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="name" label="规则名称" width="180" />
          <el-table-column prop="line_id" label="产线" width="80" />
          <el-table-column prop="rule_ids" label="子规则ID" width="200">
            <template #default="{ row }">{{ row.rule_ids?.join(', ') }}</template>
          </el-table-column>
          <el-table-column prop="logic" label="逻辑" width="80">
            <template #default="{ row }">
              <el-tag :type="row.logic === 'AND' ? 'warning' : 'info'" size="small">{{ row.logic }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="composite_severity" label="级别" width="100">
            <template #default="{ row }">
              <el-tag :type="severityType(row.composite_severity)" size="small" effect="dark">{{ severityLabel(row.composite_severity) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="is_active" label="启用" width="70">
            <template #default="{ row }"><el-switch :model-value="row.is_active" size="small" disabled /></template>
          </el-table-column>
          <el-table-column label="操作" width="150">
            <template #default="{ row }">
              <el-button size="small" @click="editComposite(row)">编辑</el-button>
              <el-button size="small" type="danger" @click="deleteComposite(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-dialog v-model="showCompositeDialog" :title="editingCompositeId ? '编辑组合规则' : '新增组合规则'" width="500px">
          <el-form :model="compositeForm" label-width="100px">
            <el-form-item label="规则名称"><el-input v-model="compositeForm.name" /></el-form-item>
            <el-form-item label="产线">
              <el-select v-model="compositeForm.line_id" style="width: 100%">
                <el-option v-for="l in lines" :key="l.id" :label="l.name" :value="l.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="子规则ID">
              <el-select v-model="compositeForm.rule_ids" multiple placeholder="选择多个规则ID" style="width: 100%">
                <el-option v-for="r in rules" :key="r.id" :label="`#${r.id} ${r.name}`" :value="r.id" :disabled="r.line_id !== compositeForm.line_id" />
              </el-select>
            </el-form-item>
            <el-form-item label="联判逻辑">
              <el-radio-group v-model="compositeForm.logic">
                <el-radio value="AND">AND (全部触发)</el-radio>
                <el-radio value="OR">OR (任一个触发)</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="告警级别">
              <el-select v-model="compositeForm.composite_severity" style="width: 100%">
                <el-option label="警告" value="warning" /><el-option label="严重" value="critical" /><el-option label="紧急" value="emergency" />
              </el-select>
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="showCompositeDialog = false">取消</el-button>
            <el-button type="primary" @click="submitCompositeForm">{{ editingCompositeId ? '更新' : '创建' }}</el-button>
          </template>
        </el-dialog>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'

const activeTab = ref('single')
const rules = ref<any[]>([])
const lines = ref<Array<{ id: number; name: string }>>([])
const loading = ref(false)
const showDialog = ref(false)
const editingId = ref<number | null>(null)

const form = ref({
  name: '', line_id: 1, metric_name: 'temperature', rule_type: 'static',
  upper_limit: null as number | null, lower_limit: null as number | null,
  baseline_window: 60, sigma_multiple: 3.0, severity: 'warning', is_active: true,
})

// ---- 组合规则 ----
const compositeRules = ref<any[]>([])
const compositeLoading = ref(false)
const showCompositeDialog = ref(false)
const editingCompositeId = ref<number | null>(null)
const compositeForm = ref({
  name: '', line_id: 1, rule_ids: [] as number[],
  logic: 'AND', composite_severity: 'critical', is_active: true,
})

async function loadRules() {
  loading.value = true
  try {
    const resp = await axios.get('/api/v1/alarms/rules')
    rules.value = resp.data?.data || []
  } catch (e) { console.error(e) }
  finally { loading.value = false }
}

async function loadLines() {
  try {
    const resp = await axios.get('/api/v1/lines')
    lines.value = resp.data?.data || []
  } catch (e) { console.error(e) }
}

async function loadCompositeRules() {
  compositeLoading.value = true
  try {
    const resp = await axios.get('/api/v1/alarms/composite-rules')
    compositeRules.value = resp.data?.data || []
  } catch (e) { console.error(e) }
  finally { compositeLoading.value = false }
}

function editRule(rule: any) {
  editingId.value = rule.id
  form.value = {
    name: rule.name, line_id: rule.line_id, metric_name: rule.metric_name,
    rule_type: rule.rule_type, upper_limit: rule.upper_limit, lower_limit: rule.lower_limit,
    baseline_window: rule.baseline_window || 60, sigma_multiple: rule.sigma_multiple || 3.0,
    severity: rule.severity, is_active: rule.is_active,
  }
  showDialog.value = true
}

async function submitForm() {
  try {
    if (editingId.value) {
      await axios.put(`/api/v1/alarms/rules/${editingId.value}`, form.value)
      ElMessage.success('规则已更新')
    } else {
      await axios.post('/api/v1/alarms/rules', form.value)
      ElMessage.success('规则已创建')
    }
    showDialog.value = false; editingId.value = null; resetForm(); loadRules()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '操作失败') }
}

async function deleteRule(id: number) {
  try {
    await ElMessageBox.confirm('确定删除此告警规则？', '确认', { type: 'warning' })
    await axios.delete(`/api/v1/alarms/rules/${id}`)
    ElMessage.success('已删除'); loadRules()
  } catch (e) { /* cancelled */ }
}

function resetForm() {
  form.value = { name: '', line_id: 1, metric_name: 'temperature', rule_type: 'static',
    upper_limit: null, lower_limit: null, baseline_window: 60, sigma_multiple: 3.0,
    severity: 'warning', is_active: true }
}

// ---- 组合规则操作 ----
function editComposite(rule: any) {
  editingCompositeId.value = rule.id
  compositeForm.value = {
    name: rule.name, line_id: rule.line_id,
    rule_ids: Array.isArray(rule.rule_ids) ? [...rule.rule_ids] : (rule.rule_ids || []),
    logic: rule.logic, composite_severity: rule.composite_severity,
    is_active: rule.is_active,
  }
  showCompositeDialog.value = true
}

async function submitCompositeForm() {
  try {
    if (editingCompositeId.value) {
      await axios.put(`/api/v1/alarms/composite-rules/${editingCompositeId.value}`, compositeForm.value)
      ElMessage.success('组合规则已更新')
    } else {
      await axios.post('/api/v1/alarms/composite-rules', compositeForm.value)
      ElMessage.success('组合规则已创建')
    }
    showCompositeDialog.value = false; editingCompositeId.value = null
    resetCompositeForm(); loadCompositeRules()
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '操作失败') }
}

async function deleteComposite(id: number) {
  try {
    await ElMessageBox.confirm('确定删除？', '确认', { type: 'warning' })
    await axios.delete(`/api/v1/alarms/composite-rules/${id}`)
    ElMessage.success('已删除'); loadCompositeRules()
  } catch (e) { /* cancelled */ }
}

function resetCompositeForm() {
  compositeForm.value = { name: '', line_id: 1, rule_ids: [], logic: 'AND', composite_severity: 'critical', is_active: true }
}

function severityType(s: string) {
  const m: Record<string, string> = { warning: '', critical: 'warning', emergency: 'danger' }
  return m[s] || ''
}
function severityLabel(s: string) {
  const m: Record<string, string> = { warning: '警告', critical: '严重', emergency: '紧急' }
  return m[s] || s
}

onMounted(() => { loadRules(); loadLines(); loadCompositeRules() })
</script>

<style scoped>
.alarm-config-page { padding: 20px; min-height: 100vh; background: #0a1628; color: #e0e6ed; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { font-size: 20px; }
.back-link { font-size: 13px; color: #5a7a9a; text-decoration: none; padding: 4px 12px; border: 1px solid rgba(0, 200, 255, 0.2); border-radius: 3px; }
.back-link:hover { color: #00d4ff; }
</style>
