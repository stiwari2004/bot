'use client';

import { ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface TableProps {
  children: ReactNode;
  className?: string;
}

export function Table({ children, className }: TableProps) {
  return (
    <div className="overflow-x-auto rounded-xl border border-neutral-200 bg-white shadow-sm">
      <table className={cn('min-w-full divide-y divide-neutral-200', className)}>
        {children}
      </table>
    </div>
  );
}

interface TableHeaderProps {
  children: ReactNode;
  className?: string;
}

export function TableHeader({ children, className }: TableHeaderProps) {
  return (
    <thead className={cn('bg-gradient-to-r from-neutral-50 to-neutral-100', className)}>
      {children}
    </thead>
  );
}

interface TableRowProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  onClick?: () => void;
}

export function TableRow({ children, className, hover = false, onClick }: TableRowProps) {
  return (
    <tr
      className={cn(
        'transition-colors',
        hover || onClick ? 'hover:bg-primary-50 cursor-pointer' : '',
        className
      )}
      onClick={onClick}
    >
      {children}
    </tr>
  );
}

interface TableHeadProps {
  children: ReactNode;
  className?: string;
}

export function TableHead({ children, className }: TableHeadProps) {
  return (
    <th
      className={cn(
        'px-6 py-4 text-left text-xs font-semibold text-neutral-700 uppercase tracking-wider',
        className
      )}
    >
      {children}
    </th>
  );
}

interface TableCellProps {
  children: ReactNode;
  className?: string;
  colSpan?: number;
  rowSpan?: number;
}

export function TableCell({ children, className, colSpan, rowSpan }: TableCellProps) {
  return (
    <td 
      className={cn('px-6 py-4 whitespace-nowrap text-sm text-neutral-900', className)}
      colSpan={colSpan}
      rowSpan={rowSpan}
    >
      {children}
    </td>
  );
}

interface TableBodyProps {
  children: ReactNode;
  className?: string;
}

export function TableBody({ children, className }: TableBodyProps) {
  return (
    <tbody className={cn('bg-white divide-y divide-neutral-200', className)}>
      {children}
    </tbody>
  );
}
