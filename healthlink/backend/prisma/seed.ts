import {
  ConsultationStatus,
  ConsultationType,
  PrismaClient,
  Role,
} from '@prisma/client';

const prisma = new PrismaClient();
import { randomBytes, scryptSync } from 'node:crypto';
const DEMO_PASSWORD = 'healthlink-demo-2026';
function demoPasswordHash() {
  const salt = randomBytes(16).toString('hex');
  return `${salt}:${scryptSync(DEMO_PASSWORD, salt, 64).toString('hex')}`;
}

function utcDayStart(date = new Date()): Date {
  return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()));
}

function addDays(date: Date, days: number): Date {
  const next = new Date(date);
  next.setUTCDate(next.getUTCDate() + days);
  return next;
}

function atUtc(day: Date, hour: number, minute = 0): Date {
  const next = new Date(day);
  next.setUTCHours(hour, minute, 0, 0);
  return next;
}

async function upsertDoctor(email: string, name: string, specialty: string, bio: string) {
  const user = await prisma.user.upsert({
    where: { email },
    update: { name, role: Role.DOCTOR },
    create: { email, name, role: Role.DOCTOR },
  });

  return prisma.doctor.upsert({
    where: { userId: user.id },
    update: { specialty, bio },
    create: { userId: user.id, specialty, bio },
  });
}

async function main() {
  const patientUser = await prisma.user.upsert({
    where: { email: 'john@healthlink.local' },
    update: { name: 'John', role: Role.PATIENT },
    create: { email: 'john@healthlink.local', name: 'John', role: Role.PATIENT },
  });

  const patient = await prisma.patient.upsert({
    where: { userId: patientUser.id },
    update: { phone: '+60 12-345 6789' },
    create: { userId: patientUser.id, phone: '+60 12-345 6789' },
  });

  const doctors = await Promise.all([
    upsertDoctor(
      'sarah.lim@healthlink.local',
      'Dr. Sarah Lim',
      'General Practitioner',
      'Primary care, preventive health and everyday medical concerns.',
    ),
    upsertDoctor(
      'aiman.rashid@healthlink.local',
      'Dr. Aiman Rashid',
      'Family Medicine',
      'Continuity-focused family care for adults and children.',
    ),
    upsertDoctor(
      'priya.nair@healthlink.local',
      'Dr. Priya Nair',
      'Internal Medicine',
      'Adult medicine with a focus on chronic-condition management.',
    ),
  ]);

  await prisma.user.upsert({ where: { email: 'admin@healthlink.local' }, update: {}, create: { email: 'admin@healthlink.local', name: 'HealthLink Admin', role: Role.ADMIN, passwordHash: demoPasswordHash() } });
  const secondPatient = await prisma.user.upsert({ where: { email: 'ahmad@healthlink.local' }, update: { name: 'Ahmad', role: Role.PATIENT }, create: { email: 'ahmad@healthlink.local', name: 'Ahmad', role: Role.PATIENT, passwordHash: demoPasswordHash() } });
  await prisma.patient.upsert({ where: { userId: secondPatient.id }, update: {}, create: { userId: secondPatient.id } });
  for (const email of ['john@healthlink.local', 'sarah.lim@healthlink.local', 'aiman.rashid@healthlink.local', 'priya.nair@healthlink.local']) {
    await prisma.user.updateMany({ where: { email, passwordHash: null }, data: { passwordHash: demoPasswordHash() } });
  }

  const day0 = utcDayStart();
  const slotHours = [1, 6, 9]; // 09:00, 14:00, 17:00 in Malaysia/Singapore (UTC+8)

  for (let offset = 1; offset <= 7; offset += 1) {
    const day = addDays(day0, offset);
    for (const doctor of doctors) {
      for (const hour of slotHours) {
        const startTime = atUtc(day, hour, 0);
        const endTime = new Date(startTime.getTime() + 30 * 60 * 1000);
        await prisma.availability.upsert({
          where: {
            doctorId_startTime: {
              doctorId: doctor.id,
              startTime,
            },
          },
          update: { endTime },
          create: {
            doctorId: doctor.id,
            startTime,
            endTime,
          },
        });
      }
    }
  }

  // Populate the two consultation states for a fresh demo. Retain existing history on restart.
  if (await prisma.consultation.count({ where: { patientId: patient.id } }) === 0) {
    await prisma.consultation.create({
      data: {
        patientId: patient.id,
        doctorId: doctors[2].id,
        type: ConsultationType.CHAT,
        preferredTime: atUtc(addDays(day0, -2), 6),
        reasonForVisit: 'Follow-up on recent blood test results.',
        status: ConsultationStatus.COMPLETED,
      },
    });
    const scheduledAt = atUtc(addDays(day0, 1), slotHours[0]);
    const slot = await prisma.availability.findUnique({
      where: { doctorId_startTime: { doctorId: doctors[0].id, startTime: scheduledAt } },
    });
    if (slot && !slot.isBooked) {
      await prisma.$transaction(async tx => {
        const claimed = await tx.availability.updateMany({
          where: { id: slot.id, isBooked: false }, data: { isBooked: true },
        });
        if (claimed.count === 1) {
          await tx.consultation.create({
            data: {
              patientId: patient.id,
              doctorId: doctors[0].id,
              type: ConsultationType.VIDEO,
              preferredTime: scheduledAt,
              reasonForVisit: 'Persistent cough and mild fever for three days.',
              status: ConsultationStatus.SCHEDULED,
            },
          });
        }
      });
    }
  }

  console.log('HealthLink seed complete.');
}

main()
  .catch((error) => {
    console.error(error);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
