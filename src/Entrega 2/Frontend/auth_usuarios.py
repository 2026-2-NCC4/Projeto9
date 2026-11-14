"""Cadastro acadêmico do DashBird com senhas protegidas por PBKDF2.

SQLite: persiste no computador do usuário em ~/.dashbird/usuarios.sqlite3.
PostgreSQL: defina CTI_DATABASE_URL ou [auth].database_url em secrets.toml.

Não substitui um provedor de identidade corporativo. Ausentes neste MVP:
verificação de e-mail no cadastro e proteção global contra ataques.
"""

from __future__ import annotations

import base64
from collections.abc import Callable
from contextlib import closing
import hashlib
import hmac
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
from urllib.parse import urlsplit

ITERACOES = 310_000
DOMINIO_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
VALIDADE_RECUPERACAO_SEGUNDOS = 15 * 60
INTERVALO_RECUPERACAO_SEGUNDOS = 60
CODIGO_RECUPERACAO = re.compile(r"^[A-Za-z0-9_-]{43}$")


class ErroCadastro(ValueError):
    """Informações informadas no cadastro são inválidas."""


class EmailJaCadastrado(ErroCadastro):
    """Endereço já possui uma conta."""


class ErroBancoUsuarios(RuntimeError):
    """Falha ao consultar ou atualizar o banco de contas."""


class ErroRecuperacao(ErroCadastro):
    """Chave ou código de recuperação inválido, expirado ou já utilizado."""


def validar_nome(nome: str) -> str:
    nome = " ".join(nome.strip().split())
    if len(nome) < 3 or len(nome) > 100:
        raise ErroCadastro("Informe um nome com 3 a 100 caracteres.")
    return nome


def normalizar_email(email: str) -> str:
    email = email.strip().lower()
    if len(email) > 254 or not DOMINIO_EMAIL.fullmatch(email):
        raise ErroCadastro("Informe um endereço de e-mail válido.")
    return email


def validar_senha(senha: str) -> None:
    if not (10 <= len(senha) <= 128):
        raise ErroCadastro("A senha deve ter entre 10 e 128 caracteres.")
    if not any(c.isalpha() for c in senha) or not any(c.isdigit() for c in senha):
        raise ErroCadastro("Use letras e pelo menos um número na senha.")


def gerar_hash_senha(senha: str) -> str:
    validar_senha(senha)
    sal = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), sal, ITERACOES)
    return "pbkdf2_sha256${}${}${}".format(
        ITERACOES,
        base64.b64encode(sal).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def conferir_senha(senha: str, senha_armazenada: str) -> bool:
    try:
        algoritmo, iteracoes, sal_b64, hash_b64 = senha_armazenada.split("$", 3)
        if algoritmo != "pbkdf2_sha256":
            return False
        rounds = int(iteracoes)
        if not 100_000 <= rounds <= 2_000_000:
            return False
        sal = base64.b64decode(sal_b64, validate=True)
        resultado = base64.b64decode(hash_b64, validate=True)
        if len(sal) != 16 or len(resultado) != 32:
            return False
        candidato = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), sal, rounds)
        return hmac.compare_digest(resultado, candidato)
    except (ValueError, TypeError, UnicodeError):
        return False


