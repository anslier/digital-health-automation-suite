import { Injectable, UnauthorizedException } from '@nestjs/common';
import { Role } from '@prisma/client';
import { createHash, randomBytes } from 'node:crypto';
import { Request } from 'express';
import { PrismaService } from '../prisma/prisma.service';
import { verifyPassword } from './password';

export const SESSION_COOKIE = 'healthlink_session';
const digest = (value: string) => createHash('sha256').update(value).digest('hex');

@Injectable()
export class AuthService {
  constructor(private readonly prisma: PrismaService) {}

  token(request: Request): string | undefined {
    const value = request.headers.cookie?.split(';').map(part => part.trim()).find(part => part.startsWith(`${SESSION_COOKIE}=`))?.slice(SESSION_COOKIE.length + 1);
    return value && /^[a-f0-9]{64}$/.test(value) ? value : undefined;
  }

  async login(email: string, password: string, role: Role) {
    const user = await this.prisma.user.findUnique({ where: { email: email.trim().toLowerCase() } });
    if (!user || user.role !== role || !verifyPassword(password, user.passwordHash)) {
      throw new UnauthorizedException('Email, password, or selected role is incorrect');
    }
    const token = randomBytes(32).toString('hex');
    await this.prisma.authSession.deleteMany({ where: { expiresAt: { lte: new Date() } } });
    await this.prisma.authSession.create({ data: { tokenHash: digest(token), userId: user.id, expiresAt: new Date(Date.now() + 12 * 3600000) } });
    return { token, user: { id: user.id, email: user.email, name: user.name, role: user.role } };
  }

  async authenticate(request: Request) {
    const token = this.token(request);
    if (!token) throw new UnauthorizedException('Please sign in');
    const session = await this.prisma.authSession.findUnique({ where: { tokenHash: digest(token) }, include: { user: true } });
    if (!session || session.expiresAt <= new Date()) throw new UnauthorizedException('Session expired. Please sign in again');
    const { id, email, name, role } = session.user;
    return { id, email, name, role };
  }

  async logout(request: Request) {
    const token = this.token(request);
    if (token) await this.prisma.authSession.deleteMany({ where: { tokenHash: digest(token) } });
  }
}
