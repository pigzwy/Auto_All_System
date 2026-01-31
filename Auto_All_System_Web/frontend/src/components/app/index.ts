import type { App, Plugin } from 'vue'
import { vLoading } from './loading'

import ElAlert from './ElAlert.vue'
import ElButton from './ElButton.vue'
import ElButtonGroup from './ElButtonGroup.vue'
import ElCard from './ElCard.vue'
import ElCollapse from './ElCollapse.vue'
import ElCollapseItem from './ElCollapseItem.vue'
import ElDatePicker from './ElDatePicker.vue'
import ElDescriptions from './ElDescriptions.vue'
import ElDescriptionsItem from './ElDescriptionsItem.vue'
import ElDialog from './ElDialog.vue'
import ElDivider from './ElDivider.vue'
import ElForm from './ElForm.vue'
import ElFormItem from './ElFormItem.vue'
import ElIcon from './ElIcon.vue'
import ElInput from './ElInput.vue'
import ElInputNumber from './ElInputNumber.vue'
import ElLink from './ElLink.vue'
import ElOption from './ElOption.vue'
import ElPageHeader from './ElPageHeader.vue'
import ElPagination from './ElPagination.vue'
import ElProgress from './ElProgress.vue'
import ElRadio from './ElRadio.vue'
import ElRadioButton from './ElRadioButton.vue'
import ElRadioGroup from './ElRadioGroup.vue'
import ElResult from './ElResult.vue'
import ElScrollbar from './ElScrollbar.vue'
import ElSelect from './ElSelect.vue'
import ElStatistic from './ElStatistic.vue'
import ElSwitch from './ElSwitch.vue'
import ElTable from './ElTable.vue'
import ElTableColumn from './ElTableColumn.vue'
import ElTag from './ElTag.vue'
import ElTimeline from './ElTimeline.vue'
import ElTimelineItem from './ElTimelineItem.vue'
import ElTooltip from './ElTooltip.vue'
import ElTransfer from './ElTransfer.vue'
import ElUpload from './ElUpload.vue'

const components = {
  AppAlert: ElAlert,
  AppButton: ElButton,
  AppButtonGroup: ElButtonGroup,
  AppCard: ElCard,
  AppCollapse: ElCollapse,
  AppCollapseItem: ElCollapseItem,
  AppDatePicker: ElDatePicker,
  AppDescriptions: ElDescriptions,
  AppDescriptionsItem: ElDescriptionsItem,
  AppDialog: ElDialog,
  AppDivider: ElDivider,
  AppForm: ElForm,
  AppFormItem: ElFormItem,
  AppIcon: ElIcon,
  AppInput: ElInput,
  AppInputNumber: ElInputNumber,
  AppLink: ElLink,
  AppOption: ElOption,
  AppPageHeader: ElPageHeader,
  AppPagination: ElPagination,
  AppProgress: ElProgress,
  AppRadio: ElRadio,
  AppRadioButton: ElRadioButton,
  AppRadioGroup: ElRadioGroup,
  AppResult: ElResult,
  AppScrollbar: ElScrollbar,
  AppSelect: ElSelect,
  AppStatistic: ElStatistic,
  AppSwitch: ElSwitch,
  AppTable: ElTable,
  AppTableColumn: ElTableColumn,
  AppTag: ElTag,
  AppTimeline: ElTimeline,
  AppTimelineItem: ElTimelineItem,
  AppTooltip: ElTooltip,
  AppTransfer: ElTransfer,
  AppUpload: ElUpload,
}

// Deprecated: kept temporarily for reference only.
// App bootstrap uses `frontend/src/plugins/ui.ts`.
export const LegacyAppComponentsPlugin: Plugin = {
  install(app: App) {
    for (const [name, component] of Object.entries(components)) {
      app.component(name, component)
    }

    app.directive('loading', vLoading)
  },
}

export default LegacyAppComponentsPlugin
