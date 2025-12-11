'use client';

import { ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { statusColors, severityColors } from '@/styles/design-system';

interface BadgeProps {
  children: ReactNode;
  variant?: 'status' | 'severity' | 'primary' | 'secondary' | 'success' | 'warning' | 'error';
  status?: keyof typeof statusColors;
  severity?: keyof typeof severityColors;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function Badge({ 
  children, 
  variant = 'primary',
  status,
  severity,
  size = 'md',
  className 
}: BadgeProps) {
  const sizeStyles = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-3 py-1 text-sm',
    lg: 'px-4 py-1.5 text-base',
  };
  
  // Get color styles - use inline styles for dynamic colors
  const getColorStyles = () => {
    if (variant === 'status' && status) {
      const colors = statusColors[status];
      if (!colors) {
        // Fallback for unknown status
        return {
          backgroundColor: '#f5f5f5',
          color: '#525252',
          borderColor: '#e5e5e5',
        };
      }
      return {
        backgroundColor: colors.bg,
        color: colors.text,
        borderColor: colors.border,
      };
    }
    if (variant === 'severity' && severity) {
      const colors = severityColors[severity];
      if (!colors) {
        // Fallback for unknown severity
        return {
          backgroundColor: '#f5f5f5',
          color: '#525252',
          borderColor: '#e5e5e5',
        };
      }
      return {
        backgroundColor: colors.bg,
        color: colors.text,
        borderColor: colors.border,
      };
    }
    
    // Static variant colors
    const variantColorMap: Record<string, { bg: string; text: string; border: string }> = {
      primary: { bg: '#ecfeff', text: '#0e7490', border: '#a5f3fc' },
      secondary: { bg: '#faf5ff', text: '#7e22ce', border: '#e9d5ff' },
      success: { bg: '#f0fdf4', text: '#15803d', border: '#bbf7d0' },
      warning: { bg: '#fffbeb', text: '#b45309', border: '#fde68a' },
      error: { bg: '#fef2f2', text: '#b91c1c', border: '#fecaca' },
    };
    
    const colors = variantColorMap[variant] || variantColorMap.primary;
    return {
      backgroundColor: colors.bg,
      color: colors.text,
      borderColor: colors.border,
    };
  };
  
  return (
    <span
      className={cn(
        'inline-flex items-center font-medium rounded-lg border',
        sizeStyles[size],
        className
      )}
      style={getColorStyles()}
    >
      {children}
    </span>
  );
}
