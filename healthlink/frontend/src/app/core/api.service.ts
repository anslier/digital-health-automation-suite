import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Consultation, CreateConsultationRequest, Doctor } from '../models';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = '/api';

  getDoctors(): Observable<Doctor[]> {
    return this.http.get<Doctor[]>(`${this.baseUrl}/doctors`);
  }

  getConsultations(): Observable<Consultation[]> {
    return this.http.get<Consultation[]>(`${this.baseUrl}/consultations`);
  }

  createConsultation(payload: CreateConsultationRequest): Observable<Consultation> {
    return this.http.post<Consultation>(`${this.baseUrl}/consultations`, payload);
  }
}
