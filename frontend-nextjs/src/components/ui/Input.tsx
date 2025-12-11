'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';

export interface InputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'> {
  /** Optional size variant – can be extended later */
  size?: 'sm' | 'md' | 'lg';
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, size = 'md', type = 'text', ...props }, ref) => {
    const sizeClasses =
      size === 'sm'
        ? 'h-8 px-2 text-xs'
        : size === 'lg'
        ? 'h-11 px-4 text-sm'
        : 'h-9 px-3 text-sm';

    return (
      <input
        ref={ref}
        type={type}
        className={cn(
          'block w-full rounded-lg border-2 border-neutral-300',
          'bg-white text-neutral-900 shadow-xs',
          'placeholder:text-neutral-400',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:border-primary-500',
          'disabled:cursor-not-allowed disabled:opacity-60',
          sizeClasses,
          className,
        )}
        {...props}
      />
    );
  },
);

Input.displayName = 'Input';


