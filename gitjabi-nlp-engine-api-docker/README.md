# Gitjabi NLP Engine Docker

깃잡의 NLP 분석 엔진이 포함된 컨테이너화 API입니다.

해당 엔진은 Azure Container Apps에 업로드 및 실테스트 되었습니다.  

## Test

`docker run --detach --name engine --publish 8000:80 gitjabi-engine`

## KEYBERT 모델

`KEYBERT_MODEL` 환경변수로 모델을 지정할 수 있다.

**snunlp/KR-SBERT-V40K-klueNLI-augSTS:**

서울대학교 KR-SBERT 모델.  

"keywords": [
    "소스",
    "코드",
    "배포",
    "이미지",
    "방식",
    "인증",
    "문제",
    "구름",
    "이름",
    "깔끔",
    "에러",
    "지정"
]

----

**paraphrase-multilingual-MiniLM-L12-v2:**

"keywords": [
    "이미지",
    "구름",
    "코드",
    "인증",
    "배포",
    "이름",
    "깔끔",
    "에러",
    "지정",
    "소스",
    "방식",
    "문제"
]

## ACA / ACR

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

