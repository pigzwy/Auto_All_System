import type { App, Plugin } from 'vue'

// shadcn-vue primitives (global)
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { Progress } from '@/components/ui/progress'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectItemText,
  SelectLabel,
  SelectScrollDownButton,
  SelectScrollUpButton,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableEmpty,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuShortcut,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogScrollContent,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'

// Legacy wrapper components (temporary) – these will be phased out.
import { vLoading } from '@/components/app/loading'

import ElAlert from '@/components/app/ElAlert.vue'
import ElButtonGroup from '@/components/app/ElButtonGroup.vue'
import ElCard from '@/components/app/ElCard.vue'
import ElCollapse from '@/components/app/ElCollapse.vue'
import ElCollapseItem from '@/components/app/ElCollapseItem.vue'
import ElDescriptions from '@/components/app/ElDescriptions.vue'
import ElDescriptionsItem from '@/components/app/ElDescriptionsItem.vue'
import ElDialog from '@/components/app/ElDialog.vue'
import ElForm from '@/components/app/ElForm.vue'
import ElFormItem from '@/components/app/ElFormItem.vue'
import ElIcon from '@/components/app/ElIcon.vue'
import ElInput from '@/components/app/ElInput.vue'
import ElInputNumber from '@/components/app/ElInputNumber.vue'
import ElOption from '@/components/app/ElOption.vue'
import ElPageHeader from '@/components/app/ElPageHeader.vue'
import ElPagination from '@/components/app/ElPagination.vue'
import ElProgress from '@/components/app/ElProgress.vue'
import ElRadio from '@/components/app/ElRadio.vue'
import ElRadioButton from '@/components/app/ElRadioButton.vue'
import ElRadioGroup from '@/components/app/ElRadioGroup.vue'
import ElResult from '@/components/app/ElResult.vue'
import ElScrollbar from '@/components/app/ElScrollbar.vue'
import ElSelect from '@/components/app/ElSelect.vue'
import ElStatistic from '@/components/app/ElStatistic.vue'
import ElSwitch from '@/components/app/ElSwitch.vue'
import ElTable from '@/components/app/ElTable.vue'
import ElTableColumn from '@/components/app/ElTableColumn.vue'
import ElTag from '@/components/app/ElTag.vue'
import ElTimeline from '@/components/app/ElTimeline.vue'
import ElTimelineItem from '@/components/app/ElTimelineItem.vue'
import ElTooltip from '@/components/app/ElTooltip.vue'
import ElTransfer from '@/components/app/ElTransfer.vue'
import ElUpload from '@/components/app/ElUpload.vue'

export const UiPlugin: Plugin = {
  install(app: App) {
    // shadcn primitives
    app.component('Button', Button)
    app.component('Badge', Badge)
    app.component('Separator', Separator)
    app.component('Card', Card)
    app.component('CardContent', CardContent)
    app.component('CardDescription', CardDescription)
    app.component('CardFooter', CardFooter)
    app.component('CardHeader', CardHeader)
    app.component('CardTitle', CardTitle)
    app.component('Input', Input)
    app.component('Textarea', Textarea)
    app.component('Switch', Switch)
    app.component('Progress', Progress)
    app.component('Checkbox', Checkbox)
    app.component('Avatar', Avatar)
    app.component('AvatarImage', AvatarImage)
    app.component('AvatarFallback', AvatarFallback)

    app.component('DropdownMenu', DropdownMenu)
    app.component('DropdownMenuCheckboxItem', DropdownMenuCheckboxItem)
    app.component('DropdownMenuContent', DropdownMenuContent)
    app.component('DropdownMenuGroup', DropdownMenuGroup)
    app.component('DropdownMenuItem', DropdownMenuItem)
    app.component('DropdownMenuLabel', DropdownMenuLabel)
    app.component('DropdownMenuRadioGroup', DropdownMenuRadioGroup)
    app.component('DropdownMenuRadioItem', DropdownMenuRadioItem)
    app.component('DropdownMenuSeparator', DropdownMenuSeparator)
    app.component('DropdownMenuShortcut', DropdownMenuShortcut)
    app.component('DropdownMenuSub', DropdownMenuSub)
    app.component('DropdownMenuSubContent', DropdownMenuSubContent)
    app.component('DropdownMenuSubTrigger', DropdownMenuSubTrigger)
    app.component('DropdownMenuTrigger', DropdownMenuTrigger)

    app.component('Dialog', Dialog)
    app.component('DialogClose', DialogClose)
    app.component('DialogContent', DialogContent)
    app.component('DialogDescription', DialogDescription)
    app.component('DialogFooter', DialogFooter)
    app.component('DialogHeader', DialogHeader)
    app.component('DialogScrollContent', DialogScrollContent)
    app.component('DialogTitle', DialogTitle)
    app.component('DialogTrigger', DialogTrigger)

    app.component('Accordion', Accordion)
    app.component('AccordionContent', AccordionContent)
    app.component('AccordionItem', AccordionItem)
    app.component('AccordionTrigger', AccordionTrigger)

    app.component('Select', Select)
    app.component('SelectContent', SelectContent)
    app.component('SelectGroup', SelectGroup)
    app.component('SelectItem', SelectItem)
    app.component('SelectItemText', SelectItemText)
    app.component('SelectLabel', SelectLabel)
    app.component('SelectScrollDownButton', SelectScrollDownButton)
    app.component('SelectScrollUpButton', SelectScrollUpButton)
    app.component('SelectSeparator', SelectSeparator)
    app.component('SelectTrigger', SelectTrigger)
    app.component('SelectValue', SelectValue)

    app.component('Table', Table)
    app.component('TableBody', TableBody)
    app.component('TableCaption', TableCaption)
    app.component('TableCell', TableCell)
    app.component('TableEmpty', TableEmpty)
    app.component('TableFooter', TableFooter)
    app.component('TableHead', TableHead)
    app.component('TableHeader', TableHeader)
    app.component('TableRow', TableRow)

    // local wrappers (still custom UI, but no longer Element/Ui-prefixed)
    app.component('InfoAlert', ElAlert)
    app.component('ButtonGroup', ElButtonGroup)
    app.component('Panel', ElCard)
    app.component('Collapse', ElCollapse)
    app.component('CollapseItem', ElCollapseItem)
    app.component('Descriptions', ElDescriptions)
    app.component('DescriptionsItem', ElDescriptionsItem)
    app.component('Modal', ElDialog)
    app.component('SimpleForm', ElForm)
    app.component('SimpleFormItem', ElFormItem)
    app.component('Icon', ElIcon)
    app.component('TextInput', ElInput)
    app.component('NumberInput', ElInputNumber)
    app.component('SelectOption', ElOption)
    app.component('PageHeader', ElPageHeader)
    app.component('Paginator', ElPagination)
    app.component('ProgressBar', ElProgress)
    app.component('Radio', ElRadio)
    app.component('RadioButton', ElRadioButton)
    app.component('RadioGroup', ElRadioGroup)
    app.component('Result', ElResult)
    app.component('Scrollbar', ElScrollbar)
    app.component('SelectNative', ElSelect)
    app.component('Statistic', ElStatistic)
    app.component('Toggle', ElSwitch)
    app.component('DataTable', ElTable)
    app.component('DataColumn', ElTableColumn)
    app.component('Tag', ElTag)
    app.component('Timeline', ElTimeline)
    app.component('TimelineItem', ElTimelineItem)
    app.component('TooltipText', ElTooltip)
    app.component('Transfer', ElTransfer)
    app.component('FileUpload', ElUpload)

    app.directive('loading', vLoading)
  },
}

export default UiPlugin
