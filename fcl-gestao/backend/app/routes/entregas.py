from datetime import datetime
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.database import get_db
from app.dependencies import exigir_perfis
from app.models.cliente import Cliente
from app.models.entrega import Entrega
from app.models.usuario import Usuario
from app.schemas.entrega import EntregaAtualizar, EntregaCriar, EntregaResposta
from app.models.historico import Historico
from app.schemas.historico import HistoricoResposta
from app.models.notificacao import Notificacao
from app.schemas.entrega import (
    AgendamentoEntregaAtualizar,
    AtribuirEntregador,
    ComprovanteEntregaAtualizar,
    EntregaCancelar,
    EntregaNaoEntregue,
)


router = APIRouter(
    prefix="/entregas",
    tags=["Entregas"]
)


def exigir_acesso_a_entrega(entrega: Entrega, usuario_atual: Usuario) -> None:
    if (
        usuario_atual.perfil == "ENTREGADOR"
        and entrega.id_entregador != usuario_atual.id_usuario
    ):
        raise HTTPException(
            status_code=403,
            detail="Esta entrega está atribuída a outro entregador."
        )


@router.post(
    "/",
    response_model=EntregaResposta,
    status_code=status.HTTP_201_CREATED
)
def criar_entrega(
    dados: EntregaCriar,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis(
            "FUNCIONARIO",
            "ESTOQUE",
            "ADMINISTRADOR"
        )
    )
):
    cliente = db.query(Cliente).filter(
        Cliente.id_cliente == dados.id_cliente
    ).first()

    if not cliente:
        raise HTTPException(
            status_code=404,
            detail="Cliente não encontrado."
        )

    if not cliente.ativo:
        raise HTTPException(
            status_code=400,
            detail="Não é possível criar entrega para cliente inativo."
        )

    if dados.data_agendada is not None and dados.data_agendada < date.today():
        raise HTTPException(
            status_code=400,
            detail="A data agendada não pode ser anterior à data atual."
        )

    if dados.id_entregador is not None:
        entregador = db.query(Usuario).filter(
            Usuario.id_usuario == dados.id_entregador
        ).first()

        if not entregador:
            raise HTTPException(
                status_code=404,
                detail="Entregador não encontrado."
            )

        if entregador.perfil != "ENTREGADOR":
            raise HTTPException(
                status_code=400,
                detail="O usuário informado não possui perfil de ENTREGADOR."
            )

        if not entregador.ativo:
            raise HTTPException(
                status_code=400,
                detail="Não é possível atribuir a entrega a um entregador inativo."
            )

        if dados.data_agendada is None:
            raise HTTPException(
                status_code=400,
                detail="A data agendada é obrigatória quando há entregador definido."
            )

        if not dados.anexo_pedido or not dados.anexo_pedido.strip():
            raise HTTPException(
                status_code=400,
                detail="O anexo do pedido é obrigatório."
            )

    nova_entrega = Entrega(
        id_cliente=dados.id_cliente,
        id_usuario_cadastro=usuario_atual.id_usuario,
        id_entregador=dados.id_entregador,
        data_cadastro=datetime.now(),
        data_agendada=dados.data_agendada,
        status="AGENDADA" if dados.data_agendada is not None else "CADASTRADA",
        anexo_pedido=dados.anexo_pedido,
        observacao=dados.observacao
    )

    db.add(nova_entrega)
    db.flush()

    historico_cadastro = Historico(
        id_usuario=usuario_atual.id_usuario,
        tipo_registro="ENTREGA",
        id_registro=nova_entrega.id_entrega,
        acao="CADASTRO",
        descricao="Entrega cadastrada.",
        data_hora=datetime.now()
    )

    db.add(historico_cadastro)

    if dados.data_agendada is not None:
        db.add(Historico(
            id_usuario=usuario_atual.id_usuario,
            tipo_registro="ENTREGA",
            id_registro=nova_entrega.id_entrega,
            acao="AGENDAMENTO",
            descricao=(
                f"Entrega agendada para {dados.data_agendada:%d/%m/%Y} "
                "durante o cadastro."
            ),
            data_hora=datetime.now()
        ))

    db.commit()
    db.refresh(nova_entrega)

    return nova_entrega

