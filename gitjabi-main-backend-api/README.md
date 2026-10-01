# GitJabi - Backend API

GitJabi 백엔드 API이며, 아래와 같은 구조로 구동됩니다!
   
`Github (WebHook) or Clients <--> Azure API Management (Gateway) <--> Backend`  
  

## Start

0. VM 환경에서 초기 상태인 경우 `setup_infra.sh`를 시작하여 환경을 세팅합니다.
1. `.env`파일 내용을 완벽하게 작성합니다.  
2. `./secret` 폴더에 Github App에서 발급받은 유요한 액세스 키 파일(.pem)이 존재해야 합니다.

4. `source run_test.sh` 명령어로 테스트 모드로 API를 실행합니다.  
5. 프로덕션 모드(백그라운드 실행)는 `./run_prod.sh {start|stop|restart|status}` 명령어로 백그라운드로 켜고 끕니다.  
    ㅡ (권한 오류: `sudo chmod +x run_prod.sh`)  

