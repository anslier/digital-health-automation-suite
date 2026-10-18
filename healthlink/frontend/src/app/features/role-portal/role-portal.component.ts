import { CommonModule } from '@angular/common';
import { Component, inject, Input, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { AdminDashboard, DoctorDashboard, PortalConsultation, UserRole } from '../../models';

@Component({ selector: 'app-role-portal', standalone: true, imports: [CommonModule, FormsModule], templateUrl: './role-portal.component.html', styleUrl: './role-portal.component.scss' })
export class RolePortalComponent implements OnInit {
  @Input({ required: true }) role!: UserRole;
  private readonly http = inject(HttpClient);
  doctor: DoctorDashboard | null = null;
  admin: AdminDashboard | null = null;
  busy = false; loading = true; error = ''; success = '';
  startTime = ''; endTime = '';
  get appointments(): PortalConsultation[] { return this.doctor?.consultations ?? this.admin?.consultations ?? []; }
  get scheduledCount() { return this.appointments.filter(c => c.status === 'SCHEDULED').length; }
  get freeSlotCount() { return this.doctor?.availability.filter(slot => !slot.isBooked).length ?? 0; }
  ngOnInit() { this.refresh(); }
  refresh() {
    this.error = ''; this.loading = true;
    if (this.role === 'DOCTOR') this.http.get<DoctorDashboard>('/api/doctor/dashboard').subscribe({ next: data => { this.doctor = data; this.loading = false; }, error: e => this.failed(e) });
    else this.http.get<AdminDashboard>('/api/admin/dashboard').subscribe({ next: data => { this.admin = data; this.loading = false; }, error: e => this.failed(e) });
  }
  private failed(e: any) { this.busy = false; this.loading = false; this.error = e.error?.message ?? 'Unable to complete the request.'; }
  complete(c: PortalConsultation) {
    if (this.busy) return; this.busy = true;
    this.http.patch('/api/doctor/consultations/' + c.id + '/status', { status: 'COMPLETED' }).subscribe({ next: () => { this.busy = false; this.success = 'Appointment marked completed.'; this.refresh(); }, error: e => this.failed(e) });
  }
  addSlot() {
    if (!this.startTime || !this.endTime || this.busy) return;
    const start = new Date(this.startTime), end = new Date(this.endTime);
    if (isNaN(start.getTime()) || isNaN(end.getTime())) { this.error = 'Choose a start and end time.'; return; }
    this.busy = true;
    this.http.post('/api/doctor/availability', { startTime: start.toISOString(), endTime: end.toISOString() }).subscribe({ next: () => { this.busy = false; this.startTime = ''; this.endTime = ''; this.success = 'New availability saved.'; this.refresh(); }, error: e => this.failed(e) });
  }
  removeSlot(id: string) {
    if (this.busy) return; this.busy = true;
    this.http.delete('/api/doctor/availability/' + id).subscribe({ next: () => { this.busy = false; this.success = 'Free slot removed.'; this.refresh(); }, error: e => this.failed(e) });
  }
  toggleDoctor(d: AdminDashboard['doctors'][number]) {
    if (this.busy) return; this.busy = true;
    this.http.patch('/api/admin/doctors/' + d.id, { active: !d.active }).subscribe({ next: () => { this.busy = false; this.success = d.active ? 'Doctor hidden from new patient bookings.' : 'Doctor available for new patient bookings.'; this.refresh(); }, error: e => this.failed(e) });
  }
}
