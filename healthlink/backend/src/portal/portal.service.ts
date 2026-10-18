import { BadRequestException, ConflictException, Injectable, NotFoundException } from '@nestjs/common';
import { Prisma } from '@prisma/client';
import { PrismaService } from '../prisma/prisma.service';

const consultationInclude = { patient: { include: { user: true } }, doctor: { include: { user: true } } } as const;
type ConsultationDetails = Prisma.ConsultationGetPayload<{ include: typeof consultationInclude }>;
const consultationView = (c: ConsultationDetails) => ({ id: c.id, doctorId: c.doctorId, doctorName: c.doctor.user.name, patientName: c.patient.user.name, type: c.type, preferredTime: c.preferredTime, reasonForVisit: c.reasonForVisit, status: c.status });

@Injectable()
export class PortalService {
  constructor(private readonly prisma: PrismaService) {}
  private async doctorForUser(userId: string) {
    const doctor = await this.prisma.doctor.findUnique({ where: { userId }, include: { user: true } });
    if (!doctor) throw new NotFoundException('Doctor profile not found');
    return doctor;
  }
  async doctorDashboard(userId: string) {
    const doctor = await this.doctorForUser(userId);
    const [consultations, availability] = await Promise.all([
      this.prisma.consultation.findMany({ where: { doctorId: doctor.id }, include: consultationInclude, orderBy: { preferredTime: 'desc' } }),
      this.prisma.availability.findMany({ where: { doctorId: doctor.id, startTime: { gt: new Date() } }, orderBy: { startTime: 'asc' } }),
    ]);
    return { doctor: { id: doctor.id, name: doctor.user.name, specialty: doctor.specialty, active: doctor.active }, consultations: consultations.map(consultationView), availability };
  }
  async updateStatus(userId: string, id: string, status: 'SCHEDULED' | 'COMPLETED') {
    const doctor = await this.doctorForUser(userId);
    const changed = await this.prisma.consultation.updateMany({ where: { id, doctorId: doctor.id }, data: { status } });
    if (!changed.count) throw new NotFoundException('Appointment not found');
    return { id, status };
  }
  async addAvailability(userId: string, startTime: string, endTime: string) {
    const doctor = await this.doctorForUser(userId);
    const start = new Date(startTime), end = new Date(endTime);
    if (start <= new Date() || end <= start || end.getTime() - start.getTime() > 4 * 3600000) {
      throw new BadRequestException('Choose a future slot ending after its start, up to four hours long');
    }
    try {
      // Serialize availability writers for this doctor before checking overlaps.
      return await this.prisma.$transaction(async tx => {
        await tx.$queryRaw`SELECT id FROM "Doctor" WHERE id = ${doctor.id} FOR UPDATE`;
        const overlap = await tx.availability.findFirst({ where: { doctorId: doctor.id, startTime: { lt: end }, endTime: { gt: start } } });
        if (overlap) throw new ConflictException('This time overlaps an existing slot');
        return tx.availability.create({ data: { doctorId: doctor.id, startTime: start, endTime: end } });
      });
    } catch (error) {
      if (error instanceof Prisma.PrismaClientKnownRequestError && error.code === 'P2002') throw new ConflictException('Slot already exists');
      throw error;
    }
  }
  async removeAvailability(userId: string, id: string) {
    const doctor = await this.doctorForUser(userId);
    const slot = await this.prisma.availability.findFirst({ where: { id, doctorId: doctor.id } });
    if (!slot) throw new NotFoundException('Slot not found');
    const removed = await this.prisma.availability.deleteMany({ where: { id, doctorId: doctor.id, isBooked: false } });
    if (!removed.count) throw new ConflictException('Booked slots cannot be removed');
    return { id, removed: true };
  }
  async adminDashboard() {
    const [doctors, patients, consultations] = await Promise.all([
      this.prisma.doctor.findMany({ include: { user: true, _count: { select: { consultations: true } } }, orderBy: { user: { name: 'asc' } } }),
      this.prisma.patient.findMany({ include: { user: true, _count: { select: { consultations: true } } }, orderBy: { user: { name: 'asc' } } }),
      this.prisma.consultation.findMany({ include: consultationInclude, orderBy: { preferredTime: 'desc' } }),
    ]);
    return {
      doctors: doctors.map(d => ({ id: d.id, name: d.user.name, email: d.user.email, specialty: d.specialty, active: d.active, consultationCount: d._count.consultations })),
      patients: patients.map(p => ({ id: p.id, name: p.user.name, email: p.user.email, consultationCount: p._count.consultations })),
      consultations: consultations.map(consultationView),
    };
  }
  async setDoctorActive(id: string, active: boolean) {
    const changed = await this.prisma.doctor.updateMany({ where: { id }, data: { active } });
    if (!changed.count) throw new NotFoundException('Doctor not found');
    return { id, active };
  }
}
