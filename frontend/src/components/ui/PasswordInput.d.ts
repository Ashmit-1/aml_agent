interface PasswordInputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
    error?: boolean;
}
export declare const PasswordInput: ({ className, error, ...props }: PasswordInputProps) => import("react").JSX.Element;
export {};
