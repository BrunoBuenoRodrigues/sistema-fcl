import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import { environment } from '../environments/environment';

@Component({
  selector: 'app-login',
  imports: [CommonModule, FormsModule],
  templateUrl: './login.component.html'
})
export class LoginComponent implements OnInit {
  private readonly apiUrl = environment.apiUrl.replace(/\/+$/, '');

  login = '';
  senha = '';
  mensagemErro = '';
  entrando = false;

  constructor(
    private readonly http: HttpClient,
    private readonly router: Router,
    private readonly cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    document.title = 'Sistema FCL';
    this.mensagemErro = sessionStorage.getItem('mensagem_login') ?? '';
    sessionStorage.removeItem('mensagem_login');

    if (localStorage.getItem('token')) {
      void this.router.navigateByUrl('/sistema', { replaceUrl: true });
    }
  }

  entrar(): void {
    if (this.entrando) {
      return;
    }

    const login = this.login.trim();
    if (!login || !this.senha) {
      this.mensagemErro = 'Informe o login e a senha.';
      return;
    }

    this.mensagemErro = '';
    this.entrando = true;

    this.http.post<any>(`${this.apiUrl}/login`, {
      login,
      senha: this.senha
    }).subscribe({
      next: (resposta) => {
        localStorage.setItem('token', resposta.access_token);
        this.entrando = false;
        void this.router.navigateByUrl('/sistema', { replaceUrl: true });
      },
      error: (erro) => {
        const detalhe = erro.error?.detail;
        this.entrando = false;
        this.mensagemErro = typeof detalhe === 'string'
          ? detalhe
          : 'Não foi possível entrar no sistema.';
        this.cdr.detectChanges();
      }
    });
  }
}
