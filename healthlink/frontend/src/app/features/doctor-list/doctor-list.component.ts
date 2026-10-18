import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { Doctor } from '../../models';

@Component({
  selector: 'app-doctor-list',
  standalone: true,
  imports: [CommonModule],
  template: `
    <section class="panel doctors-panel">
      <div class="section-heading">
        <div>
          <span class="eyebrow">AVAILABLE DOCTORS</span>
          <h2>Find the right doctor</h2>
        </div>
        <span class="count-pill">{{ doctors.length }} doctors</span>
      </div>

      <div class="doctor-list" *ngIf="doctors.length; else empty">
        <article class="doctor-card" *ngFor="let doctor of doctors">
          <div class="avatar" aria-hidden="true">{{ initials(doctor.name) }}</div>
          <div class="doctor-info">
            <h3>{{ doctor.name }}</h3>
            <p class="specialty">{{ doctor.specialty }}</p>
            <p class="bio">{{ doctor.bio }}</p>
            <div class="availability-row">
              <span class="status-dot"></span>
              <span *ngIf="doctor.availability.length; else unavailable">
                {{ doctor.availability.length }} upcoming slots · next {{ doctor.availability[0].startTime | date:'EEE, d MMM · h:mm a' }}
              </span>
              <ng-template #unavailable>No open slots</ng-template>
            </div>
          </div>
          <button
            class="primary-button compact"
            type="button"
            [disabled]="doctor.availability.length === 0"
            (click)="book.emit(doctor)"
          >
            Book Consultation
          </button>
        </article>
      </div>

      <ng-template #empty>
        <div class="empty-state">No doctors are currently available.</div>
      </ng-template>
    </section>
  `,
  styles: [`
    .doctors-panel { min-width: 0; }
    .doctor-list { display: grid; gap: 14px; }
    .doctor-card { display: grid; grid-template-columns: 54px minmax(0,1fr) auto; gap: 14px; align-items: center; padding: 18px; border: 1px solid var(--line); border-radius: 18px; background: #fff; transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease; }
    .doctor-card:hover { transform: translateY(-1px); box-shadow: 0 12px 28px rgba(16,68,101,.08); border-color: #bfddea; }
    .avatar { width: 54px; height: 54px; border-radius: 50%; display: grid; place-items: center; font-weight: 800; color: #0879bd; background: linear-gradient(145deg,#e6f7ff,#dff8f0); }
    .doctor-info { min-width: 0; }
    h3 { margin: 0 0 3px; font-size: 1rem; }
    .specialty { margin: 0; color: var(--primary); font-size: .86rem; font-weight: 700; }
    .bio { margin: 7px 0 8px; color: var(--muted); font-size: .86rem; line-height: 1.45; }
    .availability-row { display: flex; align-items: center; gap: 7px; color: #36705e; font-size: .78rem; }
    .status-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--success); box-shadow: 0 0 0 4px rgba(27,177,124,.1); }
    .count-pill { border: 1px solid var(--line); background: var(--soft); color: var(--muted); border-radius: 999px; padding: 7px 11px; font-size: .78rem; white-space: nowrap; }
    @media (max-width: 700px) {
      .doctor-card { grid-template-columns: 48px 1fr; }
      .avatar { width: 48px; height: 48px; }
      .doctor-card .primary-button { grid-column: 1 / -1; width: 100%; }
      .bio { display: none; }
    }
  `],
})
export class DoctorListComponent {
  @Input({ required: true }) doctors: Doctor[] = [];
  @Output() book = new EventEmitter<Doctor>();

  initials(name: string): string {
    return name.replace(/^Dr\.\s*/i, '').split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase();
  }
}
