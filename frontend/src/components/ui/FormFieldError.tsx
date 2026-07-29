import { AlertTriangle } from 'lucide-react';

interface FormFieldErrorProps {
  message?: string;
}

export const FormFieldError = ({ message }: FormFieldErrorProps) => {
  if (!message) return null;

  return (
    <div className="flex items-center gap-1.5 mt-1.5 text-red-400 text-sm">
      <AlertTriangle size={14} />
      <span>{message}</span>
    </div>
  );
};