@router.get(
    "/",
    response_model=list[EntregaResposta]
)
def listar_entregas(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis(
            "FUNCIONARIO",
            "ESTOQUE",
            "ADMINISTRADOR",
            "ENTREGADOR"
        )
    )
):
    consulta = db.query(Entrega)

    if usuario_atual.perfil == "ENTREGADOR":
        consulta = consulta.filter(
            Entrega.id_entregador == usuario_atual.id_usuario
        )

    return consulta.order_by(Entrega.id_entrega.desc()).all()


@router.get("/minhas-resumo")
def obter_resumo_minhas_entregas(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(exigir_perfis("ENTREGADOR")),
):
    entregas = db.query(Entrega).filter(
        Entrega.id_entregador == usuario_atual.id_usuario
    ).all()
    hoje = date.today()
    inicio_hoje = datetime.combine(hoje, datetime.min.time())
    inicio_amanha = datetime.combine(hoje, datetime.max.time())
    ids_concluidas_hoje = {
        item[0]
        for item in db.query(Historico.id_registro).filter(
            and_(
                Historico.tipo_registro == "ENTREGA",
                Historico.acao == "ALTERACAO_STATUS",
                Historico.descricao.ilike("%para ENTREGUE.%"),
                Historico.data_hora >= inicio_hoje,
                Historico.data_hora <= inicio_amanha,
            )
        ).all()
    }
    ids_do_entregador = {item.id_entrega for item in entregas}
    encerrados = {"ENTREGUE", "CANCELADA"}

    return {
        "hoje": sum(
            1 for item in entregas
            if item.data_agendada == hoje and item.status not in encerrados
        ),
        "em_rota": sum(1 for item in entregas if item.status == "EM_ROTA"),
        "pendentes": sum(1 for item in entregas if item.status not in encerrados),
        "concluidas_hoje": len(ids_concluidas_hoje & ids_do_entregador),
    }

@router.get(
    "/{id_entrega}",
    response_model=EntregaResposta
)
def buscar_entrega(
    id_entrega: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis(
            "FUNCIONARIO",
            "ESTOQUE",
            "ADMINISTRADOR",
            "ENTREGADOR"
        )
    )
):
    entrega = db.query(Entrega).filter(
        Entrega.id_entrega == id_entrega
    ).first()

    if not entrega:
        raise HTTPException(
            status_code=404,
            detail="Entrega não encontrada."
        )

    exigir_acesso_a_entrega(entrega, usuario_atual)

    return entrega


