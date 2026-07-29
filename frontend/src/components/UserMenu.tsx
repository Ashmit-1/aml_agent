import { useState, useRef, useEffect } from 'react';
import { useAuthStore } from '@/store/authStore';
import { LogOut, User } from 'lucide-react';

interface UserMenuProps {
  /** Position the dropdown to the left instead of right */
  align?: 'left' | 'right';
}

export const UserMenu = ({ align = 'right' }: UserMenuProps) => {
  const { user, logout } = useAuthStore();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  if (!user) return null;

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-md border border-white/10 hover:bg-white/5 transition-colors text-sm"
      >
        <User size={14} className="text-gray-400" />
        <span className="text-white max-w-[120px] truncate">{user.username}</span>
      </button>

      {open && (
        <div
          className={`absolute top-full mt-1 ${align === 'right' ? 'right-0' : 'left-0'} min-w-[140px] bg-black border border-white/10 rounded-md shadow-lg z-50 py-1`}
        >
          <div className="px-3 py-2 text-xs text-gray-500 border-b border-white/10">
            Signed in as <span className="text-white font-medium">{user.username}</span>
          </div>
          <button
            onClick={logout}
            className="flex items-center gap-2 w-full px-3 py-2 text-sm text-red-400 hover:bg-white/5 transition-colors"
          >
            <LogOut size={14} />
            <span>Logout</span>
          </button>
        </div>
      )}
    </div>
  );
};
