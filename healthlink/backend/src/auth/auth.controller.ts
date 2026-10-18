import { Body, Controller, Get, Post, Req, Res } from '@nestjs/common';
import { Role } from '@prisma/client';
import { IsEmail, IsEnum, IsString, MaxLength, MinLength } from 'class-validator';
import { Request, Response } from 'express';
import { Public } from './auth.decorators';
import { AuthRequest } from './auth.types';
import { AuthService, SESSION_COOKIE } from './auth.service';

class LoginDto {
  @IsEmail() email: string;
  @IsString() @MinLength(1) @MaxLength(200) password: string;
  @IsEnum(Role) role: Role;
}

@Controller('auth')
export class AuthController {
  constructor(private readonly auth: AuthService) {}
  @Public() @Post('login')
  async login(@Body() dto: LoginDto, @Req() req: Request, @Res({ passthrough: true }) response: Response) {
    const result = await this.auth.login(dto.email, dto.password, dto.role);
    await this.auth.logout(req);
    response.cookie(SESSION_COOKIE, result.token, { httpOnly: true, sameSite: 'lax', secure: process.env.COOKIE_SECURE === 'true', maxAge: 12 * 3600000, path: '/' });
    response.status(200);
    return result.user;
  }
  @Get('me') me(@Req() request: AuthRequest) { return request.user; }
  @Public() @Post('logout')
  async logout(@Req() request: Request, @Res({ passthrough: true }) response: Response) {
    await this.auth.logout(request);
    response.clearCookie(SESSION_COOKIE, { path: '/', httpOnly: true, sameSite: 'lax', secure: process.env.COOKIE_SECURE === 'true' });
    response.status(200);
    return { status: 'ok' };
  }
}
