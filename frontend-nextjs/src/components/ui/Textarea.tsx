'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  /** Optional size variant – can be extended later */
  variant?: 'default' | 'subtle';
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, rows = 4, variant = 'default', ...props }, ref) => {
    const variantClasses =
      variant === 'subtle'
        ? 'bg-neutral-50 border-neutral-200'
        : 'bg-white border-neutral-300';

    return (
      <textarea
        ref={ref}
        rows={rows}
        className={cn(
          'block w-full rounded-lg border-2',
          variantClasses,
          'text-sm text-neutral-900 shadow-xs',
          'placeholder:text-neutral-400',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:border-primary-500',
          'disabled:cursor-not-allowed disabled:opacity-60',
          'resize-y min-h-[96px]',
          className,
        )}
        {...props}
      />
    );
  },
);

Textarea.displayName = 'Textarea';









