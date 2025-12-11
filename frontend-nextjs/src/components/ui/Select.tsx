'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';

type SelectContextValue = {
  value: string;
  onValueChange: (value: string) => void;
  open: boolean;
  setOpen: (open: boolean) => void;
  disabled?: boolean;
};

const SelectContext = React.createContext<SelectContextValue | null>(null);

export interface SelectRootProps {
  value: string;
  onValueChange: (value: string) => void;
  disabled?: boolean;
  children: React.ReactNode;
  className?: string;
}

export function Select({
  value,
  onValueChange,
  disabled,
  children,
  className,
}: SelectRootProps) {
  const [open, setOpen] = React.useState(false);

  const ctx: SelectContextValue = React.useMemo(
    () => ({ value, onValueChange, open, setOpen, disabled }),
    [value, onValueChange, open, setOpen, disabled],
  );

  return (
    <SelectContext.Provider value={ctx}>
      <div className={cn('relative inline-block w-full', className)}>
        {children}
      </div>
    </SelectContext.Provider>
  );
}

function useSelectContext(component: string): SelectContextValue {
  const ctx = React.useContext<SelectContextValue | null>(SelectContext);
  if (!ctx) {
    throw new Error(`${component} must be used within <Select>`);
  }
  return ctx;
}

export interface SelectTriggerProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  id?: string;
}

export function SelectTrigger({
  className,
  children,
  id,
  ...props
}: SelectTriggerProps) {
  const { open, setOpen, disabled } = useSelectContext('SelectTrigger');

  return (
    <button
      type="button"
      id={id}
      disabled={disabled}
      aria-haspopup="listbox"
      aria-expanded={open}
      onClick={() => !disabled && setOpen(!open)}
      className={cn(
        'flex w-full items-center justify-between rounded-lg border-2 border-neutral-300 bg-white px-3 py-2.5 text-sm text-neutral-900 shadow-xs',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:border-primary-500',
        'disabled:cursor-not-allowed disabled:opacity-60',
        className,
      )}
      {...props}
    >
      <span className="flex-1 text-left">{children}</span>
      <span
        className={cn(
          'ml-2 inline-flex h-4 w-4 items-center justify-center text-[10px] text-neutral-400 transition-transform',
          open && 'rotate-180',
        )}
      >
        ▼
      </span>
    </button>
  );
}

export interface SelectValueProps {
  placeholder?: string;
}

export function SelectValue({ placeholder }: SelectValueProps) {
  const { value } = useSelectContext('SelectValue');
  return (
    <span
      className={cn(
        'truncate',
        !value && placeholder ? 'text-neutral-400' : 'text-neutral-900',
      )}
    >
      {value || placeholder || ''}
    </span>
  );
}

export interface SelectContentProps {
  children: React.ReactNode;
  className?: string;
}

export function SelectContent({ children, className }: SelectContentProps) {
  const { open } = useSelectContext('SelectContent');

  if (!open) return null;

  return (
    <div
      className={cn(
        'absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded-lg border border-neutral-200 bg-white py-1 shadow-lg',
        className,
      )}
      role="listbox"
    >
      {children}
    </div>
  );
}

export interface SelectItemProps {
  value: string;
  children: React.ReactNode;
  className?: string;
}

export function SelectItem({ value, children, className }: SelectItemProps) {
  const { value: selected, onValueChange, setOpen, disabled } =
    useSelectContext('SelectItem');

  const isSelected = selected === value;

  return (
    <button
      type="button"
      role="option"
      aria-selected={isSelected}
      disabled={disabled}
      onClick={() => {
        if (disabled) return;
        onValueChange(value);
        setOpen(false);
      }}
      className={cn(
        'flex w-full cursor-pointer items-center justify-between px-3 py-1.5 text-left text-sm',
        'text-neutral-700 hover:bg-primary-50 hover:text-primary-700',
        isSelected && 'bg-primary-50 text-primary-700 font-medium',
        className,
      )}
    >
      <span className="truncate">{children}</span>
      {isSelected && (
        <span className="ml-2 text-[10px] text-primary-600">✓</span>
      )}
    </button>
  );
}









