import { CommonModule } from '@angular/common';
import { Component, EventEmitter, inject, Output } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { AuthService } from '../../core/auth.service';
import { SessionUser, UserRole } from '../../models';

@Component({
  selector: 'app-sign-in', standalone: true, imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './sign-in.component.html', styleUrl: './sign-in.component.scss',
})
export class SignInComponent {
  private readonly auth = inject(AuthService);
  private readonly fb = inject(FormBuilder);
  @Output() signedIn = new EventEmitter<SessionUser>();
  role: UserRole = 'PATIENT';
  busy = false;
  error = '';
  readonly roles: { role: UserRole; label: string; detail: string; symbol: string }[] = [
    { role: 'PATIENT', label: 'Patient', detail: 'Find a doctor and book care', symbol: '♡' },
    { role: 'DOCTOR', label: 'Doctor', detail: 'Appointments and availability', symbol: '+' },
    { role: 'ADMIN', label: 'Admin', detail: 'People and practice overview', symbol: '▦' },
  ];
  readonly form = this.fb.nonNullable.group({ email: ['john@healthlink.local', [Validators.required, Validators.email]], password: ['healthlink-demo-2026', Validators.required] });
  get roleLabel() { return this.roles.find(r => r.role === this.role)!.label; }
  selectRole(role: UserRole) {
    this.role = role; this.error = '';
    this.form.setValue({ email: role === 'PATIENT' ? 'john@healthlink.local' : role === 'DOCTOR' ? 'sarah.lim@healthlink.local' : 'admin@healthlink.local', password: 'healthlink-demo-2026' });
  }
  submit() {
    if (this.form.invalid || this.busy) return;
    this.busy = true; this.error = '';
    const { email, password } = this.form.getRawValue();
    this.auth.login(email, password, this.role).subscribe({
      next: user => { this.busy = false; this.signedIn.emit(user); },
      error: e => { this.busy = false; this.error = e.error?.message ?? 'Unable to sign in. Check the API is running.'; },
    });
  }
}
