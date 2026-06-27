import { create } from 'zustand';
import type { Session } from '../api/sessions';

interface SessionState {
  sessions: Session[];
  setSessions: (sessions: Session[]) => void;
  addSession: (session: Session) => void;
  updateSession: (id: number, patch: Partial<Session>) => void;
  removeSession: (id: number) => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  sessions: [],
  setSessions: (sessions) => set({ sessions }),
  addSession: (session) =>
    set((s) => {
      const all = [session, ...s.sessions];
      // 置顶优先, 同组内 updated_at 降序
      all.sort((a, b) => {
        if (a.pinned !== b.pinned) return a.pinned ? -1 : 1;
        return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
      });
      return { sessions: all };
    }),
  updateSession: (id, patch) =>
    set((s) => ({
      sessions: s.sessions.map((ss) => (ss.id === id ? { ...ss, ...patch } : ss)),
    })),
  removeSession: (id) =>
    set((s) => ({
      sessions: s.sessions.filter((ss) => ss.id !== id),
    })),
}));