@router.put(
    "/{id_entrega}",
    response_model=EntregaResposta,
)
def atualizar_entrega(
    id_entrega: int,
    dados: EntregaAtualizar,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis("FUNCIONARIO", "ESTOQUE", "ADMINISTRADOR")
    ),
):
    entrega = db.query(Entrega).filter(
        Entrega.id_entrega == id_entrega
    ).with_for_update().first()
    if not entrega:
        raise HTTPException(status_code=404, detail="Entrega não encontrada.")

    status_editaveis = [
        "CADASTRADA",
        "AGENDADA",
        "EM_SEPARACAO",
        "PRONTA_PARA_ENTREGA",
    ]
    if entrega.status not in status_editaveis:
        raise HTTPException(
            status_code=400,
            detail="Não é possível editar a entrega nesta etapa.",
        )

    cliente = db.query(Cliente).filter(
        Cliente.id_cliente == dados.id_cliente
    ).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    if not cliente.ativo:
        raise HTTPException(
            status_code=400,
            detail="Não é possível utilizar um cliente inativo.",
        )

    if dados.id_entregador is not None:
        entregador = db.query(Usuario).filter(
            Usuario.id_usuario == dados.id_entregador
        ).first()
        if not entregador:
            raise HTTPException(status_code=404, detail="Entregador não encontrado.")
        if entregador.perfil != "ENTREGADOR" or not entregador.ativo:
            raise HTTPException(
                status_code=400,
                detail="Selecione um entregador ativo.",
            )

    if dados.data_agendada is not None and dados.data_agendada < date.today():
        raise HTTPException(
            status_code=400,
            detail="A data agendada não pode ser anterior à data atual.",
        )
    if entrega.status != "CADASTRADA" and dados.data_agendada is None:
        raise HTTPException(
            status_code=400,
            detail="A data agendada é obrigatória nesta etapa da entrega.",
        )

    campos_alterados = []
    if entrega.id_cliente != dados.id_cliente:
        campos_alterados.append("cliente")
    if entrega.id_entregador != dados.id_entregador:
        campos_alterados.append("entregador")
    if entrega.data_agendada != dados.data_agendada:
        campos_alterados.append("data agendada")
    if (entrega.observacao or "") != (dados.observacao or ""):
        campos_alterados.append("observação")
    if not campos_alterados:
        raise HTTPException(
            status_code=400,
            detail="Nenhuma alteração foi informada.",
        )

    status_anterior = entrega.status
    entrega.id_cliente = dados.id_cliente
    entrega.id_entregador = dados.id_entregador
    entrega.data_agendada = dados.data_agendada
    entrega.observacao = dados.observacao
    if status_anterior == "CADASTRADA" and dados.data_agendada is not None:
        entrega.status = "AGENDADA"

    descricao = f"Entrega editada. Campos alterados: {', '.join(campos_alterados)}."
    if entrega.status != status_anterior:
        descricao += f" Status alterado de {status_anterior} para {entrega.status}."
    db.add(
        Historico(
            id_usuario=usuario_atual.id_usuario,
            tipo_registro="ENTREGA",
            id_registro=entrega.id_entrega,
            acao="EDICAO",
            descricao=descricao,
            data_hora=datetime.now(),
        )
    )
    db.commit()
    db.refresh(entrega)

    return entrega

def alterar_status_entrega(
    id_entrega: int,
    novo_status: str,
    db: Session,
    usuario_atual: Usuario
):
    entrega = db.query(Entrega).filter(
        Entrega.id_entrega == id_entrega
    ).with_for_update().first()

    if not entrega:
        raise HTTPException(
            status_code=404,
            detail="Entrega não encontrada."
        )

    exigir_acesso_a_entrega(entrega, usuario_atual)

    transicoes_permitidas = {
        "CADASTRADA": ["AGENDADA"],
        "AGENDADA": ["EM_SEPARACAO"],
        "EM_SEPARACAO": ["PRONTA_PARA_ENTREGA"],
        "PRONTA_PARA_ENTREGA": ["EM_ROTA"],
        "EM_ROTA": ["ENTREGUE"]
    }

    status_anterior = entrega.status

    proximos_status = transicoes_permitidas.get(
        status_anterior,
        []
    )

    if novo_status not in proximos_status:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Não é permitido alterar a entrega de "
                f"{status_anterior} para {novo_status}."
            )
        )

    if (
        novo_status == "AGENDADA"
        and (
            entrega.data_agendada is None
            or entrega.data_agendada < date.today()
        )
    ):
        raise HTTPException(
            status_code=400,
            detail="Defina uma data de agendamento válida antes de agendar a entrega.",
        )

    if novo_status == "EM_ROTA" and entrega.id_entregador is None:
        raise HTTPException(
            status_code=400,
            detail="A entrega não pode entrar em rota sem um entregador definido.",
        )

    entrega.status = novo_status

    novo_historico = Historico(
        id_usuario=usuario_atual.id_usuario,
        tipo_registro="ENTREGA",
        id_registro=entrega.id_entrega,
        acao="ALTERACAO_STATUS",
        descricao=(
            f"Status alterado de {status_anterior} "
            f"para {novo_status}."
        ),
        data_hora=datetime.now()
    )

    db.add(novo_historico)

    if novo_status == "PRONTA_PARA_ENTREGA" and entrega.id_entregador is not None:
        nova_notificacao = Notificacao(
            id_usuario=entrega.id_entregador,
            titulo="Entrega pronta",
            mensagem=f"A entrega {entrega.id_entrega} está pronta para ser realizada.",
            lida=False,
            data_hora=datetime.now()
        )

        db.add(nova_notificacao)

    if novo_status == "ENTREGUE":
        nova_notificacao = Notificacao(
            id_usuario=entrega.id_usuario_cadastro,
            titulo="Entrega concluída",
            mensagem=f"A entrega {entrega.id_entrega} foi concluída.",
            lida=False,
            data_hora=datetime.now()
        )

        db.add(nova_notificacao)

    db.commit()
    db.refresh(entrega)

    return entrega

