import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { vi } from 'vitest';

import { LoginComponent } from './login.component';

describe('LoginComponent', () => {
  let httpTesting: HttpTestingController;
  let router: Router;

  beforeEach(async () => {
    localStorage.clear();
    sessionStorage.clear();

    await TestBed.configureTestingModule({
      imports: [LoginComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([])
      ]
    }).compileComponents();

    httpTesting = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
  });

  afterEach(() => {
    httpTesting.verify();
    localStorage.clear();
    sessionStorage.clear();
  });

  it('should render the login form with database-compatible limits', () => {
    const fixture = TestBed.createComponent(LoginComponent);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('h1')?.textContent).toContain('Sistema FCL');
    expect(compiled.querySelector<HTMLInputElement>('#login')?.maxLength).toBe(50);
    expect(compiled.querySelector<HTMLInputElement>('#senha')?.maxLength).toBe(128);
  });

  it('should authenticate, store the token and open the system', () => {
    const navegar = vi.spyOn(router, 'navigateByUrl').mockResolvedValue(true);
    const fixture = TestBed.createComponent(LoginComponent);
    const component = fixture.componentInstance;
    component.login = ' administrador ';
    component.senha = 'senha-segura';

    component.entrar();

    const requisicao = httpTesting.expectOne('http://127.0.0.1:8000/login');
    expect(requisicao.request.method).toBe('POST');
    expect(requisicao.request.body).toEqual({
      login: 'administrador',
      senha: 'senha-segura'
    });
    requisicao.flush({ access_token: 'token-valido' });

    expect(localStorage.getItem('token')).toBe('token-valido');
    expect(navegar).toHaveBeenCalledWith('/sistema', { replaceUrl: true });
    expect(component.entrando).toBe(false);
  });

  it('should reuse a saved session without submitting credentials', () => {
    localStorage.setItem('token', 'token-salvo');
    const navegar = vi.spyOn(router, 'navigateByUrl').mockResolvedValue(true);
    const fixture = TestBed.createComponent(LoginComponent);

    fixture.detectChanges();

    expect(navegar).toHaveBeenCalledWith('/sistema', { replaceUrl: true });
  });

  it('should show the API error and allow another attempt', () => {
    const fixture = TestBed.createComponent(LoginComponent);
    const component = fixture.componentInstance;
    component.login = 'usuario';
    component.senha = 'senha-incorreta';

    component.entrar();
    httpTesting.expectOne('http://127.0.0.1:8000/login').flush(
      { detail: 'Login ou senha inválidos.' },
      { status: 401, statusText: 'Unauthorized' }
    );

    expect(component.mensagemErro).toBe('Login ou senha inválidos.');
    expect(component.entrando).toBe(false);
  });
});
