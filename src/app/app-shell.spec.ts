import { provideHttpClient } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';

import { App } from './app';
import { routes } from './app.routes';

describe('App shell', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  it('should load the login without loading the operational screen', async () => {
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [provideHttpClient(), provideRouter(routes)]
    }).compileComponents();

    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    await TestBed.inject(Router).navigateByUrl('/');
    await fixture.whenStable();
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('app-login')).not.toBeNull();
    expect(compiled.querySelector('app-sistema')).toBeNull();
    expect(compiled.querySelector('h1')?.textContent).toContain('Sistema FCL');
  });
});
