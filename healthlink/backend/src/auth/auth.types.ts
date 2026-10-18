import { Role } from '@prisma/client';
import { Request } from 'express';

export interface SessionUser { id: string; email: string; name: string; role: Role }
export interface AuthRequest extends Request { user: SessionUser }
