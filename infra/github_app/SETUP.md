# Github App 활용으로 Webhook 및 Check Run 사용

Check Run은 PR 단계에서 커스터마이징된 Check를 할 수 있도록 도와줌.

**참조 링크:**

* [Github Docs](https://docs.github.com/ko/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/about-status-checks)
* [Github REST API - Check Runs](https://docs.github.com/ko/rest/checks/runs?apiVersion=2022-11-28)

## Github App 생성 및 Organization 인스톨

1. 깃헙 App을 자체 생성하고, Organization에 설치까지 완료하여야 한다.
2. 사용할 기능에 따라 Permission을 적절히 선택한다.
   1. Contents  : Read Only
   2. Pull Request  : Read Only
   3. Checks  : Read & Write
3. Subscribe to Event는 Push, Pull Requests 등 사용할 이벤트를 선택한다.
4. Webhook 링크는 Webhook을 받을 API Gateway 혹은 애플리케이션 링크 지정하면 된다.
