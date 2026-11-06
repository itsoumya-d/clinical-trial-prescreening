import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClientModule } from '@angular/common/http';
import { TravelerChecklistComponent } from './traveler-checklist.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, HttpClientModule, TravelerChecklistComponent],
  template: `
    <main style="max-width:880px;margin:0 auto;padding:24px">
      <h1>Clinical trial — your eligibility checklist</h1>
      <p>Explainable criterion-level eligibility with physician review — never a black box.</p>
      <app-traveler-checklist [tripId]="'demo-trip-1'"></app-traveler-checklist>
    </main>
  `
})
export class AppComponent {
  title = 'Clinical Trial Pre-screening';
}
