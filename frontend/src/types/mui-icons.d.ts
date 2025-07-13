declare module '@mui/icons-material' {
  import { SvgIconComponent } from '@mui/icons-material'
  
  export const Dashboard: SvgIconComponent
  export const Build: SvgIconComponent
  export const Timeline: SvgIconComponent
  export const Add: SvgIconComponent
  export const PlayArrow: SvgIconComponent
  export const Upload: SvgIconComponent
  export const Cancel: SvgIconComponent
  export const Download: SvgIconComponent
  export const Refresh: SvgIconComponent
  export const ArrowBack: SvgIconComponent
  export const Visibility: SvgIconComponent
  export const Compare: SvgIconComponent
  export const Save: SvgIconComponent
}

declare module '@mui/icons-material/*' {
  import { SvgIconComponent } from '@mui/icons-material'
  const Icon: SvgIconComponent
  export default Icon
}