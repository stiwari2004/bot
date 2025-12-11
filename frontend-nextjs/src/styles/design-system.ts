/**
 * Unified Design System
 * Modern, vibrant, and professional color palette with consistent styling
 */

export const colors = {
  // Primary - Vibrant Cyan/Blue gradient
  primary: {
    50: '#ecfeff',
    100: '#cffafe',
    200: '#a5f3fc',
    300: '#67e8f9',
    400: '#22d3ee',
    500: '#06b6d4', // Main primary
    600: '#0891b2',
    700: '#0e7490',
    800: '#155e75',
    900: '#164e63',
  },
  
  // Secondary - Vibrant Purple/Magenta
  secondary: {
    50: '#faf5ff',
    100: '#f3e8ff',
    200: '#e9d5ff',
    300: '#d8b4fe',
    400: '#c084fc',
    500: '#a855f7', // Main secondary
    600: '#9333ea',
    700: '#7e22ce',
    800: '#6b21a8',
    900: '#581c87',
  },
  
  // Accent - Vibrant Emerald/Teal
  accent: {
    50: '#ecfdf5',
    100: '#d1fae5',
    200: '#a7f3d0',
    300: '#6ee7b7',
    400: '#34d399',
    500: '#10b981', // Main accent
    600: '#059669',
    700: '#047857',
    800: '#065f46',
    900: '#064e3b',
  },
  
  // Success
  success: {
    50: '#f0fdf4',
    100: '#dcfce7',
    200: '#bbf7d0',
    300: '#86efac',
    400: '#4ade80',
    500: '#22c55e',
    600: '#16a34a',
    700: '#15803d',
    800: '#166534',
    900: '#14532d',
  },
  
  // Warning
  warning: {
    50: '#fffbeb',
    100: '#fef3c7',
    200: '#fde68a',
    300: '#fcd34d',
    400: '#fbbf24',
    500: '#f59e0b',
    600: '#d97706',
    700: '#b45309',
    800: '#92400e',
    900: '#78350f',
  },
  
  // Error
  error: {
    50: '#fef2f2',
    100: '#fee2e2',
    200: '#fecaca',
    300: '#fca5a5',
    400: '#f87171',
    500: '#ef4444',
    600: '#dc2626',
    700: '#b91c1c',
    800: '#991b1b',
    900: '#7f1d1d',
  },
  
  // Neutral - Sophisticated grays
  neutral: {
    50: '#fafafa',
    100: '#f5f5f5',
    200: '#e5e5e5',
    300: '#d4d4d4',
    400: '#a3a3a3',
    500: '#737373',
    600: '#525252',
    700: '#404040',
    800: '#262626',
    900: '#171717',
  },
} as const;

export const typography = {
  fontFamily: {
    sans: ['-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'sans-serif'],
    mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
  },
  fontSize: {
    xs: '0.75rem',    // 12px
    sm: '0.875rem',   // 14px
    base: '1rem',     // 16px
    lg: '1.125rem',   // 18px
    xl: '1.25rem',    // 20px
    '2xl': '1.5rem',  // 24px
    '3xl': '1.875rem', // 30px
    '4xl': '2.25rem', // 36px
  },
  fontWeight: {
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },
  lineHeight: {
    tight: 1.25,
    normal: 1.5,
    relaxed: 1.75,
  },
} as const;

export const spacing = {
  0: '0',
  1: '0.25rem',  // 4px
  2: '0.5rem',   // 8px
  3: '0.75rem',  // 12px
  4: '1rem',     // 16px
  5: '1.25rem',  // 20px
  6: '1.5rem',   // 24px
  8: '2rem',     // 32px
  10: '2.5rem',  // 40px
  12: '3rem',    // 48px
  16: '4rem',    // 64px
  20: '5rem',    // 80px
} as const;

export const shadows = {
  sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
  base: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
  md: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
  lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
  xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
  '2xl': '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
  inner: 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.06)',
} as const;

export const borderRadius = {
  none: '0',
  sm: '0.375rem',   // 6px
  base: '0.5rem',   // 8px
  md: '0.75rem',    // 12px
  lg: '1rem',       // 16px
  xl: '1.5rem',     // 24px
  '2xl': '2rem',    // 32px
  full: '9999px',
} as const;

export const transitions = {
  fast: '150ms ease-in-out',
  base: '200ms ease-in-out',
  slow: '300ms ease-in-out',
} as const;

// Status color mappings
export const statusColors = {
  pending: {
    bg: colors.warning[50],
    text: colors.warning[700],
    border: colors.warning[200],
    icon: colors.warning[600],
  },
  running: {
    bg: colors.primary[50],
    text: colors.primary[700],
    border: colors.primary[200],
    icon: colors.primary[600],
  },
  waiting_approval: {
    bg: colors.secondary[50],
    text: colors.secondary[700],
    border: colors.secondary[200],
    icon: colors.secondary[600],
  },
  completed: {
    bg: colors.success[50],
    text: colors.success[700],
    border: colors.success[200],
    icon: colors.success[600],
  },
  failed: {
    bg: colors.error[50],
    text: colors.error[700],
    border: colors.error[200],
    icon: colors.error[600],
  },
  completed_with_errors: {
    bg: colors.warning[50],
    text: colors.warning[700],
    border: colors.warning[200],
    icon: colors.warning[600],
  },
  resolved: {
    bg: colors.success[50],
    text: colors.success[700],
    border: colors.success[200],
    icon: colors.success[600],
  },
  closed: {
    bg: colors.neutral[100],
    text: colors.neutral[700],
    border: colors.neutral[200],
    icon: colors.neutral[600],
  },
  escalated: {
    bg: colors.error[50],
    text: colors.error[700],
    border: colors.error[200],
    icon: colors.error[600],
  },
  in_progress: {
    bg: colors.primary[50],
    text: colors.primary[700],
    border: colors.primary[200],
    icon: colors.primary[600],
  },
  analyzing: {
    bg: colors.warning[50],
    text: colors.warning[700],
    border: colors.warning[200],
    icon: colors.warning[600],
  },
} as const;

// Severity color mappings
export const severityColors = {
  critical: {
    bg: colors.error[50],
    text: colors.error[700],
    border: colors.error[200],
    icon: colors.error[600],
  },
  high: {
    bg: colors.warning[50],
    text: colors.warning[700],
    border: colors.warning[200],
    icon: colors.warning[600],
  },
  medium: {
    bg: colors.warning[50],
    text: colors.warning[600],
    border: colors.warning[200],
    icon: colors.warning[500],
  },
  low: {
    bg: colors.primary[50],
    text: colors.primary[700],
    border: colors.primary[200],
    icon: colors.primary[600],
  },
} as const;








