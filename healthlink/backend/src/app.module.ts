import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { ConsultationsModule } from './consultations/consultations.module';
import { DoctorsModule } from './doctors/doctors.module';
import { PrismaModule } from './prisma/prisma.module';
import { AuthModule } from './auth/auth.module';
import { PortalModule } from './portal/portal.module';

@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true }),
    PrismaModule,
    AuthModule,
    PortalModule,
    DoctorsModule,
    ConsultationsModule,
  ],
})
export class AppModule {}
