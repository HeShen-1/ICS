import { request } from './client';

interface RegisterParams {
  phone: string;
  password: string;
}

interface LoginParams {
  account: string;
  password: string;
}

interface AuthResponse {
  token: string;
  user_id: number;
  message: string;
}

export async function register(params: RegisterParams): Promise<AuthResponse> {
  return request('/auth/register', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

export async function login(params: LoginParams): Promise<AuthResponse> {
  return request('/auth/login', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}
