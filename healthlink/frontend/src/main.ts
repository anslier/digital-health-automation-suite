import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { sessionInterceptor } from './app/core/auth.service';
import { bootstrapApplication } from '@angular/platform-browser';
import { AppComponent } from './app/app.component';

bootstrapApplication(AppComponent, {
  providers: [provideHttpClient(withInterceptors([sessionInterceptor]))],
}).catch((error) => console.error(error));