@router.patch(
    "/{id_entrega}/agendar",
    response_model=EntregaResposta
)
def agendar_entrega(
    id_entrega: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis(
            "FUNCIONARIO",
            "ESTOQUE",
            "ADMINISTRADOR"
        )
    )
):
    return alterar_status_entrega(
    id_entrega,
    "AGENDADA",
    db,
    usuario_atual
)


@router.patch(
    "/{id_entrega}/agendamento",
    response_model=EntregaResposta,
)
def atualizar_agendamento_entrega(
    id_entrega: int,
    dados: AgendamentoEntregaAtualizar,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis(
            "FUNCIONARIO",
            "ESTOQUE",
            "ADMINISTRADOR",
        )
    ),
):
    entrega = db.query(Entrega).filter(
        Entrega.id_entrega == id_entrega
    ).with_for_update().first()

    if not entrega:
        raise HTTPException(
            status_code=404,
            detail="Entrega não encontrada.",
        )

    if entrega.status not in [
        "CADASTRADA",
        "AGENDADA",
        "EM_SEPARACAO",
        "PRONTA_PARA_ENTREGA",
        "NAO_ENTREGUE",
    ]:
        raise HTTPException(
            status_code=400,
            detail="Não é possível alterar a data nesta etapa da entrega.",
        )

    if dados.data_agendada < date.today():
        raise HTTPException(
            status_code=400,
            detail="A data agendada não pode ser anterior à data atual.",
        )

    data_anterior = entrega.data_agendada
    status_anterior = entrega.status
    entrega.data_agendada = dados.data_agendada

    if status_anterior == "CADASTRADA":
        entrega.status = "AGENDADA"
        acao = "AGENDAMENTO"
        descricao = f"Entrega agendada para {dados.data_agendada:%d/%m/%Y}."
    else:
        if status_anterior == "NAO_ENTREGUE":
            entrega.status = "AGENDADA"
        acao = "REAGENDAMENTO"
        data_anterior_texto = (
            data_anterior.strftime("%d/%m/%Y")
            if data_anterior is not None
            else "não definida"
        )
        descricao = (
            f"Data alterada de {data_anterior_texto} "
            f"para {dados.data_agendada:%d/%m/%Y}."
        )

    historico = Historico(
        id_usuario=usuario_atual.id_usuario,
        tipo_registro="ENTREGA",
        id_registro=entrega.id_entrega,
        acao=acao,
        descricao=descricao,
        data_hora=datetime.now(),
    )
    db.add(historico)
    db.commit()
    db.refresh(entrega)

    return entrega


@router.patch(
    "/{id_entrega}/iniciar-separacao",
    response_model=EntregaResposta
)
def iniciar_separacao(
    id_entrega: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis(
            "FUNCIONARIO",
            "ESTOQUE",
            "ADMINISTRADOR"
        )
    )
):
    return alterar_status_entrega(
    id_entrega,
    "EM_SEPARACAO",
    db,
    usuario_atual
)


@router.patch(
    "/{id_entrega}/pronta",
    response_model=EntregaResposta
)
def marcar_pronta(
    id_entrega: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis(
            "FUNCIONARIO",
            "ESTOQUE",
            "ADMINISTRADOR"
        )
    )
):
    return alterar_status_entrega(
    id_entrega,
    "PRONTA_PARA_ENTREGA",
    db,
    usuario_atual
)

