import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import { authApi } from '@/services/authApi';
import { AuthCard } from '@/components/auth/AuthCard';
import { FormField } from '@/components/ui/FormField';
import { PasswordInput } from '@/components/ui/PasswordInput';
import { FormFieldError } from '@/components/ui/FormFieldError';
import { Button } from '@/components/ui/button';
import { Loader2 } from 'lucide-react';

interface FormErrors {
  username?: string;
  password?: string;
  general?: string;
}

export const LoginPage = () => {
  const navigate = useNavigate();
  const { login } = useAuthStore();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState<FormErrors>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const validateField = (name: string, value: string): string | undefined => {
    switch (name) {
      case 'username':
        if (!value) return 'Username is required';
        if (value.length < 3) return 'Username must be at least 3 characters';
        if (value.length > 50) return 'Username must be less than 50 characters';
        if (!/^[a-zA-Z0-9_-]+$/.test(value)) return 'Username can only contain letters, numbers, underscores, and hyphens';
        return undefined;
      case 'password':
        if (!value) return 'Password is required';
        if (value.length < 6) return 'Password must be at least 6 characters';
        if (value.length > 128) return 'Password must be less than 128 characters';
        return undefined;
      default:
        return undefined;
    }
  };

  const handleBlur = (name: string, value: string) => {
    setTouched((prev) => ({ ...prev, [name]: true }));
    const error = validateField(name, value);
    setErrors((prev) => ({ ...prev, [name]: error }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});

    // Validate all fields
    const usernameError = validateField('username', username);
    const passwordError = validateField('password', password);

    if (usernameError || passwordError) {
      setErrors({ username: usernameError, password: passwordError });
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await authApi.login(username, password);
      login(response);
      navigate('/chat');
    } catch (err: any) {
      setErrors({ general: err.message || 'Login failed' });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthCard
      title="Welcome Back"
      footer={
        <p>
          Don't have an account?{' '}
          <Link to="/signup" className="text-white hover:underline">
            Sign up
          </Link>
        </p>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {errors.general && (
          <div className="p-3 rounded-md bg-red-900/30 border border-red-500/30">
            <p className="text-sm text-red-400">{errors.general}</p>
          </div>
        )}

        <FormField
          label="Username"
          name="username"
          value={username}
          onChange={setUsername}
          onBlur={() => handleBlur('username', username)}
          error={touched.username ? errors.username : undefined}
          placeholder="Enter your username"
          maxLength={50}
        />

        <div className="space-y-1.5">
          <label className="block text-sm font-medium text-white">
            Password
          </label>
          <PasswordInput
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onBlur={() => handleBlur('password', password)}
            placeholder="Enter your password"
            error={!!(touched.password && errors.password)}
          />
          <FormFieldError
            message={touched.password ? errors.password : undefined}
          />
        </div>

        <Button
          type="submit"
          disabled={isSubmitting}
          className="w-full bg-white text-black hover:bg-gray-200"
        >
          {isSubmitting ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            'Login'
          )}
        </Button>
      </form>
    </AuthCard>
  );
};
