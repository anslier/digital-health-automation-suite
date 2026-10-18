import { Body, Controller, Delete, Get, Param, Patch, Post, Req } from '@nestjs/common';
import { Role } from '@prisma/client';
import { IsBoolean, IsIn, IsISO8601 } from 'class-validator';
import { Roles } from '../auth/auth.decorators';
import { AuthRequest } from '../auth/auth.types';
import { PortalService } from './portal.service';

class StatusDto { @IsIn(['SCHEDULED', 'COMPLETED']) status: 'SCHEDULED' | 'COMPLETED'; }
class AvailabilityDto { @IsISO8601() startTime: string; @IsISO8601() endTime: string; }
class VisibilityDto { @IsBoolean() active: boolean; }

@Controller('doctor')
@Roles(Role.DOCTOR)
export class DoctorPortalController {
  constructor(private readonly portal: PortalService) {}
  @Get('dashboard') dashboard(@Req() req: AuthRequest) { return this.portal.doctorDashboard(req.user.id); }
  @Patch('consultations/:id/status') status(@Req() req: AuthRequest, @Param('id') id: string, @Body() dto: StatusDto) { return this.portal.updateStatus(req.user.id, id, dto.status); }
  @Post('availability') availability(@Req() req: AuthRequest, @Body() dto: AvailabilityDto) { return this.portal.addAvailability(req.user.id, dto.startTime, dto.endTime); }
  @Delete('availability/:id') remove(@Req() req: AuthRequest, @Param('id') id: string) { return this.portal.removeAvailability(req.user.id, id); }
}

@Controller('admin')
@Roles(Role.ADMIN)
export class AdminPortalController {
  constructor(private readonly portal: PortalService) {}
  @Get('dashboard') dashboard() { return this.portal.adminDashboard(); }
  @Patch('doctors/:id') visibility(@Param('id') id: string, @Body() dto: VisibilityDto) { return this.portal.setDoctorActive(id, dto.active); }
}
