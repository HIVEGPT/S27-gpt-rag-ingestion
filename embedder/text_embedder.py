import openai
import os
import re
import logging
from tenacity import retry, wait_random_exponential, stop_after_attempt  
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

def get_secret(secretName):
    keyVaultName = os.environ["AZURE_KEY_VAULT_NAME"]
    KVUri = f"https://{keyVaultName}.vault.azure.net"
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=KVUri, credential=credential)
    logging.info(f"Retrieving {secretName} secret from {keyVaultName}.")   
    retrieved_secret = client.get_secret(secretName)
    return retrieved_secret.value

class TextEmbedder():
    openai.api_type = "azure"    
    openai.api_key = get_secret('azureOpenAIKey')
    openai.api_base = f"https://{os.getenv('AZURE_OPENAI_SERVICE_NAME')}.openai.azure.com/"
    openai.api_version = os.getenv("AZURE_OPENAI_API_VERSION")
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")

    def clean_text(self, text, text_limit=7000):
        # Clean up text (e.g. line breaks, )    
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'[\n\r]+', ' ', text).strip()
        # Truncate text if necessary (e.g. for, ada-002, 4095 tokens ~ 7000 chracters)    
        if len(text) > text_limit:
            logging.warning("Token limit reached exceeded maximum length, truncating...")
            text = text[:text_limit]
        return text

    @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(6))
    def embed_content(self, text, clean_text=True, use_single_precision=True):
        import time
        embedding_precision = 9 if use_single_precision else 18
        if clean_text:
            text = self.clean_text(text)
        try:
            response = openai.Embedding.create(input=text, engine=self.AZURE_OPENAI_EMBEDDING_DEPLOYMENT)
        except Exception as e:
            wait = int(e.headers['Retry-After'])
            time.sleep(wait+1)
            response = openai.Embedding.create(input=text, engine=self.AZURE_OPENAI_EMBEDDING_DEPLOYMENT)

        embedding = [round(x, embedding_precision) for x in response['data'][0]['embedding']] # type: ignore
        return embedding