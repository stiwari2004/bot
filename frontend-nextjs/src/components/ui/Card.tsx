'use client';

import { ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface CardProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  onClick?: () => void;
  variant?: 'default' | 'elevated' | 'outlined' | 'gradient';
}

export function Card({ 
  children, 
  className, 
  hover = false, 
  onClick,
  variant = 'default' 
}: CardProps) {
  const baseStyles = 'rounded-xl transition-all duration-200 animate-fade-in';
  
  const variantStyles = {
    default: 'bg-white border border-neutral-200 shadow-sm',
    elevated: 'bg-white border border-neutral-200 shadow-md',
    outlined: 'bg-white border-2 border-neutral-200 shadow-sm',
    gradient: 'bg-gradient-to-br from-white to-neutral-50 border border-neutral-200 shadow-sm',
  };
  
  const hoverStyles = hover || onClick
    ? 'hover:shadow-lg hover:border-primary-300 hover:-translate-y-0.5 cursor-pointer active:scale-[0.98]'
    : '';
  
  const clickStyles = onClick ? 'cursor-pointer' : '';
  
  return (
    <div
      className={cn(
        baseStyles,
        variantStyles[variant],
        hoverStyles,
        clickStyles,
        className
      )}
      onClick={onClick}
    >
      {children}
    </div>
  );
}

interface CardHeaderProps {
  children: ReactNode;
  className?: string;
}

export function CardHeader({ children, className }: CardHeaderProps) {
  return (
    <div className={cn('px-6 py-4 border-b border-neutral-100', className)}>
      {children}
    </div>
  );
}

interface CardContentProps {
  children: ReactNode;
  className?: string;
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

export function CardContent({ children, className, padding = 'md' }: CardContentProps) {
  const paddingStyles = {
    none: 'p-0',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
  };
  
  return (
    <div className={cn(paddingStyles[padding], className)}>
      {children}
    </div>
  );
}

interface CardFooterProps {
  children: ReactNode;
  className?: string;
}

export function CardFooter({ children, className }: CardFooterProps) {
  return (
    <div className={cn('px-6 py-4 border-t border-neutral-100 bg-neutral-50 rounded-b-xl', className)}>
      {children}
    </div>
  );
}