@router.patch(
    "/{id_entrega}/atribuir-entregador",
    response_model=EntregaResposta
)
def atribuir_entregador(
    id_entrega: int,
    dados: AtribuirEntregador,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis(
            "FUNCIONARIO",
            "ESTOQUE",
            "ADMINISTRADOR"
        )
    )
):
    entrega = db.query(Entrega).filter(
        Entrega.id_entrega == id_entrega
    ).with_for_update().first()

    if not entrega:
        raise HTTPException(
            status_code=404,
            detail="Entrega não encontrada."
        )

    entregador = db.query(Usuario).filter(
        Usuario.id_usuario == dados.id_entregador
    ).first()

    if not entregador:
        raise HTTPException(
            status_code=404,
            detail="Entregador não encontrado."
        )

    if entregador.perfil != "ENTREGADOR":
        raise HTTPException(
            status_code=400,
            detail="O usuário informado não possui perfil de ENTREGADOR."
        )

    if not entregador.ativo:
        raise HTTPException(
            status_code=400,
            detail="Não é possível atribuir um entregador inativo."
        )

    if entrega.status in ["EM_ROTA", "ENTREGUE", "CANCELADA"]:
        raise HTTPException(
            status_code=400,
            detail="Não é possível alterar o entregador nesta etapa da entrega."
        )

    entrega.id_entregador = dados.id_entregador

    novo_historico = Historico(
        id_usuario=usuario_atual.id_usuario,
        tipo_registro="ENTREGA",
        id_registro=entrega.id_entrega,
        acao="ATRIBUICAO_ENTREGADOR",
        descricao=f"Entregador {dados.id_entregador} atribuído à entrega.",
        data_hora=datetime.now()
    )

    db.add(novo_historico)

    db.commit()
    db.refresh(entrega)

    return entrega

@router.patch(
    "/{id_entrega}/em-rota",
    response_model=EntregaResposta
)
def colocar_em_rota(
    id_entrega: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis(
            "ENTREGADOR",
            "ADMINISTRADOR"
        )
    )
):
    return alterar_status_entrega(
        id_entrega,
        "EM_ROTA",
        db,
        usuario_atual
    )


@router.patch(
    "/{id_entrega}/nao-entregue",
    response_model=EntregaResposta,
)
def registrar_nao_entrega(
    id_entrega: int,
    dados: EntregaNaoEntregue,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis("ENTREGADOR", "ADMINISTRADOR")
    ),
):
    entrega = db.query(Entrega).filter(
        Entrega.id_entrega == id_entrega
    ).with_for_update().first()

    if not entrega:
        raise HTTPException(
            status_code=404,
            detail="Entrega não encontrada.",
        )

    exigir_acesso_a_entrega(entrega, usuario_atual)

    if entrega.status != "EM_ROTA":
        raise HTTPException(
            status_code=400,
            detail="Somente uma entrega em rota pode ser marcada como não entregue.",
        )

    agora = datetime.now()
    entrega.status = "NAO_ENTREGUE"
    entrega.motivo_nao_entrega = dados.motivo
    entrega.data_ultima_tentativa = agora
    entrega.id_usuario_ultima_tentativa = usuario_atual.id_usuario

    historico = Historico(
        id_usuario=usuario_atual.id_usuario,
        tipo_registro="ENTREGA",
        id_registro=entrega.id_entrega,
        acao="NAO_ENTREGA",
        descricao=f"Tentativa de entrega não concluída. Motivo: {dados.motivo}",
        data_hora=agora,
    )
    notificacao = Notificacao(
        id_usuario=entrega.id_usuario_cadastro,
        titulo="Entrega não concluída",
        mensagem=(
            f"A entrega {entrega.id_entrega} não foi concluída. "
            f"Motivo: {dados.motivo}"
        ),
        lida=False,
        data_hora=agora,
    )
    db.add(historico)
    db.add(notificacao)
    db.commit()
    db.refresh(entrega)

    return entrega


@router.patch(
    "/{id_entrega}/entregue",
    response_model=EntregaResposta
)
def marcar_entregue(
    id_entrega: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis(
            "ENTREGADOR",
            "ADMINISTRADOR"
        )
    )
):
    return alterar_status_entrega(
        id_entrega,
        "ENTREGUE",
        db,
        usuario_atual
    )


