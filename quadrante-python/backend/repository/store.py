"""Implementação in-memory das portas de persistência.

Espelha internal/repository/memory/memory.go, mas troca as fatias (slices)
e mapas do Go pelas estruturas de dados clássicas exigidas pela disciplina,
cada uma usada onde seu comportamento é a escolha certa — não decorativa:

- Vetor        -> cadastro de fiscais (poucas inserções, muita leitura/percorrimento)
- ListaEncadeada -> carteira de condomínios de CADA fiscal (alta rotatividade por
                    realocação: religar dois ponteiros é O(1), contra deslocar um vetor)
- Pilha (LIFO) -> histórico de realocações, para desfazer a mais recente primeiro
- Fila (FIFO)  -> solicitações de ausência pendentes, processadas na ordem de chegada

Hash maps (dict nativo) seguem para o que já era hash map no Go (ausências e
realocações por ID) — não é uma das quatro estruturas do syllabus, é a
estrutura auxiliar certa para lookup O(1) por chave, exatamente como no Go.
"""

import threading
from datetime import datetime
from typing import Optional

from backend.domain.ausencia import Ausencia, Realocacao
from backend.domain.condominio import Condominio, GEOCODE_OK
from backend.domain.fiscal import Fiscal, PAPEL_FISCAL_CAMPO
from backend.domain.rota import Rota
from backend.estruturas import Vetor, ListaEncadeada, Pilha, Fila


class FiscalNaoEncontradoError(Exception):
    pass


class CondominioNaoEncontradoError(Exception):
    pass


class CarteiraSemGeocodeError(Exception):
    pass


