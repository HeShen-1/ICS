import { create } from 'zustand';
import { login as apiLogin, register as apiRegister } from '../api/auth';

interface AuthState {
  token: string | null;
  userId: number | null;
  isAuthenticated: boolean;
  login: (account: string, password: string) => Promise<void>;
  register: (phone: string | undefined, email: string | undefined, password: string) => Promise<void>;
  logout: () => void;
  init: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  userId: null,
  isAuthenticated: false,

  login: async (account, password) => {
    const res = await apiLogin({ account, password });
    localStorage.setItem('token', res.token);
    localStorage.setItem('userId', String(res.user_id));
    set({ token: res.token, userId: res.user_id, isAuthenticated: true });
  },

  register: async (phone, email, password) => {
    const res = await apiRegister({ phone, email, password });
    localStorage.setItem('token', res.token);
    localStorage.setItem('userId', String(res.user_id));
    set({ token: res.token, userId: res.user_id, isAuthenticated: true });
  },

  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('userId');
    set({ token: null, userId: null, isAuthenticated: false });
  },

  init: () => {
    const token = localStorage.getItem('token');
    const userId = localStorage.getItem('userId');
    if (token) {
      set({ token, userId: userId ? Number(userId) : null, isAuthenticated: true });
    }
  },
}));
