import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { forkJoin } from 'rxjs';
import { ApiService } from './core/api.service';
import { BookingPanelComponent } from './features/booking-panel/booking-panel.component';
import { ConsultationListComponent } from './features/consultation-list/consultation-list.component';
import { DoctorListComponent } from './features/doctor-list/doctor-list.component';
import { Consultation, Doctor, SessionUser } from './models';
import { AuthService } from './core/auth.service';
import { SignInComponent } from './features/sign-in/sign-in.component';
import { RolePortalComponent } from './features/role-portal/role-portal.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, DoctorListComponent, ConsultationListComponent, BookingPanelComponent, SignInComponent, RolePortalComponent],
  template: `
    <p class="loading-card session-loading" *ngIf="sessionLoading">Opening HealthLink...</p>
    <app-sign-in *ngIf="!sessionLoading && !user" (signedIn)="signedIn($event)" />
    <header class="topbar" *ngIf="user">
      <div class="brand"><span class="brand-mark">♥</span><strong>HealthLink</strong></div>
      <nav *ngIf="user.role === 'PATIENT'"><a href="#doctors">Doctors</a><a href="#consultations">Consultations</a></nav>
      <nav *ngIf="user.role !== 'PATIENT'"><span>{{ user.role === 'DOCTOR' ? 'Doctor workspace' : 'Admin workspace' }}</span></nav>
      <div class="profile"><span class="profile-avatar">{{ initials(user.name) }}</span><div><strong>{{ user.name }}</strong><small>{{ user.role | titlecase }}</small></div><button class="sign-out" type="button" (click)="signOut()">Sign out</button></div>
    </header>

    <main class="page-shell" *ngIf="user">
      <ng-container *ngIf="user.role === 'PATIENT'">
      <section class="hero">
        <div>
          <span class="hero-kicker">WELCOME TO HEALTHLINK</span>
          <h1>Consult a Doctor</h1>
          <p>Book a private chat or video consultation with an available doctor.</p>
        </div>
        <div class="hero-art" aria-hidden="true">
          <div class="pulse-ring"><span>+</span></div>
        </div>
      </section>

      <div class="notice error" *ngIf="loadError">{{ loadError }}</div>
      <div class="notice success" *ngIf="successMessage">{{ successMessage }}</div>
      <div class="loading-card" *ngIf="loading">Loading HealthLink...</div>

      <div class="content-grid" *ngIf="!loading">
        <div id="doctors">
          <app-doctor-list [doctors]="doctors" (book)="selectedDoctor = $event" />
        </div>
        <div id="consultations">
          <app-consultation-list [consultations]="consultations" />
        </div>
      </div>
      </ng-container>
      <app-role-portal *ngIf="user.role !== 'PATIENT'" [role]="user.role" />
    </main>

    <app-booking-panel
      *ngIf="selectedDoctor && user?.role === 'PATIENT'"
      [doctor]="selectedDoctor"
      (closed)="selectedDoctor = null"
      (booked)="bookingCompleted($event)"
    />
  `,
})
export class AppComponent implements OnInit {
  private readonly api = inject(ApiService);
  private readonly auth = inject(AuthService);
  sessionLoading = true;
  get user() { return this.auth.user(); }

  doctors: Doctor[] = [];
  consultations: Consultation[] = [];
  selectedDoctor: Doctor | null = null;
  loading = true;
  loadError = '';
  successMessage = '';

  ngOnInit(): void {
    this.auth.restore().subscribe({ next: user => { this.sessionLoading = false; this.signedIn(user); }, error: () => { this.sessionLoading = false; } });
  }

  signedIn(user: SessionUser) {
    this.selectedDoctor = null; this.successMessage = ''; this.loadError = '';
    this.doctors = []; this.consultations = [];
    if (user.role === 'PATIENT') this.refresh();
  }

  signOut() {
    this.auth.logout().subscribe({ next: () => { this.selectedDoctor = null; this.doctors = []; this.consultations = []; this.successMessage = ''; }, error: () => { this.loadError = 'Unable to sign out. Check the API connection.'; } });
  }

  initials(name: string) {
    return name.replace(/^Dr\.\s*/i, '').split(/\s+/).slice(0, 2).map(part => part[0]).join('').toUpperCase();
  }

  refresh(showLoading = true) {
    if (showLoading) this.loading = true;
    this.loadError = '';
    forkJoin({
      doctors: this.api.getDoctors(),
      consultations: this.api.getConsultations(),
    }).subscribe({
      next: ({ doctors, consultations }) => {
        this.doctors = doctors;
        this.consultations = consultations;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.loadError = 'Unable to reach the HealthLink API. Check that the backend and database are running.';
      },
    });
  }

  bookingCompleted(consultation: Consultation) {
    this.selectedDoctor = null;
    this.successMessage = `Consultation booked with ${consultation.doctorName}.`;
    this.refresh(false);
    window.setTimeout(() => (this.successMessage = ''), 4500);
  }
}
