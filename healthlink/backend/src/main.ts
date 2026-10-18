import { ValidationPipe } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { Request, Response, NextFunction } from 'express';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.setGlobalPrefix('api');
  const origins = (process.env.ALLOWED_ORIGINS ?? 'http://localhost:4200,http://127.0.0.1:4200').split(',');
  app.enableCors({ origin: origins, credentials: true });
  app.use((request: Request, response: Response, next: NextFunction) => {
    if (!['GET', 'HEAD', 'OPTIONS'].includes(request.method) && request.headers.origin && !origins.includes(request.headers.origin)) {
      response.status(403).json({ message: 'Untrusted request origin' });
      return;
    }
    next();
  });
  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,
      forbidNonWhitelisted: true,
      transform: true,
    }),
  );

  const port = Number(process.env.PORT ?? 3000);
  await app.listen(port, '0.0.0.0');
  console.log(`HealthLink API listening on port ${port}`);
}

bootstrap();
