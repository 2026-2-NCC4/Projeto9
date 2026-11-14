"""Recuperação de senha com banco temporário e SMTP simulado, sem rede."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
import smtplib
import sqlite3
import ssl
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

FRONTEND = Path(__file__).resolve().parents[2] / 'Frontend'
if str(FRONTEND) not in sys.path:
    sys.path.insert(0, str(FRONTEND))

from auth_usuarios import (
    BancoUsuarios,
    ErroBancoUsuarios,
    ErroCadastro,
    ErroRecuperacao,
    INTERVALO_RECUPERACAO_SEGUNDOS,
    VALIDADE_RECUPERACAO_SEGUNDOS,
)
from email_recuperacao import EmailRecuperacao, ErroEnvioEmail


class TesteRecuperacaoSenha(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.banco = BancoUsuarios(sqlite_path=Path(self.tempdir.name) / 'usuarios.sqlite3')
        self.email = 'ana@exemplo.com'
        self.senha_antiga = 'SenhaSegura2026'
        self.senha_nova = 'NovaSenhaSegura2027'
        conta = self.banco.cadastrar('Ana Maria', self.email, self.senha_antiga)
        self.chave_original = conta['chave_recuperacao']
        self.enviar = Mock()

    def tearDown(self):
        self.tempdir.cleanup()

    def solicitar(self, instante=1000):
        with patch('auth_usuarios.time.time', return_value=instante):
            self.banco.solicitar_recuperacao(self.email, self.enviar)
        return self.enviar.call_args.args[1]

    def redefinir(self, codigo, instante=1001, email=None, senha=None):
        with patch('auth_usuarios.time.time', return_value=instante):
            return self.banco.redefinir_senha(
                email or self.email, codigo, senha or self.senha_nova
            )

    def test_solicitacao_normaliza_email_e_nao_muda_senha(self):
        resultado = self.banco.solicitar_recuperacao(' ANA@EXEMPLO.COM ', self.enviar)
        self.assertIsNone(resultado)
        self.enviar.assert_called_once()
        email, codigo = self.enviar.call_args.args
        self.assertEqual(email, self.email)
        self.assertEqual(len(codigo), 43)
        self.assertIsNotNone(self.banco.autenticar(self.email, self.senha_antiga))

    def test_troca_senha_persiste_e_codigo_so_funciona_uma_vez(self):
        codigo = self.solicitar()
        outro_banco = BancoUsuarios(sqlite_path=self.banco.sqlite_path)
        with patch('auth_usuarios.time.time', return_value=1001):
            outro_banco.redefinir_senha(' ANA@EXEMPLO.COM ', f' {codigo}\n', self.senha_nova)
        self.assertIsNone(self.banco.autenticar(self.email, self.senha_antiga))
        self.assertIsNotNone(self.banco.autenticar(self.email, self.senha_nova))
        with self.assertRaises(ErroRecuperacao):
            self.redefinir(codigo, senha='OutraSenhaValida2028')

    def test_email_desconhecido_tem_mesmo_retorno_sem_enviar(self):
        resultado = self.banco.solicitar_recuperacao('desconhecido@exemplo.com', self.enviar)
        self.assertIsNone(resultado)
        self.enviar.assert_not_called()
        with closing(sqlite3.connect(self.banco.sqlite_path)) as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM dashbird_recuperacao_senha').fetchone()[0], 0)

    def test_email_invalido_nao_envia(self):
        with self.assertRaises(ErroCadastro):
            self.banco.solicitar_recuperacao('email-invalido', self.enviar)
        self.enviar.assert_not_called()

    def test_codigo_e_senha_nao_sao_armazenados_em_texto_puro(self):
        codigo = self.solicitar()
        dados = self.banco.sqlite_path.read_bytes()
        self.assertNotIn(codigo.encode('ascii'), dados)
        with closing(sqlite3.connect(self.banco.sqlite_path)) as con:
            codigo_hash, validade = con.execute(
                'SELECT codigo_hash, expira_em FROM dashbird_recuperacao_senha'
            ).fetchone()
        self.assertEqual(len(codigo_hash), 64)
        self.assertEqual(validade, 1000 + VALIDADE_RECUPERACAO_SEGUNDOS)
        self.redefinir(codigo)
        self.assertNotIn(self.senha_nova.encode('utf-8'), self.banco.sqlite_path.read_bytes())

    def test_codigo_expira_no_limite_de_15_minutos(self):
        codigo = self.solicitar()
        with self.assertRaises(ErroRecuperacao):
            self.redefinir(codigo, instante=1000 + VALIDADE_RECUPERACAO_SEGUNDOS)
        self.assertIsNotNone(self.banco.autenticar(self.email, self.senha_antiga))

    def test_codigo_valido_ate_antes_do_limite(self):
        self.redefinir(self.solicitar(), instante=999 + VALIDADE_RECUPERACAO_SEGUNDOS)
        self.assertIsNotNone(self.banco.autenticar(self.email, self.senha_nova))

    def test_codigo_nao_pode_ser_usado_em_outra_conta(self):
        self.banco.cadastrar('Bruno Silva', 'bruno@exemplo.com', self.senha_antiga)
        codigo = self.solicitar()
        for email in ('bruno@exemplo.com', 'inexistente@exemplo.com'):
            with self.subTest(email=email), self.assertRaises(ErroRecuperacao):
                self.redefinir(codigo, email=email)
        self.assertIsNotNone(self.banco.autenticar('bruno@exemplo.com', self.senha_antiga))
        self.redefinir(codigo)

    def test_codigo_invalido_nao_consume_codigo_correto(self):
        codigo = self.solicitar()
        for invalido in ('', '123456', 'ç' * 43, 'x' * 1000, 'A' * 43):
            with self.subTest(codigo=invalido), self.assertRaises(ErroRecuperacao):
                self.redefinir(invalido)
        self.redefinir(codigo)

    def test_senha_fraca_nao_consume_codigo(self):
        codigo = self.solicitar()
        for senha in ('Abc123', 'SenhaSemNumeros', 'x1' * 65):
            with self.subTest(senha=senha), self.assertRaises(ErroCadastro):
                self.redefinir(codigo, senha=senha)
        self.redefinir(codigo)

    def test_intervalo_persiste_em_outra_instancia_sem_invalidar_codigo(self):
        codigo = self.solicitar()
        outro_banco = BancoUsuarios(sqlite_path=self.banco.sqlite_path)
        with patch('auth_usuarios.time.time', return_value=1059):
            self.assertIsNone(outro_banco.solicitar_recuperacao(self.email, self.enviar))
        self.enviar.assert_called_once()
        self.redefinir(codigo, instante=1059)

    def test_reenvio_apos_intervalo_invalida_codigo_anterior(self):
        antigo = self.solicitar()
        novo = self.solicitar(1000 + INTERVALO_RECUPERACAO_SEGUNDOS)
        self.assertEqual(self.enviar.call_count, 2)
        self.assertNotEqual(antigo, novo)
        with self.assertRaises(ErroRecuperacao):
            self.redefinir(antigo, instante=1061)
        self.redefinir(novo, instante=1061)

    def test_falha_no_envio_mantem_senha_e_intervalo(self):
        self.enviar.side_effect = ErroEnvioEmail('Falha simulada')
        with self.assertRaises(ErroEnvioEmail):
            self.solicitar()
        self.assertIsNotNone(self.banco.autenticar(self.email, self.senha_antiga))
        self.enviar.reset_mock(side_effect=True)
        with patch('auth_usuarios.time.time', return_value=1001):
            self.banco.solicitar_recuperacao(self.email, self.enviar)
        self.enviar.assert_not_called()

    def test_falha_na_troca_faz_rollback_do_consumo_do_codigo(self):
        codigo = self.solicitar()
        with closing(sqlite3.connect(self.banco.sqlite_path)) as con:
            con.execute("CREATE TRIGGER impedir_troca BEFORE UPDATE ON dashbird_usuarios "
                        "BEGIN SELECT RAISE(ABORT, 'falha simulada'); END")
            con.commit()
        with self.assertRaises(ErroBancoUsuarios):
            self.redefinir(codigo)
        self.assertIsNotNone(self.banco.autenticar(self.email, self.senha_antiga))
        with closing(sqlite3.connect(self.banco.sqlite_path)) as con:
            con.execute('DROP TRIGGER impedir_troca')
            con.commit()
        self.redefinir(codigo)

    def test_duas_trocas_simultaneas_nao_reutilizam_codigo(self):
        codigo = self.solicitar()

        def trocar(senha):
            try:
                self.banco.redefinir_senha(self.email, codigo, senha)
                return True
            except ErroRecuperacao:
                return False

        with patch('auth_usuarios.time.time', return_value=1001):
            with ThreadPoolExecutor(max_workers=2) as executor:
                resultados = list(executor.map(trocar, (self.senha_nova, 'OutraSenha2028')))
        self.assertEqual(sorted(resultados), [False, True])

    def test_chave_do_cadastro_funciona_sem_email_e_gera_substituta(self):
        outro_banco = BancoUsuarios(sqlite_path=self.banco.sqlite_path)
        nova = outro_banco.redefinir_senha(self.email, self.chave_original, self.senha_nova)
        self.assertEqual(len(nova), 43)
        self.assertNotEqual(nova, self.chave_original)
        self.assertIsNone(self.banco.autenticar(self.email, self.senha_antiga))
        with self.assertRaises(ErroRecuperacao):
            self.redefinir(self.chave_original)
        self.banco.redefinir_senha(self.email, nova, 'TerceiraSenha2028')
        self.assertIsNotNone(self.banco.autenticar(self.email, 'TerceiraSenha2028'))
        self.enviar.assert_not_called()

    def test_chave_nao_tem_prazo_de_15_minutos_e_nao_e_exposta_no_login(self):
        self.redefinir(self.chave_original, instante=9_000_000_000)
        conta = self.banco.autenticar(self.email, self.senha_nova)
        self.assertEqual(set(conta), {'nome', 'email'})

    def test_chave_nao_e_persistida_em_texto_puro(self):
        self.assertNotIn(self.chave_original.encode('ascii'), self.banco.sqlite_path.read_bytes())
        with closing(sqlite3.connect(self.banco.sqlite_path)) as con:
            chave_hash = con.execute('SELECT chave_hash FROM dashbird_chaves_recuperacao').fetchone()[0]
        self.assertEqual(len(chave_hash), 64)

    def test_chave_de_outra_conta_e_senha_fraca_nao_consumem_chave(self):
        self.banco.cadastrar('Bruno Silva', 'bruno@exemplo.com', self.senha_antiga)
        with self.assertRaises(ErroRecuperacao):
            self.redefinir(self.chave_original, email='bruno@exemplo.com')
        with self.assertRaises(ErroCadastro):
            self.redefinir(self.chave_original, senha='curta123')
        self.redefinir(self.chave_original)

    def test_gerar_nova_chave_exige_senha_atual_e_revoga_anterior(self):
        with self.assertRaises(ErroCadastro):
            self.banco.gerar_chave_recuperacao(self.email, 'SenhaErrada2026')
        nova = self.banco.gerar_chave_recuperacao(' ANA@EXEMPLO.COM ', self.senha_antiga)
        with self.assertRaises(ErroRecuperacao):
            self.redefinir(self.chave_original)
        self.redefinir(nova)
        with self.assertRaises(ErroCadastro):
            self.banco.gerar_chave_recuperacao(self.email, self.senha_antiga)

    def test_conta_antiga_pode_gerar_chave(self):
        # Simula o banco anterior à existência das chaves de recuperação.
        with closing(sqlite3.connect(self.banco.sqlite_path)) as con:
            con.execute('DROP TABLE dashbird_chaves_recuperacao')
            con.commit()
        nova = self.banco.gerar_chave_recuperacao(self.email, self.senha_antiga)
        self.redefinir(nova)

    def test_recuperacao_por_chave_revoga_codigo_de_email_pendente(self):
        codigo = self.solicitar()
        self.redefinir(self.chave_original)
        with self.assertRaises(ErroRecuperacao):
            self.redefinir(codigo)

    def test_recuperacao_por_email_tambem_substitui_chave_guardada(self):
        nova = self.redefinir(self.solicitar())
        with self.assertRaises(ErroRecuperacao):
            self.redefinir(self.chave_original)
        self.redefinir(nova, senha='TerceiraSenha2028')

    def test_falha_ao_gerar_chave_reverte_troca_de_senha(self):
        with patch.object(self.banco, '_salvar_chave_recuperacao', side_effect=sqlite3.OperationalError):
            with self.assertRaises(ErroBancoUsuarios):
                self.redefinir(self.chave_original)
        self.assertIsNotNone(self.banco.autenticar(self.email, self.senha_antiga))
        self.redefinir(self.chave_original)

    def test_cadastro_e_chave_sao_salvos_na_mesma_transacao(self):
        with patch.object(self.banco, '_salvar_chave_recuperacao', side_effect=sqlite3.OperationalError):
            with self.assertRaises(ErroBancoUsuarios):
                self.banco.cadastrar('Bruno Silva', 'bruno@exemplo.com', self.senha_antiga)
        self.assertIsNone(self.banco.autenticar('bruno@exemplo.com', self.senha_antiga))


class TesteEmailRecuperacao(unittest.TestCase):
    def configuracao(self, **opcoes):
        return EmailRecuperacao(
            host='smtp.exemplo.com', remetente='acesso@exemplo.com',
            usuario='usuario-smtp', senha='segredo-smtp', **opcoes
        )

    @patch('email_recuperacao.smtplib.SMTP')
    def test_starttls_antes_de_autenticar_e_enviar(self, cliente):
        servidor = cliente.return_value.__enter__.return_value
        servidor.send_message.return_value = {}
        self.configuracao().enviar_codigo('ana@exemplo.com', 'codigo-de-teste')
        cliente.assert_called_once_with('smtp.exemplo.com', 587, timeout=10)
        self.assertEqual([chamada[0] for chamada in servidor.method_calls],
                         ['starttls', 'login', 'send_message'])
        contexto = servidor.starttls.call_args.kwargs['context']
        self.assertTrue(contexto.check_hostname)
        self.assertEqual(contexto.verify_mode, ssl.CERT_REQUIRED)
        servidor.login.assert_called_once_with('usuario-smtp', 'segredo-smtp')
        mensagem = servidor.send_message.call_args.args[0]
        self.assertEqual(mensagem['To'], 'ana@exemplo.com')
        self.assertEqual(mensagem['From'], 'acesso@exemplo.com')
        self.assertIn('codigo-de-teste', mensagem.get_content())
        self.assertIn('15 minutos', mensagem.get_content())
        self.assertNotIn('segredo-smtp', mensagem.as_string())

    @patch('email_recuperacao.smtplib.SMTP_SSL')
    def test_tls_implicito(self, cliente):
        servidor = cliente.return_value.__enter__.return_value
        servidor.send_message.return_value = {}
        self.configuracao(porta=465, ssl_implicito=True).enviar_codigo('ana@exemplo.com', 'codigo')
        self.assertEqual(cliente.call_args.args, ('smtp.exemplo.com', 465))
        self.assertTrue(cliente.call_args.kwargs['context'].check_hostname)
        servidor.starttls.assert_not_called()
        servidor.send_message.assert_called_once()

    @patch('email_recuperacao.smtplib.SMTP')
    def test_falha_tls_nao_envia_credenciais_ou_codigo(self, cliente):
        servidor = cliente.return_value.__enter__.return_value
        servidor.starttls.side_effect = smtplib.SMTPNotSupportedError('TLS indisponível')
        with self.assertRaises(ErroEnvioEmail):
            self.configuracao().enviar_codigo('ana@exemplo.com', 'codigo')
        servidor.login.assert_not_called()
        servidor.send_message.assert_not_called()

    @patch('email_recuperacao.smtplib.SMTP', side_effect=TimeoutError)
    def test_timeout_e_tratado(self, cliente):
        with self.assertRaises(ErroEnvioEmail):
            self.configuracao().enviar_codigo('ana@exemplo.com', 'codigo')

    @patch('email_recuperacao.smtplib.SMTP')
    def test_destinatario_recusado(self, cliente):
        servidor = cliente.return_value.__enter__.return_value
        servidor.send_message.return_value = {'ana@exemplo.com': (550, b'recusado')}
        with self.assertRaises(ErroEnvioEmail):
            self.configuracao().enviar_codigo('ana@exemplo.com', 'codigo')

    def test_configuracao_invalida(self):
        for porta in (0, 65536):
            with self.subTest(porta=porta), self.assertRaises(ValueError):
                self.configuracao(porta=porta)
        with self.assertRaises(ValueError):
            EmailRecuperacao(host='smtp.exemplo.com', remetente='nao-e-email')
        with self.assertRaises(ValueError):
            EmailRecuperacao(host='smtp.exemplo.com', remetente='acesso@exemplo.com', usuario='sem-senha')


if __name__ == '__main__':
    unittest.main()
