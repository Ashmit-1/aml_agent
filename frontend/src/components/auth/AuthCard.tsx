import { Card } from '@/components/ui/card';

interface AuthCardProps {
  title: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}

export const AuthCard = ({ title, children, footer }: AuthCardProps) => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-black px-4">
      <Card className="w-full max-w-md bg-black border border-white/10 p-8">
        <div className="space-y-6">
          <div className="text-center">
            <h1 className="text-2xl font-medium text-white">{title}</h1>
          </div>
          <div className="space-y-4">{children}</div>
          {footer && (
            <div className="text-center text-sm text-gray-500">{footer}</div>
          )}
        </div>
      </Card>
    </div>
  );
};
