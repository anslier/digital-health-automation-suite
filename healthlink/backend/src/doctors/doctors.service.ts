import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';

@Injectable()
export class DoctorsService {
  constructor(private readonly prisma: PrismaService) {}

  async listAvailableDoctors() {
    const now = new Date();
    const doctors = await this.prisma.doctor.findMany({
      where: { active: true },
      include: {
        user: true,
        availabilities: {
          where: {
            isBooked: false,
            startTime: { gt: now },
          },
          orderBy: { startTime: 'asc' },
          take: 12,
        },
      },
      orderBy: { user: { name: 'asc' } },
    });

    return doctors.map((doctor) => ({
      id: doctor.id,
      name: doctor.user.name,
      specialty: doctor.specialty,
      bio: doctor.bio,
      availability: doctor.availabilities.map((slot) => ({
        id: slot.id,
        startTime: slot.startTime,
        endTime: slot.endTime,
      })),
    }));
  }
}
