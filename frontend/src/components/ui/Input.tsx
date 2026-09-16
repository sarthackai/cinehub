import type { InputHTMLAttributes } from 'react'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
    label: string
    error?: string
}

export function Input({ label, error, id, ...props }: InputProps) {
    return (
        <div className="flex flex-col gap-1.5">
            <label htmlFor={id} className="text-sm font-medium text-neutral-300">
                {label}
            </label>
            <input
                id={id}
                className="bg-neutral-900 border border-neutral-800 rounded-lg px-4 py-2.5 text-white placeholder-neutral-600 focus:outline-none focus:ring-2 focus:ring-red-600 focus:border-transparent transition"
                {...props}
            />
            {error && <p className="text-sm text-red-500">{error}</p>}
        </div>
    )
}