import { CommonModule } from '@angular/common';
import { Component, Input, OnChanges } from '@angular/core';
import { Consultation } from '../../models';

@Component({
  selector: 'app-consultation-list',
  standalone: true,
  imports: [CommonModule],
  template: `
    <section class="panel consultations-panel">
      <div class="section-heading">
        <div>
          <span class="eyebrow">MY CONSULTATIONS</span>
          <h2>Appointments</h2>
        </div>
      </div>

      <div class="consultation-list" *ngIf="consultations.length; else empty">
        <section class="consultation-group" *ngFor="let group of groups" [attr.aria-label]="group.title">
          <h3 class="group-title">{{ group.title }} <span>{{ group.items.length }}</span></h3>
          <p class="sort-hint">{{ group.order }}</p>
          <p class="empty-group" *ngIf="!group.items.length">{{ group.empty }}</p>
        <article class="consultation-card" *ngFor="let item of group.items">
          <div class="type-icon" [class.video]="item.type === 'VIDEO'">
            {{ item.type === 'VIDEO' ? '▶' : '✦' }}
          </div>
          <div class="consultation-main">
            <div class="title-row">
              <h3>{{ item.doctorName }}</h3>
              <span class="status" [class.completed]="item.status === 'COMPLETED'">
                {{ item.status === 'SCHEDULED' ? 'Scheduled' : 'Completed' }}
              </span>
            </div>
            <p>{{ item.specialty }} · {{ item.type === 'VIDEO' ? 'Video Call' : 'Chat' }}</p>
            <strong>{{ item.preferredTime | date:'EEE, d MMM · h:mm a' }}</strong>
            <p class="visit-reason"><span>Reason for visit</span>{{ item.reasonForVisit }}</p>
          </div>
        </article>
        </section>
      </div>

      <ng-template #empty>
        <div class="empty-state">Your booked consultations will appear here.</div>
      </ng-template>
    </section>
  `,
  styles: [`
    .consultation-list { display: grid; gap: 12px; }
    .consultation-group { display: grid; gap: 12px; }
    .consultation-group + .consultation-group { margin-top: 12px; padding-top: 20px; border-top: 1px solid var(--line); }
    .group-title { display: flex; justify-content: space-between; gap: 8px; }
    .group-title span { color: var(--muted); font-weight: 500; }
    .sort-hint, .empty-group { margin: 0; }
    .consultation-card { display: grid; grid-template-columns: 42px minmax(0,1fr); gap: 12px; padding: 16px; background: #fff; border: 1px solid var(--line); border-radius: 16px; }
    .type-icon { width: 42px; height: 42px; border-radius: 13px; display: grid; place-items: center; color: var(--primary); background: #eaf6ff; font-weight: 900; }
    .type-icon.video { color: #7b58c7; background: #f1edff; }
    .consultation-main { min-width: 0; }
    .title-row { display: flex; align-items: start; justify-content: space-between; gap: 8px; }
    h3 { margin: 0; font-size: .96rem; }
    p { margin: 4px 0 8px; color: var(--muted); font-size: .8rem; }
    strong { font-size: .82rem; color: var(--text); }
    .status { flex: 0 0 auto; border-radius: 999px; padding: 5px 8px; background: #f0edff; color: #6946ba; font-size: .68rem; font-weight: 800; }
    .status.completed { background: #e7f8ef; color: #167654; }
    .visit-reason { margin: 12px 0 0; padding-top: 10px; border-top: 1px solid var(--line); color: var(--text); white-space: pre-wrap; overflow-wrap: anywhere; line-height: 1.5; }
    .visit-reason span { display: block; margin-bottom: 4px; color: var(--muted); font-size: .7rem; font-weight: 700; }
  `],
})
export class ConsultationListComponent implements OnChanges {
  @Input({ required: true }) consultations: Consultation[] = [];
  groups: { title: string; order: string; empty: string; items: Consultation[] }[] = [];

  ngOnChanges(): void {
    const now = Date.now();
    const upcoming = (item: Consultation) => item.status === 'SCHEDULED' && Date.parse(item.preferredTime) >= now;
    const byTime = (a: Consultation, b: Consultation) => Date.parse(a.preferredTime) - Date.parse(b.preferredTime)
      || Date.parse(a.createdAt) - Date.parse(b.createdAt) || a.id.localeCompare(b.id);
    this.groups = [
      { title: 'Upcoming', order: 'Nearest appointment first', empty: 'No upcoming appointments.', items: this.consultations.filter(upcoming).sort(byTime) },
      { title: 'Past and completed', order: 'Most recent appointment first', empty: 'No past or completed appointments.', items: this.consultations.filter(item => !upcoming(item)).sort((a, b) => byTime(b, a)) },
    ];
  }
}
