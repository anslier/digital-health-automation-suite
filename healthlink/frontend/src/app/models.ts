export type ConsultationType = 'CHAT' | 'VIDEO';
export type ConsultationStatus = 'SCHEDULED' | 'COMPLETED';
export type UserRole = 'PATIENT' | 'DOCTOR' | 'ADMIN';
export interface SessionUser { id: string; name: string; email: string; role: UserRole }

export interface PortalConsultation extends Consultation { patientName: string }
export interface DoctorDashboard {
  doctor: { id: string; name: string; specialty: string; active: boolean };
  consultations: PortalConsultation[];
  availability: (AvailabilitySlot & { isBooked: boolean })[];
}
export interface AdminDashboard {
  doctors: { id: string; name: string; email: string; specialty: string; active: boolean; consultationCount: number }[];
  patients: { id: string; name: string; email: string; consultationCount: number }[];
  consultations: PortalConsultation[];
}

export interface AvailabilitySlot {
  id: string;
  startTime: string;
  endTime: string;
}

export interface Doctor {
  id: string;
  name: string;
  specialty: string;
  bio: string | null;
  availability: AvailabilitySlot[];
}

export interface Consultation {
  id: string;
  doctorId: string;
  doctorName: string;
  specialty: string;
  type: ConsultationType;
  preferredTime: string;
  reasonForVisit: string;
  status: ConsultationStatus;
  createdAt: string;
}

export interface CreateConsultationRequest {
  doctorId: string;
  type: ConsultationType;
  preferredTime: string;
  reasonForVisit: string;
}
