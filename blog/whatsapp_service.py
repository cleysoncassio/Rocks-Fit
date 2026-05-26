import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class EvolutionApiService:
    @staticmethod
    def _get_headers():
        api_key = getattr(settings, 'EVOLUTION_API_KEY', '')
        return {
            'apikey': api_key,
            'Content-Type': 'application/json'
        }
        
    @staticmethod
    def _get_base_url():
        base_url = getattr(settings, 'EVOLUTION_API_URL', 'http://localhost:8080')
        instance = getattr(settings, 'EVOLUTION_INSTANCE_NAME', 'RocksFit')
        return f"{base_url.rstrip('/')}/message/sendText/{instance}"

    @staticmethod
    def enviar_mensagem_texto(numero: str, texto: str):
        """
        Envia uma mensagem de texto simples pelo WhatsApp usando a Evolution API.
        """
        url = EvolutionApiService._get_base_url()
        headers = EvolutionApiService._get_headers()
        
        # A Evolution API espera que o número tenha formato DDI+DDD+Numero (ex: 5584999999999)
        numero_limpo = ''.join(filter(str.isdigit, str(numero)))
        
        payload = {
            "number": numero_limpo,
            "options": {
                "delay": 1200,
                "presence": "composing",
                "linkPreview": False
            },
            "textMessage": {
                "text": texto
            }
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            logger.info(f"Mensagem enviada com sucesso para {numero_limpo}")
            return True, response.json()
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem para {numero_limpo}: {str(e)}")
            return False, str(e)

    @staticmethod
    def enviar_pix_copia_e_cola(numero: str, chave_pix: str):
        """
        Envia a chave PIX copia e cola.
        """
        url = EvolutionApiService._get_base_url()
        headers = EvolutionApiService._get_headers()
        numero_limpo = ''.join(filter(str.isdigit, str(numero)))
        
        # Primeiro, enviamos um aviso
        EvolutionApiService.enviar_mensagem_texto(
            numero, 
            "Segue abaixo a chave PIX Copia e Cola. Basta copiar a mensagem inteira a seguir e colar na área PIX do seu banco:"
        )
        
        # Depois enviamos apenas a chave limpa para facilitar a cópia
        payload = {
            "number": numero_limpo,
            "options": {
                "delay": 2000,
                "presence": "composing"
            },
            "textMessage": {
                "text": chave_pix
            }
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            logger.info(f"PIX enviado com sucesso para {numero_limpo}")
            return True, response.json()
        except Exception as e:
            logger.error(f"Erro ao enviar PIX para {numero_limpo}: {str(e)}")
            return False, str(e)
