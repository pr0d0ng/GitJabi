# Azure Container Apps

[MS Doc](https://learn.microsoft.com/ko-kr/azure/developer/python/tutorial-containerize-simple-web-app?tabs=web-app-fastapi)

## Gitjabi NLP Engine Docker

PyTorch 기반과 KeyBERT, kiwi 형태소 분석기의 추출과 토크나이징을 
제공하는 간단한 API이다.

### 설정

1. 리소스 그룹에 ACA 인스턴스와 Azure Container Registry 생성
2. 로컬 NLP Engine 레포지터리에서 도커 이미지 빌드 후 ACR로 전송해야 한다.  

```sh
az login
az acr login --name {리소스명}
```  

```sh
docker build -t gitjabi-engine:v1 .

docker tag gitjabi-engine:v1 <ACR호스트명>.azurecr.io/gitjabi-engine:v1

docker push <ACR호스트명>.azurecr.io/gitjabi-engine:v1
```

3. ACA에서 Revision 및 Container 생성 후 배포한다.  
4. Network의 Ingress 세팅에서 포트 설정을 한다.

* Environment Variables 설정에서  
`KEYBERT_MODEL` 값 설정시 KEYBERT 모델을 지정할 수 있다. (변경시 재시작 하여야 함)
