# Databricks

## 세팅 과정

1. Azure Databricks - Premium 플랜 생성
2. Azure Access Connector를 생성한다.
   AAC는 Azure Data Lake Storage Gen2를 연결해주는 용도이며,
   Azure KeyVault 또한 연결 가능하다.
3. Workspace에서 작업을 시작한다.

## KeyVault 사용 예시

Azure KeyVault에서 시크릿 값을 가져오는 것은 아래 예제 코드를 활용.

```python
from azure.keyvault.secrets import SecretClient 

credential = dbutils.credentials.getServiceCredentialsProvider(
  '2dtfin-gitjabi-access-conector-credential'
)
vault_url = "https://gitjabi-keyvault.vault.azure.net/"
secret_client = SecretClient(vault_url=vault_url, credential=credential)


GITHUB_TOKEN = secret_client.get_secret("github-token").value.strip()
```
