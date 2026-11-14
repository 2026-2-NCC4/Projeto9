"""Envio de códigos de recuperação por SMTP com conexão TLS verificada."""

from dataclasses import dataclass, field
from email.message import EmailMessage
import smtplib
import ssl

from auth_usuarios import VALIDADE_RECUPERACAO_SEGUNDOS, normalizar_email


class ErroEnvioEmail(RuntimeError):
    """Não foi possível entregar a mensagem de recuperação."""


@dataclass(frozen=True)
class EmailRecuperacao:
    host: str
    remetente: str
    usuario: str = ""
    senha: str = field(default="", repr=False)
    porta: int = 587
    ssl_implicito: bool = False

    def __post_init__(self):
        if not self.host.strip() or not 1 <= self.porta <= 65535:
            raise ValueError("Configure um servidor SMTP e uma porta válida.")
        normalizar_email(self.remetente)
        if bool(self.usuario) != bool(self.senha):
            raise ValueError("Informe o usuário e a senha SMTP juntos.")

    def enviar_codigo(self, destinatario: str, codigo: str) -> None:
        mensagem = EmailMessage()
        mensagem["Subject"] = "DashBird | Recuperação de senha"
        mensagem["From"] = normalizar_email(self.remetente)
        mensagem["To"] = normalizar_email(destinatario)
        minutos = VALIDADE_RECUPERACAO_SEGUNDOS // 60
        mensagem.set_content(
            "Recebemos uma solicitação para redefinir a senha da sua conta DashBird.\n\n"
            f"Seu código de recuperação é:\n{codigo}\n\n"
            "Volte à plataforma, abra 'Esqueci minha senha' e informe o e-mail, "
            "o código completo e sua nova senha.\n"
            f"O código vale por {minutos} minutos e só pode ser usado uma vez.\n\n"
            "Se você não solicitou esta alteração, ignore esta mensagem. "
            "Sua senha continua a mesma. Não compartilhe este código.\n"
        )
        contexto = ssl.create_default_context()
        cliente = smtplib.SMTP_SSL if self.ssl_implicito else smtplib.SMTP
        opcoes = {"timeout": 10}
        if self.ssl_implicito:
            opcoes["context"] = contexto
        try:
            with cliente(self.host, self.porta, **opcoes) as servidor:
                if not self.ssl_implicito:
                    servidor.starttls(context=contexto)
                if self.usuario:
                    servidor.login(self.usuario, self.senha)
                recusados = servidor.send_message(mensagem)
                if recusados:
                    raise ErroEnvioEmail("O servidor recusou o destinatário.")
        except (OSError, smtplib.SMTPException) as erro:
            raise ErroEnvioEmail("Não foi possível enviar o e-mail de recuperação.") from erro
