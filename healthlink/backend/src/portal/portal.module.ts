import { Module } from '@nestjs/common';
import { DoctorPortalController, AdminPortalController } from './portal.controller';
import { PortalService } from './portal.service';
@Module({ controllers: [DoctorPortalController, AdminPortalController], providers: [PortalService] })
export class PortalModule {}
