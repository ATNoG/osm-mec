import type { ToastTransition } from 'react-toastify'
import type { ReactNode } from 'react'

export type ToastType = {
  position?: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right',
  autoClose?: number | false,
  hideProgressBar?: boolean,
  closeOnClick?: boolean,
  pauseOnHover?: boolean,
  draggable?: boolean,
  progress?: undefined | number | string,
  closeButton?: boolean,
  theme?: 'dark' | 'light' | 'colored',
  icon?: ReactNode | boolean,
  pauseOnFocusLoss?: boolean,
  delay?: number,
  type?: 'default' | 'success' | 'info' | 'warning' | 'error',
  transition?: ToastTransition
}

export enum OperationalStatus {
  INIT = 'init',
  RUNNING = 'running',
  FAILED = 'failed',
}

export enum ConfigStatus {
  INIT = 'init',
  CONFIGURED = 'configured',
  FAILED = 'failed',
}

export enum ActionType {
  CREATE = 'create',
  DELETE = 'delete',
  DEPLOY = 'deploy',
  UPDATE = 'update',
  TERMINATE = 'terminate'
}

export enum Item {
  APP = 'app',
  INSTANCE = 'instance'
}

export type ConfirmationDialogProps = {
  open: boolean,
  onClose: () => void,
  onConfirm: () => void,
  action: ActionType,
  item: Item
}

export type AppData = {
  id: string,
  name: string,
  provider: string,
  version: number
}

export type InstanceData = {
  id: string;
  name: string;
  description: string;
  details: string;
  'operational-status': string;
  'config-status': string;
  'created-at': Date;
}

export type RowData = {
  id: string,
  expand: boolean,
  name: string,
  description: string | null,
  details: string | null,
  'current-meh': string | null,
  'cpu-load': number | null,
  'mem-load': number | null,
  latency: number | null,
  'created-at': Date | null,
  'operational-status': OperationalStatus | null,
  'config-status': ConfigStatus | null,
  warnings: string | null,
  actions: boolean,
}

export type VimData = {
  id: string,
  name: string
}

export type DropdownOption = {
  label: string,
  handleClick: () => void
}

export type DropdownButtonProps = {
  title: string,
  options: DropdownOption[]
}

export type FormDialogField = {
  id: string,
  label: string,
  type: 'text' | 'select' | 'textarea',
  rows?: number,
  options?: Array<string | { label: string; value: string }>;
  required: boolean
}

export type FormDialogProps = {
  open: boolean,
  onClose: () => void,
  onSubmit: (data: any) => void,
  title: string,
  fields: FormDialogField[]
}

export type UploadDialogProps = {
  title: string,
  open: boolean,
  onClose: () => void,
  onSubmit: (data: any) => void
}

export type DetailsDialogProps = {
  title: string,
  open: boolean,
  onClose: () => void,
  data: string
}

export type InstanceGridProps = {
  minimalConfig?: boolean,
  instanceCount?: (count: number) => void,
}

export type SidebarProps = {
  item: {
    path: string,
    name: string,
    icon: ReactNode
  },
  isOpen: boolean,
  isSelected: boolean
}

export type Metrics = {
  [appiID: string]: {
    [containerID: string]: {
      mem_load: number | null,
      cpu_load: number | null,
      node: string | null,
      latency: number | null,
      kdu_id: string | null,
      warning: string | null
    }
  }
}