class BancoUsuarios:
    def __init__(self, database_url: str = "", sqlite_path: str | Path | None = None):
        self.database_url = database_url.strip()
        if self.database_url:
            parsed = urlsplit(self.database_url)
            if parsed.scheme not in ("postgresql", "postgres"):
                raise ErroBancoUsuarios("CTI_DATABASE_URL deve ser uma URL PostgreSQL.")
        self.sqlite_path = Path(sqlite_path) if sqlite_path else Path(
            os.getenv("CTI_USERS_DB_PATH", str(Path.home() / ".dashbird" / "usuarios.sqlite3"))
        )

    @property
    def remoto(self) -> bool:
        return bool(self.database_url)

    def _conexao(self):
        if self.remoto:
            try:
                import psycopg
            except ImportError as erro:
                raise ErroBancoUsuarios(
                    "Instale psycopg[binary] para usar o banco PostgreSQL."
                ) from erro
            return psycopg.connect(self.database_url, connect_timeout=8)
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(str(self.sqlite_path), timeout=10)
        con.execute("PRAGMA busy_timeout = 10000")
        return con

    def _criar_tabela(self, con) -> None:
        if self.remoto:
            con.execute("""
                CREATE TABLE IF NOT EXISTS dashbird_usuarios (
                    id BIGSERIAL PRIMARY KEY,
                    nome TEXT NOT NULL,
                    email TEXT NOT NULL,
                    email_normalizado TEXT NOT NULL UNIQUE,
                    senha_hash TEXT NOT NULL,
                    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
        else:
            con.execute("""
                CREATE TABLE IF NOT EXISTS dashbird_usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    email TEXT NOT NULL,
                    email_normalizado TEXT NOT NULL UNIQUE,
                    senha_hash TEXT NOT NULL,
                    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def _criar_tabela_chaves(self, con) -> None:
        self._criar_tabela(con)
        con.execute("""
            CREATE TABLE IF NOT EXISTS dashbird_chaves_recuperacao (
                email_normalizado TEXT PRIMARY KEY
                    REFERENCES dashbird_usuarios(email_normalizado) ON DELETE CASCADE,
                chave_hash TEXT NOT NULL UNIQUE
            )
        """)

    def _salvar_chave_recuperacao(self, con, email: str, chave: str) -> None:
        placeholder = "%s" if self.remoto else "?"
        con.execute(
            "INSERT INTO dashbird_chaves_recuperacao (email_normalizado, chave_hash) "
            f"VALUES ({placeholder}, {placeholder}) "
            "ON CONFLICT (email_normalizado) DO UPDATE SET chave_hash = excluded.chave_hash",
            (email, hashlib.sha256(chave.encode("ascii")).hexdigest()),
        )

    def cadastrar(self, nome: str, email: str, senha: str) -> dict:
        """Cria a conta e retorna sua chave de recuperação uma única vez."""
        nome = validar_nome(nome)
        email = normalizar_email(email)
        senha_hash = gerar_hash_senha(senha)
        chave = secrets.token_urlsafe(32)
        params = (nome, email, email, senha_hash)
        placeholder = "%s" if self.remoto else "?"
        parametros = ", ".join([placeholder] * 4)
        try:
            with closing(self._conexao()) as con:
                with con:
                    self._criar_tabela_chaves(con)
                    con.execute(
                        "INSERT INTO dashbird_usuarios "
                        "(nome, email, email_normalizado, senha_hash) "
                        f"VALUES ({parametros})",
                        params,
                    )
                    self._salvar_chave_recuperacao(con, email, chave)
        except Exception as erro:
            if isinstance(erro, sqlite3.IntegrityError) or (
                self.remoto and getattr(erro, "sqlstate", None) == "23505"
            ):
                raise EmailJaCadastrado("Este e-mail já está cadastrado.") from erro
            if isinstance(erro, ErroBancoUsuarios):
                raise
            raise ErroBancoUsuarios("Não foi possível salvar o cadastro.") from erro
        return {"nome": nome, "email": email, "chave_recuperacao": chave}

    def autenticar(self, identificador: str, senha: str) -> dict | None:
        try:
            email = normalizar_email(identificador)
        except ErroCadastro:
            return None
        if not senha:
            return None
        placeholder = "%s" if self.remoto else "?"
        try:
            with closing(self._conexao()) as con:
                with con:
                    self._criar_tabela(con)
                    cursor = con.execute(
                        "SELECT nome, email, senha_hash FROM dashbird_usuarios "
                        f"WHERE email_normalizado = {placeholder}",
                        (email,),
                    )
                    registro = cursor.fetchone()
        except Exception as erro:
            if isinstance(erro, ErroBancoUsuarios):
                raise
            raise ErroBancoUsuarios("Não foi possível consultar as contas.") from erro
        if not registro or not conferir_senha(senha, registro[2]):
            return None
        return {"nome": registro[0], "email": registro[1]}

    def _criar_tabela_recuperacao(self, con) -> None:
        self._criar_tabela_chaves(con)
        con.execute("""
            CREATE TABLE IF NOT EXISTS dashbird_recuperacao_senha (
                email_normalizado TEXT PRIMARY KEY
                    REFERENCES dashbird_usuarios(email_normalizado) ON DELETE CASCADE,
                codigo_hash TEXT NOT NULL UNIQUE,
                expira_em BIGINT NOT NULL,
                solicitado_em BIGINT NOT NULL
            )
        """)

    def gerar_chave_recuperacao(self, email: str, senha_atual: str) -> str:
        """Emite uma nova chave após confirmar a senha atual da conta.

        Contas antigas também podem usar este método. O bloqueio impede
        emitir uma chave com uma senha que mudou durante a operação.
        """
        email = normalizar_email(email)
        chave = secrets.token_urlsafe(32)
        placeholder = "%s" if self.remoto else "?"
        try:
            with closing(self._conexao()) as con:
                with con:
                    if not self.remoto:
                        con.execute("BEGIN IMMEDIATE")
                    self._criar_tabela_chaves(con)
                    bloqueio = " FOR NO KEY UPDATE" if self.remoto else ""
                    registro = con.execute(
                        "SELECT senha_hash FROM dashbird_usuarios "
                        f"WHERE email_normalizado = {placeholder}{bloqueio}",
                        (email,),
                    ).fetchone()
                    if not registro or not conferir_senha(senha_atual, registro[0]):
                        raise ErroCadastro("E-mail ou senha atual inválidos.")
                    self._salvar_chave_recuperacao(con, email, chave)
        except (ErroCadastro, ErroBancoUsuarios):
            raise
        except Exception as erro:
            raise ErroBancoUsuarios("Não foi possível gerar a chave de recuperação.") from erro
        return chave

    def solicitar_recuperacao(
        self, email: str, enviar_codigo: Callable[[str, str], None]
    ) -> None:
        """Envia um código sem revelar se a conta existe ou está em espera.

        Somente o hash do código é persistido. Um novo envio invalida o
        anterior e exige um intervalo de 60 segundos, inclusive entre sessões.
        O envio ocorre após o commit; falhas no e-mail mantêm esse intervalo.
        """
        email = normalizar_email(email)
        codigo = secrets.token_urlsafe(32)
        codigo_hash = hashlib.sha256(codigo.encode("ascii")).hexdigest()
        agora = int(time.time())
        placeholder = "%s" if self.remoto else "?"
        try:
            with closing(self._conexao()) as con:
                with con:
                    self._criar_tabela_recuperacao(con)
                    cursor = con.execute(
                        "INSERT INTO dashbird_recuperacao_senha "
                        "(email_normalizado, codigo_hash, expira_em, solicitado_em) "
                        f"SELECT email_normalizado, {placeholder}, {placeholder}, {placeholder} "
                        f"FROM dashbird_usuarios WHERE email_normalizado = {placeholder} "
                        "ON CONFLICT (email_normalizado) DO UPDATE SET "
                        "codigo_hash = excluded.codigo_hash, "
                        "expira_em = excluded.expira_em, "
                        "solicitado_em = excluded.solicitado_em "
                        f"WHERE dashbird_recuperacao_senha.solicitado_em <= {placeholder}",
                        (codigo_hash, agora + VALIDADE_RECUPERACAO_SEGUNDOS,
                         agora, email, agora - INTERVALO_RECUPERACAO_SEGUNDOS),
                    )
                    enviar = cursor.rowcount == 1
        except Exception as erro:
            if isinstance(erro, ErroBancoUsuarios):
                raise
            raise ErroBancoUsuarios("Não foi possível solicitar a recuperação de senha.") from erro
        if enviar:
            enviar_codigo(email, codigo)

    def redefinir_senha(self, email: str, codigo: str, nova_senha: str) -> str:
        """Aceita a chave guardada ou um código de e-mail ainda válido.

        Troca a senha, invalida as credenciais de recuperação anteriores e
        retorna uma nova chave, tudo na mesma transação.
        """
        email = normalizar_email(email)
        codigo = codigo.strip()
        mensagem_invalido = "Chave ou código de recuperação inválido, expirado ou já utilizado."
        if not CODIGO_RECUPERACAO.fullmatch(codigo):
            raise ErroRecuperacao(mensagem_invalido)
        codigo_hash = hashlib.sha256(codigo.encode("ascii")).hexdigest()
        senha_hash = gerar_hash_senha(nova_senha)
        nova_chave = secrets.token_urlsafe(32)
        placeholder = "%s" if self.remoto else "?"
        try:
            with closing(self._conexao()) as con:
                with con:
                    self._criar_tabela_recuperacao(con)
                    if self.remoto:
                        con.execute(
                            "SELECT id FROM dashbird_usuarios "
                            f"WHERE email_normalizado = {placeholder} FOR NO KEY UPDATE",
                            (email,),
                        ).fetchone()
                    cursor = con.execute(
                        "DELETE FROM dashbird_recuperacao_senha "
                        f"WHERE email_normalizado = {placeholder} "
                        f"AND codigo_hash = {placeholder} AND expira_em > {placeholder}",
                        (email, codigo_hash, int(time.time())),
                    )
                    codigo_valido = cursor.rowcount == 1
                    cursor = con.execute(
                        "DELETE FROM dashbird_chaves_recuperacao "
                        f"WHERE email_normalizado = {placeholder} AND chave_hash = {placeholder}",
                        (email, codigo_hash),
                    )
                    chave_valida = cursor.rowcount == 1
                    if not (codigo_valido or chave_valida):
                        raise ErroRecuperacao(mensagem_invalido)
                    cursor = con.execute(
                        f"UPDATE dashbird_usuarios SET senha_hash = {placeholder} "
                        f"WHERE email_normalizado = {placeholder}",
                        (senha_hash, email),
                    )
                    if cursor.rowcount != 1:
                        raise ErroRecuperacao(mensagem_invalido)
                    con.execute(
                        f"DELETE FROM dashbird_recuperacao_senha WHERE email_normalizado = {placeholder}",
                        (email,),
                    )
                    self._salvar_chave_recuperacao(con, email, nova_chave)
        except (ErroRecuperacao, ErroBancoUsuarios):
            raise
        except Exception as erro:
            raise ErroBancoUsuarios("Não foi possível redefinir a senha.") from erro
        return nova_chave