@router.patch(
    "/{id_entrega}/comprovante",
    response_model=EntregaResposta
)
def anexar_comprovante_entrega(
    id_entrega: int,
    dados: ComprovanteEntregaAtualizar,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis("ENTREGADOR", "ADMINISTRADOR")
    )
):
    entrega = db.query(Entrega).filter(
        Entrega.id_entrega == id_entrega
    ).with_for_update().first()

    if not entrega:
        raise HTTPException(
            status_code=404,
            detail="Entrega não encontrada."
        )

    exigir_acesso_a_entrega(entrega, usuario_atual)

    if entrega.status not in ["EM_ROTA", "ENTREGUE"]:
        raise HTTPException(
            status_code=400,
            detail="O comprovante só pode ser anexado quando a entrega estiver em rota ou concluída."
        )

    from app.routes.arquivos import resolver_arquivo_entrega

    if resolver_arquivo_entrega(dados.comprovante_entrega) is None:
        raise HTTPException(
            status_code=400,
            detail="Envie um arquivo válido antes de anexar o comprovante."
        )

    entrega.comprovante_entrega = dados.comprovante_entrega

    historico = Historico(
        id_usuario=usuario_atual.id_usuario,
        tipo_registro="ENTREGA",
        id_registro=entrega.id_entrega,
        acao="ANEXO_COMPROVANTE",
        descricao="Comprovante de entrega anexado.",
        data_hora=datetime.now()
    )
    db.add(historico)

    db.commit()
    db.refresh(entrega)

    return entrega


@router.patch(
    "/{id_entrega}/cancelar",
    response_model=EntregaResposta,
)
def cancelar_entrega(
    id_entrega: int,
    dados: EntregaCancelar,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis("ADMINISTRADOR")
    ),
):
    entrega = db.query(Entrega).filter(
        Entrega.id_entrega == id_entrega
    ).with_for_update().first()

    if not entrega:
        raise HTTPException(
            status_code=404,
            detail="Entrega não encontrada.",
        )

    if entrega.status == "CANCELADA":
        raise HTTPException(
            status_code=400,
            detail="Esta entrega já foi cancelada.",
        )

    if entrega.status in ["EM_ROTA", "ENTREGUE"]:
        raise HTTPException(
            status_code=400,
            detail=(
                "Não é possível cancelar uma entrega que já entrou em rota "
                "ou foi concluída."
            ),
        )

    status_anterior = entrega.status
    agora = datetime.now()
    entrega.status = "CANCELADA"
    entrega.motivo_cancelamento = dados.motivo
    entrega.data_cancelamento = agora
    entrega.id_usuario_cancelamento = usuario_atual.id_usuario

    historico = Historico(
        id_usuario=usuario_atual.id_usuario,
        tipo_registro="ENTREGA",
        id_registro=entrega.id_entrega,
        acao="CANCELAMENTO",
        descricao=(
            f"Entrega cancelada quando estava em {status_anterior}. "
            f"Motivo: {dados.motivo}"
        ),
        data_hora=agora,
    )
    db.add(historico)
    db.commit()
    db.refresh(entrega)

    return entrega

@router.get(
    "/{id_entrega}/historico",
    response_model=list[HistoricoResposta]
)
def listar_historico_entrega(
    id_entrega: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(
        exigir_perfis(
            "FUNCIONARIO",
            "ESTOQUE",
            "ADMINISTRADOR",
            "ENTREGADOR"
        )
    )
):
    entrega = db.query(Entrega).filter(
        Entrega.id_entrega == id_entrega
    ).first()

    if not entrega:
        raise HTTPException(
            status_code=404,
            detail="Entrega não encontrada."
        )

    exigir_acesso_a_entrega(entrega, usuario_atual)

    historicos = db.query(Historico).filter(
        Historico.tipo_registro == "ENTREGA",
        Historico.id_registro == id_entrega
    ).order_by(
        Historico.data_hora.asc()
    ).all()

    return historicos
