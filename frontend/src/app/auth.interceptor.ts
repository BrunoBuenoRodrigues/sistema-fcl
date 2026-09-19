import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { catchError, throwError } from 'rxjs';

export const authInterceptor: HttpInterceptorFn = (requisicao, proximo) => {
  return proximo(requisicao).pipe(
    catchError((erro: HttpErrorResponse) => {
      const requisicaoDeLogin = requisicao.url.endsWith('/login');

      if (erro.status === 401 && !requisicaoDeLogin) {
        localStorage.removeItem('token');
        window.dispatchEvent(new Event('sessao-expirada'));
      }

      return throwError(() => erro);
    })
  );
};
