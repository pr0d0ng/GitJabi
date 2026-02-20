# Shared Test

## 사용법

```sh
uv sync
```

## generate_dummy_webhook.py

LLM을 활용해 GitHub Pull Request Webhook 이벤트 더미 데이터를 자동 생성하는 도구입니다.

보안 엔진 테스트, PR 위반 탐지 실험, ML 학습 데이터 생성 등에 사용할 수 있습니다.

```sh
uv run python -m pr_dummy.main

uv run python -m pr_dummy.main --count 50
```
