/**
 * 디자인 토큰 - 색상, 간격, 둥글기를 중앙 관리.
 * 컴포넌트에서 직접 색상 코드를 쓰지 않고 여기서 참조한다.
 */

export const colors = {
  bgPage: '#0f0f1a',
  bgSurface: '#1e1e2e',
  bgSurfaceDeep: '#161622',

  border: '#333',
  borderSubtle: '#2a2a3e',
  borderInput: '#444',

  text: '#e0e0e0',
  textMuted: '#aaa',
  textFaint: '#666',
  textDim: '#888',

  primary: '#6366f1',
  primaryMuted: '#6366f144',
  success: '#10b981',
  warning: '#f59e0b',
  accent: '#a78bfa',
  danger: '#ef4444',
} as const;

export const spacing = {
  xs: '4px',
  sm: '8px',
  md: '12px',
  lg: '16px',
  xl: '24px',
  xxl: '32px',
} as const;

export const radius = {
  sm: '6px',
  md: '8px',
  lg: '12px',
} as const;

export const fontSize = {
  xs: '11px',
  sm: '12px',
  md: '13px',
  base: '14px',
  lg: '16px',
  xl: '18px',
  xxl: '20px',
} as const;
