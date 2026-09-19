def cpf_valido(valor: str) -> bool:
    if len(valor) != 11 or len(set(valor)) == 1:
        return False

    def calcular_digito(quantidade: int) -> int:
        soma = sum(
            int(valor[indice]) * (quantidade + 1 - indice)
            for indice in range(quantidade)
        )
        digito = (soma * 10) % 11
        return 0 if digito == 10 else digito

    return (
        calcular_digito(9) == int(valor[9])
        and calcular_digito(10) == int(valor[10])
    )


def cnpj_valido(valor: str) -> bool:
    if len(valor) != 14 or len(set(valor)) == 1:
        return False

    def calcular_digito(quantidade: int) -> int:
        pesos = (
            [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
            if quantidade == 12
            else [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        )
        soma = sum(
            int(valor[indice]) * peso
            for indice, peso in enumerate(pesos)
        )
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    return (
        calcular_digito(12) == int(valor[12])
        and calcular_digito(13) == int(valor[13])
    )
