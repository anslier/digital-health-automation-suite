import { inject, Injectable, signal } from '@angular/core';
import { HttpClient, HttpInterceptorFn } from '@angular/common/http';
import { catchError, tap, throwError } from 'rxjs';
import { SessionUser, UserRole } from '../models';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  readonly user = signal<SessionUser | null>(null);
  restore() { return this.http.get<SessionUser>('/api/auth/me').pipe(tap(user => this.user.set(user))); }
  login(email: string, password: string, role: UserRole) {
    return this.http.post<SessionUser>('/api/auth/login', { email, password, role }).pipe(tap(user => this.user.set(user)));
  }
  logout() { return this.http.post('/api/auth/logout', {}).pipe(tap(() => this.user.set(null))); }
}

export const sessionInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  return next(req).pipe(catchError(error => {
    if (error.status === 401 && !req.url.endsWith('/auth/login')) auth.user.set(null);
    return throwError(() => error);
  }));
};
