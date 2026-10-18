import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ApiService } from '../../core/api.service';
import { Consultation, ConsultationType, Doctor } from '../../models';

@Component({
  selector: 'app-booking-panel',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  template: `
    <div class="backdrop" (click)="closed.emit()"></div>
    <aside class="booking-panel" role="dialog" aria-modal="true" aria-labelledby="booking-title">
      <div class="booking-header">
        <div>
          <span class="eyebrow">BOOK CONSULTATION</span>
          <h2 id="booking-title">Schedule with {{ doctor.name }}</h2>
        </div>
        <button class="icon-button" type="button" aria-label="Close booking" (click)="closed.emit()">×</button>
      </div>

      <div class="doctor-summary">
        <div class="summary-avatar">{{ initials(doctor.name) }}</div>
        <div><strong>{{ doctor.name }}</strong><span>{{ doctor.specialty }}</span></div>
      </div>

      <form [formGroup]="form" (ngSubmit)="submit()">
        <label class="field-label">1. Consultation Type</label>
        <div class="type-grid">
          <button type="button" class="type-card" [class.active]="form.controls.type.value === 'CHAT'" (click)="setType('CHAT')">
            <span class="type-symbol">✦</span><strong>Chat</strong><small>Text-based consultation</small>
          </button>
          <button type="button" class="type-card" [class.active]="form.controls.type.value === 'VIDEO'" (click)="setType('VIDEO')">
            <span class="type-symbol">▶</span><strong>Video Call</strong><small>Face-to-face online</small>
          </button>
        </div>

        <label class="field-label" for="preferredTime">2. Preferred Time</label>
        <select id="preferredTime" formControlName="preferredTime">
          <option value="" disabled>Select an available slot</option>
          <option *ngFor="let slot of doctor.availability" [value]="slot.startTime">
            {{ slot.startTime | date:'EEEE, d MMMM · h:mm a' }}
          </option>
        </select>

        <label class="field-label" for="reason">3. Reason for Visit</label>
        <textarea id="reason" formControlName="reasonForVisit" rows="5" maxlength="500" placeholder="Please share your symptoms or concern briefly..."></textarea>
        <div class="field-meta">
          <span *ngIf="form.controls.reasonForVisit.touched && form.controls.reasonForVisit.invalid">Please enter at least 5 characters.</span>
          <span>{{ form.controls.reasonForVisit.value.length }}/500</span>
        </div>

        <div class="form-error" *ngIf="errorMessage">{{ errorMessage }}</div>

        <button class="primary-button confirm" type="submit" [disabled]="form.invalid || submitting">
          {{ submitting ? 'Booking...' : 'Confirm Booking' }}
        </button>
        <p class="privacy-note">Your information is used only for this assessment demo.</p>
      </form>
    </aside>
  `,
  styles: [`
    :host { position: fixed; inset: 0; z-index: 20; pointer-events: none; }
    .backdrop { position: absolute; inset: 0; background: rgba(14,35,51,.25); backdrop-filter: blur(2px); pointer-events: auto; }
    .booking-panel { position: absolute; top: 0; right: 0; height: 100%; width: min(470px, 100%); overflow-y: auto; padding: 28px; background: #fff; box-shadow: -18px 0 50px rgba(18,55,80,.14); pointer-events: auto; animation: enter .2s ease-out; }
    @keyframes enter { from { transform: translateX(24px); opacity: .7; } }
    .booking-header { display: flex; justify-content: space-between; gap: 16px; align-items: start; }
    .booking-header h2 { margin: 5px 0 0; font-size: 1.35rem; }
    .icon-button { border: 0; width: 36px; height: 36px; border-radius: 50%; background: var(--soft); color: var(--muted); font-size: 1.6rem; line-height: 1; cursor: pointer; }
    .doctor-summary { display: flex; align-items: center; gap: 12px; padding: 14px; margin: 22px 0; background: linear-gradient(135deg,#eff9ff,#f2fcf8); border: 1px solid #dcecf2; border-radius: 16px; }
    .summary-avatar { width: 46px; height: 46px; border-radius: 14px; display: grid; place-items: center; background: #fff; color: var(--primary); font-weight: 900; box-shadow: 0 5px 16px rgba(20,85,125,.08); }
    .doctor-summary strong, .doctor-summary span { display: block; }
    .doctor-summary span { color: var(--muted); font-size: .8rem; margin-top: 2px; }
    form { display: grid; }
    .field-label { margin: 18px 0 10px; color: var(--text); font-size: .84rem; font-weight: 800; }
    .type-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .type-card { display: grid; justify-items: start; gap: 3px; padding: 14px; border: 1.5px solid var(--line); border-radius: 15px; background: #fff; color: var(--text); cursor: pointer; text-align: left; }
    .type-card.active { border-color: var(--primary); background: #f1f9ff; box-shadow: 0 0 0 3px rgba(8,121,189,.08); }
    .type-symbol { color: var(--primary); font-size: 1rem; }
    .type-card small { color: var(--muted); font-size: .72rem; }
    select, textarea { width: 100%; border: 1px solid var(--line); border-radius: 12px; background: #fff; color: var(--text); padding: 12px 13px; font: inherit; outline: none; }
    select:focus, textarea:focus { border-color: var(--primary); box-shadow: 0 0 0 3px rgba(8,121,189,.08); }
    textarea { resize: vertical; min-height: 110px; }
    .field-meta { display: flex; justify-content: space-between; min-height: 20px; padding-top: 5px; color: #b34646; font-size: .7rem; }
    .field-meta span:last-child { margin-left: auto; color: var(--muted); }
    .form-error { padding: 10px 12px; margin-top: 8px; border-radius: 10px; background: #fff0f0; color: #a63f3f; font-size: .8rem; }
    .confirm { width: 100%; margin-top: 18px; }
    .privacy-note { margin: 10px 0 0; text-align: center; color: var(--muted); font-size: .69rem; }
    @media (max-width: 520px) { .booking-panel { padding: 22px 18px; } }
  `],
})
export class BookingPanelComponent implements OnChanges {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(ApiService);

  @Input({ required: true }) doctor!: Doctor;
  @Output() closed = new EventEmitter<void>();
  @Output() booked = new EventEmitter<Consultation>();

  submitting = false;
  errorMessage = '';
  readonly form = this.fb.nonNullable.group({
    type: ['CHAT' as ConsultationType, Validators.required],
    preferredTime: ['', Validators.required],
    reasonForVisit: ['', [Validators.required, Validators.minLength(5), Validators.maxLength(500)]],
  });

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['doctor']) {
      this.form.reset({ type: 'CHAT', preferredTime: '', reasonForVisit: '' });
      this.errorMessage = '';
    }
  }

  setType(type: ConsultationType) {
    this.form.controls.type.setValue(type);
  }

  submit() {
    if (this.form.invalid || this.submitting) {
      this.form.markAllAsTouched();
      return;
    }
    this.submitting = true;
    this.errorMessage = '';
    this.api.createConsultation({ doctorId: this.doctor.id, ...this.form.getRawValue() }).subscribe({
      next: (consultation) => {
        this.submitting = false;
        this.booked.emit(consultation);
      },
      error: (error) => {
        this.submitting = false;
        this.errorMessage = error?.error?.message ?? 'Unable to complete the booking. Please try again.';
      },
    });
  }

  initials(name: string): string {
    return name.replace(/^Dr\.\s*/i, '').split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase();
  }
}
