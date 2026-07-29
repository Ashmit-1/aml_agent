interface FormFieldProps {
    label: string;
    name: string;
    type?: string;
    value: string;
    onChange: (value: string) => void;
    onBlur?: () => void;
    error?: string;
    placeholder?: string;
    maxLength?: number;
}
export declare const FormField: ({ label, name, type, value, onChange, onBlur, error, placeholder, maxLength, }: FormFieldProps) => import("react").JSX.Element;
export {};
