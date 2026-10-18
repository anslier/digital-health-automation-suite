import { ConsultationType } from '@prisma/client';
import { IsEnum, IsISO8601, IsString, MaxLength, MinLength } from 'class-validator';
import { Transform } from 'class-transformer';

export class CreateConsultationDto {
  @IsString()
  doctorId: string;

  @IsEnum(ConsultationType)
  type: ConsultationType;

  @IsISO8601()
  preferredTime: string;

  @IsString()
  @MinLength(5)
  @MaxLength(500)
  @Transform(({ value }) => typeof value === 'string' ? value.trim() : value)
  reasonForVisit: string;
}
