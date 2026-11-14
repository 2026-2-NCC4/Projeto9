"""Testes unitários sem Streamlit ou banco externo."""

from pathlib import Path
import sys
import tempfile
import unittest

FRONTEND = Path(__file__).resolve().parents[2] / 'Frontend'
if str(FRONTEND) not in sys.path:
    sys.path.insert(0, str(FRONTEND))

from auth_usuarios import (
    BancoUsuarios,
    EmailJaCadastrado,
    ErroCadastro,
    ErroBancoUsuarios,
    conferir_senha,
    gerar_hash_senha,
    normalizar_email,
)


class TesteCadastro(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.banco = BancoUsuarios(sqlite_path=Path(self.tempdir.name) / 'sub' / 'usuarios.sqlite3')

    def tearDown(self):
        self.tempdir.cleanup()

    def test_cadastrar_e_autenticar(self):
        conta = self.banco.cadastrar('Ana  Maria', ' ANA@EXEMPLO.COM ', 'SenhaSegura2026')
        self.assertEqual({chave: conta[chave] for chave in ('nome', 'email')},
                         {'nome': 'Ana Maria', 'email': 'ana@exemplo.com'})
        self.assertEqual(len(conta['chave_recuperacao']), 43)
        self.assertEqual(self.banco.autenticar('ANA@EXEMPLO.COM', 'SenhaSegura2026'),
                         {'nome': 'Ana Maria', 'email': 'ana@exemplo.com'})
        self.assertIsNone(self.banco.autenticar('ana@exemplo.com', 'senhaerrada123'))

    def test_conta_persiste_em_outra_instancia(self):
        self.banco.cadastrar('Carlos Vieira', 'c@exemplo.com', 'SegredoFort3')
        novo = BancoUsuarios(sqlite_path=self.banco.sqlite_path)
        self.assertEqual(novo.autenticar('c@exemplo.com', 'SegredoFort3')['nome'], 'Carlos Vieira')

    def test_email_duplicado_case_insensitive(self):
        self.banco.cadastrar('Ana Maria', 'ana@exemplo.com', 'SenhaSegura2026')
        with self.assertRaises(EmailJaCadastrado):
            self.banco.cadastrar('Outra Ana', 'ANA@EXEMPLO.COM', 'OutraSenha2026')

    def test_senha_nao_gravada_em_texto_puro(self):
        self.banco.cadastrar('Ana Maria', 'ana@exemplo.com', 'SenhaSegura2026')
        dados = self.banco.sqlite_path.read_bytes()
        self.assertNotIn(b'SenhaSegura2026', dados)
        self.assertIn(b'pbkdf2_sha256', dados)

    def test_nome_curto(self):
        with self.assertRaises(ErroCadastro):
            self.banco.cadastrar('A', 'a@exemplo.com', 'SenhaSegura2026')

    def test_email_invalido(self):
        with self.assertRaises(ErroCadastro):
            self.banco.cadastrar('Nome Completo', 'email-invalido', 'SenhaSegura2026')

    def test_senha_curta(self):
        with self.assertRaises(ErroCadastro):
            self.banco.cadastrar('Nome Completo', 'teste@exemplo.com', 'Abc123')

    def test_senha_sem_numero(self):
        with self.assertRaises(ErroCadastro):
            self.banco.cadastrar('Nome Completo', 'teste@exemplo.com', 'SenhaLongaSemNumero')

    def test_hash_aleatorio(self):
        primeiro = gerar_hash_senha('SenhaSegura2026')
        segundo = gerar_hash_senha('SenhaSegura2026')
        self.assertNotEqual(primeiro, segundo)
        self.assertTrue(conferir_senha('SenhaSegura2026', primeiro))
        self.assertFalse(conferir_senha('SenhaErrada2026', primeiro))

    def test_hash_malformado(self):
        self.assertFalse(conferir_senha('SenhaSegura2026', 'senha-pura'))
        self.assertFalse(conferir_senha('SenhaSegura2026', 'pbkdf2_sha256$999999999$abc$abc'))

    def test_banco_rejeita_url_inadequada(self):
        with self.assertRaises(ErroBancoUsuarios):
            BancoUsuarios(database_url='sqlite:///tmp/test.db')

    def test_nao_exige_banco_para_login_invalido(self):
        self.assertIsNone(self.banco.autenticar('sem-email', 'Senh4Longa'))

    def test_email_com_espacos(self):
        self.assertEqual(normalizar_email('  EU@EXEMPLO.COM  '), 'eu@exemplo.com')


if __name__ == '__main__':
    unittest.main()
