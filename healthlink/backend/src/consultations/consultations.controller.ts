import { Body, Controller, Get, Post, Req } from '@nestjs/common';
import { Role } from '@prisma/client';
import { Roles } from '../auth/auth.decorators';
import { AuthRequest } from '../auth/auth.types';
import { CreateConsultationDto } from './dto/create-consultation.dto';
import { ConsultationsService } from './consultations.service';

@Controller('consultations')
@Roles(Role.PATIENT)
export class ConsultationsController {
  constructor(private readonly consultationsService: ConsultationsService) {}

  @Get()
  list(@Req() request: AuthRequest) {
    return this.consultationsService.listForPatient(request.user.id);
  }

  @Post()
  create(@Req() request: AuthRequest, @Body() dto: CreateConsultationDto) {
    return this.consultationsService.createForPatient(request.user.id, dto);
  }
}
