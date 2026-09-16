import type { ButtonHTMLAttributes, ReactNode } from 'react'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
    children: ReactNode
    variant?: 'primary' | 'secondary'
    isLoading?: boolean
}

export function Button({
    children,
    variant = 'primary',
    isLoading = false,
    className = '',
    disabled,
    ...props
}: ButtonProps) {
    const base =
        'px-5 py-2.5 rounded-lg font-semibold transition disabled:opacity-50 disabled:cursor-not-allowed'
    const variants = {
        primary: 'bg-red-600 hover:bg-red-500 text-white',
        secondary: 'bg-neutral-800 hover:bg-neutral-700 text-white',
    }

    return (
        <button
            className={`${base} ${variants[variant]} ${className}`}
            disabled={disabled || isLoading}
            {...props}
        >
            {isLoading ? 'Loading...' : children}
        </button>
    )
}