import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    loadComponent: () =>
      import('./login.component').then((modulo) => modulo.LoginComponent)
  },
  {
    path: 'sistema',
    loadComponent: () =>
      import('./sistema.component').then((modulo) => modulo.SistemaComponent)
  },
  {
    path: '**',
    redirectTo: ''
  }
];
