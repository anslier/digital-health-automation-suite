import {
  BadRequestException,
  ConflictException,
  Injectable,
  NotFoundException,
} from '@nestjs/common';
import { ConsultationStatus, Prisma } from '@prisma/client';
import { PrismaService } from '../prisma/prisma.service';
import { CreateConsultationDto } from './dto/create-consultation.dto';

@Injectable()
export class ConsultationsService {
  constructor(private readonly prisma: PrismaService) {}

  private async getPatient(userId: string) {
    const patient = await this.prisma.patient.findFirst({
      where: { userId },
      include: { user: true },
    });
    if (!patient) {
      throw new NotFoundException('Patient profile not found');
    }
    return patient;
  }

  async listForPatient(userId: string) {
    const patient = await this.getPatient(userId);
    const consultations = await this.prisma.consultation.findMany({
      where: { patientId: patient.id },
      include: { doctor: { include: { user: true } } },
      orderBy: { preferredTime: 'desc' },
    });

    return consultations.map((consultation) => ({
      id: consultation.id,
      doctorId: consultation.doctorId,
      doctorName: consultation.doctor.user.name,
      specialty: consultation.doctor.specialty,
      type: consultation.type,
      preferredTime: consultation.preferredTime,
      reasonForVisit: consultation.reasonForVisit,
      status: consultation.status,
      createdAt: consultation.createdAt,
    }));
  }

  async createForPatient(userId: string, dto: CreateConsultationDto) {
    const patient = await this.getPatient(userId);
    const preferredTime = new Date(dto.preferredTime);

    if (Number.isNaN(preferredTime.getTime()) || preferredTime <= new Date()) {
      throw new BadRequestException('Preferred time must be in the future');
    }

    const doctor = await this.prisma.doctor.findFirst({
      where: { id: dto.doctorId, active: true },
    });
    if (!doctor) {
      throw new NotFoundException('Doctor not found');
    }

    const availability = await this.prisma.availability.findFirst({
      where: {
        doctorId: dto.doctorId,
        startTime: preferredTime,
        isBooked: false,
      },
    });
    if (!availability) {
      throw new ConflictException('That appointment slot is no longer available');
    }

    try {
      const consultation = await this.prisma.$transaction(async (tx) => {
        const claimed = await tx.availability.updateMany({
          where: { id: availability.id, isBooked: false },
          data: { isBooked: true },
        });

        if (claimed.count !== 1) {
          throw new ConflictException('That appointment slot was just booked');
        }

        return tx.consultation.create({
          data: {
            patientId: patient.id,
            doctorId: dto.doctorId,
            type: dto.type,
            preferredTime,
            reasonForVisit: dto.reasonForVisit.trim(),
            status: ConsultationStatus.SCHEDULED,
          },
          include: { doctor: { include: { user: true } } },
        });
      });

      return {
        id: consultation.id,
        doctorId: consultation.doctorId,
        doctorName: consultation.doctor.user.name,
        specialty: consultation.doctor.specialty,
        type: consultation.type,
        preferredTime: consultation.preferredTime,
        reasonForVisit: consultation.reasonForVisit,
        status: consultation.status,
        createdAt: consultation.createdAt,
      };
    } catch (error) {
      if (error instanceof ConflictException) {
        throw error;
      }
      if (error instanceof Prisma.PrismaClientKnownRequestError && error.code === 'P2002') {
        throw new ConflictException('That appointment slot is already booked');
      }
      throw error;
    }
  }
}
