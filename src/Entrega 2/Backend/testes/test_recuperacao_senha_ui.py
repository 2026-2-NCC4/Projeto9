"""Fluxo Streamlit de recuperação com contas temporárias e envio simulado."""

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

FRONTEND = Path(__file__).resolve().parents[2] / 'Frontend'
if str(FRONTEND) not in sys.path:
    sys.path.insert(0, str(FRONTEND))

from auth_usuarios import BancoUsuarios
from email_recuperacao import ErroEnvioEmail


class TesteRecuperacaoSenhaUI(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / 'usuarios.sqlite3'
        variaveis = {chave: '' for chave in (
            'CTI_DATABASE_URL', 'CTI_USER', 'CTI_PASSWORD', 'CTI_SMTP_HOST',
            'CTI_SMTP_FROM', 'CTI_SMTP_PORT', 'CTI_SMTP_USER',
            'CTI_SMTP_PASSWORD', 'CTI_SMTP_SSL',
        )}
        variaveis.update(CTI_USERS_DB_PATH=str(self.db_path), CTI_ENABLE_DEMO='false')
        self.ambiente = patch.dict(os.environ, variaveis)
        self.ambiente.start()
        self.addCleanup(self.ambiente.stop)
        self.addCleanup(self.tempdir.cleanup)
        self.banco = BancoUsuarios(sqlite_path=self.db_path)
        conta = self.banco.cadastrar('Ana Maria', 'ana@exemplo.com', 'SenhaSegura2026')
        self.chave = conta['chave_recuperacao']

    def abrir(self, smtp=False):
        app = AppTest.from_file(str(FRONTEND / 'app.py'), default_timeout=30)
        app.secrets['auth'] = {'allow_signup': True, 'allow_demo': False}
        app.secrets['smtp'] = {
            'host': 'smtp.exemplo.com', 'port': 587,
            'from_email': 'acesso@exemplo.com',
        } if smtp else {}
        app.run()
        self.sem_excecoes(app)
        return app

    def sem_excecoes(self, app):
        self.assertEqual(len(app.exception), 0, [erro.message for erro in app.exception])

    def campo(self, app, rotulo):
        return next(campo for campo in app.text_input if campo.label == rotulo)

    def botao(self, app, rotulo):
        return next(botao for botao in app.button if botao.label == rotulo)

    def preencher_troca(self, app, codigo, confirmacao='NovaSenhaSegura2027'):
        rotulo_chave = ('Chave de recuperação' if any(campo.label == 'Chave de recuperação' for campo in app.text_input)
                        else 'Código ou chave de recuperação')
        for rotulo, valor in (
            ('E-mail da conta', 'ana@exemplo.com'),
            (rotulo_chave, codigo),
            ('Nova senha', 'NovaSenhaSegura2027'),
            ('Confirmar nova senha', confirmacao),
        ):
            self.campo(app, rotulo).set_value(valor)

    def guardar_chave(self, app, autenticado=False):
        chave = app.code[0].value
        rotulo = 'Continuar para a plataforma' if autenticado else 'Voltar para entrar'
        self.assertTrue(self.botao(app, rotulo).disabled)
        app.checkbox[0].check().run()
        self.botao(app, rotulo).click().run()
        self.sem_excecoes(app)
        self.assertEqual(len(app.code), 0)
        return chave

    @patch('email_recuperacao.EmailRecuperacao.enviar_codigo')
    def test_sem_smtp_recupera_por_chave_sem_enviar_email(self, enviar):
        app = self.abrir()
        self.assertNotIn('Enviar código de recuperação', [botao.label for botao in app.button])
        self.assertFalse(self.botao(app, 'Redefinir senha').disabled)
        self.preencher_troca(app, self.chave)
        self.botao(app, 'Redefinir senha').click().run()
        self.sem_excecoes(app)
        self.assertIn('Senha redefinida com sucesso', app.success[0].value)
        nova_chave = self.guardar_chave(app)
        self.assertNotEqual(nova_chave, self.chave)
        enviar.assert_not_called()

    def test_smtp_invalido_nao_interrompe_login(self):
        with patch.dict(os.environ, CTI_SMTP_PORT='porta-invalida'):
            app = self.abrir(smtp=True)
        self.assertNotIn('Enviar código de recuperação', [botao.label for botao in app.button])
        self.assertFalse(self.botao(app, 'Entrar na plataforma').disabled)

    @patch('email_recuperacao.EmailRecuperacao.enviar_codigo')
    def test_resposta_igual_para_email_cadastrado_e_desconhecido(self, enviar):
        app = self.abrir(smtp=True)
        self.campo(app, 'E-mail cadastrado').set_value('ANA@EXEMPLO.COM')
        self.botao(app, 'Enviar código de recuperação').click().run()
        self.sem_excecoes(app)
        enviar.assert_called_once()
        self.assertEqual(enviar.call_args.args[0], 'ana@exemplo.com')
        resposta = app.success[0].value
        self.campo(app, 'E-mail cadastrado').set_value('desconhecido@exemplo.com')
        self.botao(app, 'Enviar código de recuperação').click().run()
        self.sem_excecoes(app)
        self.assertEqual(app.success[0].value, resposta)
        self.assertEqual(enviar.call_count, 1)

    @patch('email_recuperacao.EmailRecuperacao.enviar_codigo', side_effect=ErroEnvioEmail)
    def test_falha_de_envio_nao_revela_se_email_existe(self, enviar):
        app = self.abrir(smtp=True)
        self.campo(app, 'E-mail cadastrado').set_value('ana@exemplo.com')
        self.botao(app, 'Enviar código de recuperação').click().run()
        self.sem_excecoes(app)
        resposta = app.success[0].value
        self.campo(app, 'E-mail cadastrado').set_value('desconhecido@exemplo.com')
        self.botao(app, 'Enviar código de recuperação').click().run()
        self.assertEqual(app.success[0].value, resposta)
        self.assertEqual(enviar.call_count, 1)

    def test_confirmacao_diferente_nao_troca_senha(self):
        app = self.abrir()
        self.preencher_troca(app, 'A' * 43, confirmacao='SenhaDiferente2027')
        self.botao(app, 'Redefinir senha').click().run()
        self.sem_excecoes(app)
        self.assertEqual(app.error[0].value, 'As senhas não coincidem.')
        self.assertIsNotNone(self.banco.autenticar('ana@exemplo.com', 'SenhaSegura2026'))

    def test_redefinicao_exige_novo_login_e_libera_tentativas(self):
        app = self.abrir()
        app.session_state['cti_autenticado'] = False
        app.session_state['cti_tentativas_login'] = 8
        self.preencher_troca(app, self.chave)
        self.botao(app, 'Redefinir senha').click().run()
        self.sem_excecoes(app)
        self.assertIn('Senha redefinida com sucesso', app.success[0].value)
        self.assertFalse(app.session_state['cti_autenticado'])
        self.assertEqual(app.session_state['cti_tentativas_login'], 0)
        self.guardar_chave(app)
        self.campo(app, 'Usuário ou e-mail').set_value('ana@exemplo.com')
        self.campo(app, 'Senha').set_value('SenhaSegura2026')
        self.botao(app, 'Entrar na plataforma').click().run()
        self.assertEqual(app.error[0].value, 'Usuário/e-mail ou senha inválidos.')
        self.campo(app, 'Senha').set_value('NovaSenhaSegura2027')
        self.botao(app, 'Entrar na plataforma').click().run()
        self.sem_excecoes(app)
        self.assertTrue(app.session_state['cti_autenticado'])

    def test_cadastro_exibe_chave_ate_usuario_guardar(self):
        app = self.abrir()
        for rotulo, valor in (
            ('Nome completo', 'Bruno Silva'), ('E-mail', 'bruno@exemplo.com'),
            ('Criar senha', 'SenhaSegura2026'), ('Confirmar senha', 'SenhaSegura2026'),
        ):
            self.campo(app, rotulo).set_value(valor)
        self.botao(app, 'Criar minha conta').click().run()
        self.sem_excecoes(app)
        chave = app.code[0].value
        app.run()
        self.assertEqual(app.code[0].value, chave)
        self.assertEqual(self.guardar_chave(app, autenticado=True), chave)
        self.banco.redefinir_senha('bruno@exemplo.com', chave, 'NovaSenha2027')

    def test_conta_existente_pode_gerar_chave_confirmando_senha(self):
        app = self.abrir()
        self.campo(app, 'Usuário ou e-mail').set_value('ana@exemplo.com')
        self.campo(app, 'Senha').set_value('SenhaSegura2026')
        self.botao(app, 'Entrar na plataforma').click().run()
        self.sem_excecoes(app)
        self.campo(app, 'Senha atual').set_value('SenhaErrada2026')
        self.botao(app, 'Gerar nova chave de recuperação').click().run()
        self.sem_excecoes(app)
        self.assertEqual(app.error[0].value, 'E-mail ou senha atual inválidos.')
        self.assertEqual(len(app.code), 0)
        self.campo(app, 'Senha atual').set_value('SenhaSegura2026')
        self.botao(app, 'Gerar nova chave de recuperação').click().run()
        self.sem_excecoes(app)
        nova_chave = self.guardar_chave(app, autenticado=True)
        self.assertNotEqual(nova_chave, self.chave)
        self.banco.redefinir_senha('ana@exemplo.com', nova_chave, 'NovaSenha2027')

    def test_chave_invalida_nao_expoe_nova_chave(self):
        app = self.abrir()
        self.preencher_troca(app, 'A' * 43)
        self.botao(app, 'Redefinir senha').click().run()
        self.sem_excecoes(app)
        self.assertIn('inválido', app.error[0].value)
        self.assertEqual(len(app.code), 0)
        self.assertEqual(len(app.success), 0)

    def test_sair_e_entrar_em_demo_nao_herda_seguranca_da_conta(self):
        app = self.abrir()
        self.campo(app, 'Usuário ou e-mail').set_value('ana@exemplo.com')
        self.campo(app, 'Senha').set_value('SenhaSegura2026')
        self.botao(app, 'Entrar na plataforma').click().run()
        self.botao(app, 'Sair da plataforma').click().run()
        app.secrets['auth']['allow_demo'] = True
        app.run()
        self.botao(app, 'Acessar demonstração').click().run()
        self.sem_excecoes(app)
        self.assertNotIn('Senha atual', [campo.label for campo in app.text_input])
        self.assertEqual(app.session_state['cti_usuario_email'], '')


if __name__ == '__main__':
    unittest.main()
