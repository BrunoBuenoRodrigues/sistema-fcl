from dataclasses import dataclass
from threading import Lock
from time import monotonic


@dataclass
class TentativasLogin:
    quantidade: int
    primeira_tentativa: float
    bloqueado_ate: float | None = None


class LimitadorLogin:
    def __init__(self, max_tentativas: int, bloqueio_segundos: int):
        self.max_tentativas = max_tentativas
        self.bloqueio_segundos = bloqueio_segundos
        self._tentativas: dict[str, TentativasLogin] = {}
        self._lock = Lock()

    def tempo_bloqueio(self, chave: str) -> int:
        agora = monotonic()

        with self._lock:
            registro = self._tentativas.get(chave)
            if registro is None:
                return 0

            if registro.bloqueado_ate is not None:
                restante = registro.bloqueado_ate - agora
                if restante > 0:
                    return max(1, int(restante + 0.999))

                self._tentativas.pop(chave, None)
                return 0

            if agora - registro.primeira_tentativa >= self.bloqueio_segundos:
                self._tentativas.pop(chave, None)

            return 0

    def registrar_falha(self, chave: str) -> None:
        agora = monotonic()

        with self._lock:
            registro = self._tentativas.get(chave)
            if (
                registro is None
                or agora - registro.primeira_tentativa >= self.bloqueio_segundos
            ):
                registro = TentativasLogin(0, agora)
                self._tentativas[chave] = registro

            registro.quantidade += 1
            if registro.quantidade >= self.max_tentativas:
                registro.bloqueado_ate = agora + self.bloqueio_segundos

    def registrar_sucesso(self, chave: str) -> None:
        with self._lock:
            self._tentativas.pop(chave, None)

    def limpar(self) -> None:
        with self._lock:
            self._tentativas.clear()
