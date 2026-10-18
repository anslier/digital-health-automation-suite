import { CommonModule } from '@angular/common';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Component, OnDestroy, OnInit, computed, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';

type RecordItem = {
  registration_no: string; product_name: string | null; holder: string | null;
  manufacturer: string | null; status: string | null; category: string | null;
  registration_date: string | null; expiry_date: string | null; meeting: number; source_url: string | null;
};
type Run = {
  id:string; trigger:string; status:string; requested_at:string; started_at:string|null; finished_at:string|null;
  discovered_count:number; skipped_count:number; downloaded_count:number; processed_count:number; failed_count:number; observation_count:number;
};
type Schedule = {enabled:boolean; cadence:'DAILY'|'WEEKLY'|'MONTHLY'; local_time:string; weekday:number|null; day_of_month:number; timezone:string; revision:number; next_run_at?:string|null};

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent implements OnInit, OnDestroy {
  email='admin@npra.local'; password='npra-demo-2026';
  user = signal<string | null>(null); error = signal(''); busy = signal(false);
  tab = signal<'records'|'runs'|'schedule'>('records');
  records = signal<RecordItem[]>([]); total = signal(0); query='';
  page = signal(1); pageSize = signal(50); recordsBusy = signal(false);
  pageCount = computed(() => Math.max(1, Math.ceil(this.total()/this.pageSize())));
  recordRange = computed(() => `Showing ${this.total() ? (this.page()-1)*this.pageSize()+1 : 0}–${Math.min(this.page()*this.pageSize(),this.total())} of ${this.total()} records`);
  private appliedQuery=''; private recordsRequest=0;
  runs = signal<Run[]>([]);
  activeRun = computed(() => this.runs().find(r => ['QUEUED','RUNNING'].includes(r.status)));
  runBusy=signal(false); runsReady=signal(false); runsError=signal(''); runNotice=signal('');
  private runsLoading=false; private pollTimer?:ReturnType<typeof setInterval>;
  schedule = signal<Schedule>({enabled:false,cadence:'MONTHLY',local_time:'09:00',weekday:null,day_of_month:8,timezone:'Asia/Kuala_Lumpur',revision:1});
  savedSchedule=signal<Schedule|null>(null); scheduleNotice=signal(''); scheduleDirty=signal(false);

  constructor(private http: HttpClient) {}

  useDemoAccount() { this.email = 'admin@npra.local'; this.password = 'npra-demo-2026'; this.error.set(''); }

  async ngOnInit() {
    try { const me:any = await firstValueFrom(this.http.get('/api/auth/me',{withCredentials:true})); this.user.set(me.email); await this.refreshAll(); }
    catch { /* login screen */ }
  }

  private message(e: unknown) {
    if(!(e instanceof HttpErrorResponse)) return String(e);
    const detail=e.error?.detail;
    return Array.isArray(detail) ? detail.map((x:any)=>`${x.loc?.slice(1).join('.') || 'Input'}: ${x.msg}`).join('; ') : (detail || e.message);
  }

  async login() {
    this.busy.set(true); this.error.set('');
    try { const x:any = await firstValueFrom(this.http.post('/api/auth/login',{email:this.email,password:this.password},{withCredentials:true})); this.user.set(x.email); await this.refreshAll(); }
    catch(e) { this.error.set(this.message(e)); } finally { this.busy.set(false); }
  }
  async logout() { await firstValueFrom(this.http.post('/api/auth/logout',{}, {withCredentials:true})); this.user.set(null); this.stopPolling(); }
  ngOnDestroy() { this.stopPolling(); }
  private stopPolling() { if(this.pollTimer) clearInterval(this.pollTimer); this.pollTimer=undefined; }
  async refreshAll() {
    await Promise.all([this.loadRecords(), this.loadRuns(), this.loadSchedule()]);
    if(!this.pollTimer) this.pollTimer=setInterval(() => { if(this.user()) void this.loadRuns(); },3000);
  }
  async searchRecords() { this.appliedQuery=this.query.trim(); this.page.set(1); await this.loadRecords(); }
  async changePage(next:number) { if(this.recordsBusy() || next<1 || next>this.pageCount()) return; this.page.set(next); await this.loadRecords(); }
  async changePageSize(size:number) { this.pageSize.set(size); this.page.set(1); await this.loadRecords(); }
  async loadRecords() {
    const request=++this.recordsRequest; this.recordsBusy.set(true);
    try {
      const params:any={page:this.page(),page_size:this.pageSize()}; if(this.appliedQuery) params.q=this.appliedQuery;
      const res:any = await firstValueFrom(this.http.get('/api/records',{params,withCredentials:true}));
      if(request!==this.recordsRequest) return;
      this.records.set(res.items); this.total.set(res.total);
      if(this.page()>this.pageCount()) { this.page.set(this.pageCount()); await this.loadRecords(); }
    } catch(e) { if(request===this.recordsRequest) this.error.set(this.message(e)); }
    finally { if(request===this.recordsRequest) this.recordsBusy.set(false); }
  }
  async loadRuns() {
    if(this.runsLoading) return; this.runsLoading=true;
    const previous=this.activeRun();
    try {
      const runs=await firstValueFrom(this.http.get<Run[]>('/api/runs',{withCredentials:true}));
      this.runs.set(runs); this.runsReady.set(true); this.runsError.set('');
      if(previous) {
        const finished=runs.find(r=>r.id===previous.id);
        if(finished && !['QUEUED','RUNNING'].includes(finished.status)) {
          this.runNotice.set(finished.status==='SUCCESS'?'Import completed successfully':`Import finished with ${finished.status}. Review Import history.`);
          if(finished.status==='SUCCESS') void this.loadRecords();
        }
      }
    } catch(e) { this.runsReady.set(false); this.runsError.set('Cannot update import status. Retrying automatically; use Refresh to try again.'); }
    finally { this.runsLoading=false; }
  }
  async loadSchedule() {
    const s=await firstValueFrom(this.http.get<Schedule>('/api/schedule',{withCredentials:true}));
    this.schedule.set(s); this.savedSchedule.set({...s}); this.scheduleDirty.set(false);
  }
  async runNow() {
    if(this.runBusy() || this.activeRun() || !this.runsReady()) return;
    this.runBusy.set(true); this.error.set(''); this.runNotice.set('');
    try {
      const run=await firstValueFrom(this.http.post<Run>('/api/runs',{}, {withCredentials:true}));
      this.runs.update(runs=>[run,...runs.filter(r=>r.id!==run.id)]);
      this.tab.set('runs'); await this.loadRuns();
    } catch(e){this.error.set(this.message(e));} finally{this.runBusy.set(false);}
  }
  patchSchedule(patch: Partial<Schedule>) {
    if(patch.cadence==='WEEKLY' && this.schedule().weekday===null) patch.weekday=0;
    this.schedule.set({...this.schedule(), ...patch}); this.scheduleDirty.set(true); this.scheduleNotice.set('');
  }
  scheduleTime(s:Schedule) { return s.next_run_at ? new Intl.DateTimeFormat('en-MY',{dateStyle:'medium',timeStyle:'short',timeZone:s.timezone}).format(new Date(s.next_run_at)) : ''; }
  runTime(value:string) { return new Intl.DateTimeFormat('en-MY',{dateStyle:'medium',timeStyle:'medium',timeZone:'Asia/Kuala_Lumpur'}).format(new Date(/[Zz]|[+-]\d\d:\d\d$/.test(value)?value:value+'Z')); }
  async saveSchedule() {
    this.busy.set(true); this.error.set('');
    this.scheduleNotice.set('');
    try {
      const s=await firstValueFrom(this.http.put<Schedule>('/api/schedule',this.schedule(),{withCredentials:true}));
      this.schedule.set(s); this.savedSchedule.set({...s}); this.scheduleDirty.set(false);
      this.scheduleNotice.set(s.enabled?'Schedule saved. Automatic checks are enabled.':'Schedule saved. Automatic checks are disabled.');
    }
    catch(e){this.error.set(this.message(e));} finally{this.busy.set(false);}
  }
  exportRecords(){ window.location.href='/api/exports/records.csv'; }
  exportManifest(){ window.location.href='/api/exports/manifest.csv'; }
}