class Store:
    def __init__(self):
        self._lock = threading.Lock()
        self._seq = 0

        self.fiscais = Vetor()
        self._fiscais_por_email: dict[str, Fiscal] = {}

        # fiscal_id -> ListaEncadeada[Condominio] (a "carteira" propriamente dita)
        self._carteiras: dict[str, ListaEncadeada] = {}
        # condominio_id -> fiscal_id, só para achar em qual carteira um condomínio
        # está sem percorrer todas — o dado de verdade é sempre a ListaEncadeada.
        self._titular_de: dict[str, str] = {}
        # condominio_id -> Condominio, cache de leitura (o dado de verdade também
        # é o nó na ListaEncadeada; mantido em sincronia nas mesmas operações).
        self._condominios: dict[str, Condominio] = {}

        self._ausencias: dict[str, Ausencia] = {}
        self._realocacoes: dict[str, Realocacao] = {}
        self._rotas: dict[str, Rota] = {}  # fiscal_id -> última rota gerada

        self.historico_realocacoes = Pilha()  # ids de Realocacao, mais recente no topo
        self.fila_solicitacoes_ausencia = Fila()  # solicitações aguardando processamento

    # ---- utilidades ---------------------------------------------------

    def _novo_id(self, prefixo: str) -> str:
        self._seq += 1
        return f"{prefixo}-{self._seq:03d}"

    def _carteira_de(self, fiscal_id: str) -> ListaEncadeada:
        if fiscal_id not in self._carteiras:
            self._carteiras[fiscal_id] = ListaEncadeada()
        return self._carteiras[fiscal_id]

    # ---- seed -----------------------------------------------------------

    def seed_fiscal(
        self,
        nome: str,
        email: str,
        papel: str,
        senha_hash: str = "",
        salt: str = "",
    ) -> str:
        with self._lock:
            fid = self._novo_id("fisc")
            fiscal = Fiscal(
                id=fid,
                nome=nome,
                email=email,
                papel=papel,
                senha_hash=senha_hash,
                salt=salt,
            )
            self.fiscais.adicionar(fiscal)
            if email:
                self._fiscais_por_email[email.strip().lower()] = fiscal
            self._carteiras[fid] = ListaEncadeada()
            return fid

    def seed_condominio(
        self, nome: str, endereco: str, lat: float, lng: float, status: str, fiscal_titular_id: str
    ) -> str:
        with self._lock:
            cid = self._novo_id("cond")
            condominio = Condominio(
                id=cid,
                nome=nome,
                endereco_formatado=endereco,
                latitude=lat,
                longitude=lng,
                geocode_status=status,
                fiscal_titular_id=fiscal_titular_id,
            )
            self._condominios[cid] = condominio
            self._titular_de[cid] = fiscal_titular_id
            self._carteira_de(fiscal_titular_id).inserir_no_fim(condominio)
            return cid

    def adicionar_condominio(
        self, nome: str, endereco: str, lat: float, lng: float, fiscal_titular_id: str
    ) -> Condominio:
        cid = self.seed_condominio(nome, endereco, lat, lng, GEOCODE_OK, fiscal_titular_id)
        return self._condominios[cid]

    # ---- FiscalRepository -------------------------------------------------

    def listar(self, somente_ativos: bool = True) -> list[Fiscal]:
        with self._lock:
            if not somente_ativos:
                return self.fiscais.para_lista()
            return self.fiscais.filtrar(lambda f: f.ativo).para_lista()

    def buscar_fiscal(self, fiscal_id: str) -> Fiscal:
        fiscal = self.fiscais.encontrar(lambda f: f.id == fiscal_id)
        if fiscal is None:
            raise FiscalNaoEncontradoError(fiscal_id)
        return fiscal

    def buscar_por_email(self, email: str) -> Optional[Fiscal]:
        with self._lock:
            return self._fiscais_por_email.get(email.strip().lower())

    def atualizar_credenciais(self, fiscal_id: str, senha_hash: str, salt: str) -> None:
        with self._lock:
            fiscal = self.fiscais.encontrar(lambda f: f.id == fiscal_id)
            if fiscal is None:
                raise FiscalNaoEncontradoError(fiscal_id)
            fiscal.senha_hash = senha_hash
            fiscal.salt = salt


    # ---- CondominioRepository ----------------------------------------------

    def buscar_condominio(self, condominio_id: str) -> Optional[Condominio]:
        return self._condominios.get(condominio_id)

    def listar_por_fiscal(self, fiscal_id: str) -> list[Condominio]:
        with self._lock:
            carteira = self._carteira_de(fiscal_id)
            return sorted(carteira.para_lista(), key=lambda c: c.id)

    def listar_todos_geocodificados(self) -> list[Condominio]:
        with self._lock:
            geocodificados = [c for c in self._condominios.values() if c.tem_localizacao()]
            return sorted(geocodificados, key=lambda c: c.id)

    def atualizar_fiscal_titular(self, condominio_id: str, fiscal_id: str) -> None:
        with self._lock:
            if condominio_id not in self._condominios:
                raise CondominioNaoEncontradoError(condominio_id)

            origem_id = self._titular_de[condominio_id]
            if origem_id == fiscal_id:
                return

            condominio = self._carteira_de(origem_id).remover_onde(lambda c: c.id == condominio_id)
            if condominio is None:
                condominio = self._condominios[condominio_id]

            condominio.fiscal_titular_id = fiscal_id
            self._condominios[condominio_id] = condominio
            self._titular_de[condominio_id] = fiscal_id
            self._carteira_de(fiscal_id).inserir_no_fim(condominio)

    def centroide_da_carteira(self, fiscal_id: str) -> tuple[float, float]:
        with self._lock:
            soma_lat = soma_lng = 0.0
            n = 0
            for c in self._carteira_de(fiscal_id):
                if not c.tem_localizacao():
                    continue
                soma_lat += c.latitude
                soma_lng += c.longitude
                n += 1
            if n == 0:
                raise CarteiraSemGeocodeError(fiscal_id)
            return soma_lat / n, soma_lng / n

    # ---- AusenciaRepository -------------------------------------------------

    def criar_ausencia(self, ausencia: Ausencia) -> Ausencia:
        with self._lock:
            ausencia.id = self._novo_id("ausc")
            ausencia.criado_em = datetime.utcnow()
            self._ausencias[ausencia.id] = ausencia
            return ausencia

    def listar_ativas_em(self, data: datetime) -> list[Ausencia]:
        with self._lock:
            ativas = [a for a in self._ausencias.values() if a.cobre(data)]
            return sorted(ativas, key=lambda a: a.id)

    # ---- RealocacaoRepository ----------------------------------------------

    def criar_realocacao(self, realocacao: Realocacao) -> Realocacao:
        with self._lock:
            realocacao.id = self._novo_id("real")
            realocacao.ativa = True
            realocacao.criado_em = datetime.utcnow()
            self._realocacoes[realocacao.id] = realocacao
            self.historico_realocacoes.empilhar(realocacao.id)
            return realocacao

    def listar_expiradas(self, hoje: datetime) -> list[Realocacao]:
        with self._lock:
            dia = hoje.replace(hour=0, minute=0, second=0, microsecond=0)
            expiradas = []
            for r in self._realocacoes.values():
                if not r.ativa:
                    continue
                ausencia = self._ausencias.get(r.ausencia_id)
                if ausencia is None:
                    continue
                if ausencia.data_fim < dia:
                    expiradas.append(r)
            return sorted(expiradas, key=lambda r: r.id)

    def reverter(self, realocacao_id: str) -> None:
        with self._lock:
            realocacao = self._realocacoes.get(realocacao_id)
            if realocacao is None:
                raise KeyError(f"realocacao {realocacao_id} não encontrada")
            realocacao.ativa = False
            realocacao.revertida_em = datetime.utcnow()

    def buscar_realocacao(self, realocacao_id: str) -> Optional[Realocacao]:
        return self._realocacoes.get(realocacao_id)

    def desfazer_ultima_realocacao(self) -> Optional[Realocacao]:
        """Usa a Pilha de histórico para desfazer manualmente a realocação
        mais recente ainda ativa — distinto de ReverterExpiradas (que reverte
        por vencimento da ausência, não por ordem de pilha)."""
        with self._lock:
            pendentes = Pilha()
            desfeita: Optional[Realocacao] = None
            while not self.historico_realocacoes.esta_vazia():
                realocacao_id = self.historico_realocacoes.desempilhar()
                realocacao = self._realocacoes.get(realocacao_id)
                if realocacao is not None and realocacao.ativa:
                    desfeita = realocacao
                    break
                pendentes.empilhar(realocacao_id)
            while not pendentes.esta_vazia():
                self.historico_realocacoes.empilhar(pendentes.desempilhar())

        if desfeita is None:
            return None

        self.atualizar_fiscal_titular(desfeita.condominio_id, desfeita.fiscal_origem_id)
        with self._lock:
            desfeita.ativa = False
            desfeita.revertida_em = datetime.utcnow()
        return desfeita

    # ---- RotaRepository -----------------------------------------------------

    def salvar_rota(self, rota: Rota) -> Rota:
        with self._lock:
            rota.gerada_em = datetime.utcnow()
            self._rotas[rota.fiscal_id] = rota
            return rota

    def rota_atual(self, fiscal_id: str) -> Optional[Rota]:
        return self._rotas.get(fiscal_id)

    # ---- consultas auxiliares p/ API ---------------------------------------

    def fiscais_de_campo(self, somente_ativos: bool = True) -> list[Fiscal]:
        campo = [f for f in self.listar(somente_ativos) if f.papel == PAPEL_FISCAL_CAMPO]
        return sorted(campo, key=lambda f: f.id)

    def carga_por_fiscal(self) -> dict[str, int]:
        with self._lock:
            return {fid: len(carteira) for fid, carteira in self._carteiras.items()}
