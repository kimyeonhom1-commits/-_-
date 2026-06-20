# OpenClaw Python Workspace

Discord의 OpenClaw agent가 코드 생성, 수정, 실행 및 데이터 분석에 사용하는 전용 작업 폴더입니다.

> 이 공개 저장소에는 소스와 설정 예시만 포함합니다. Discord 토큰, `.env`,
> OpenClaw secrets, 로그, 모델, 원본 데이터와 실행 결과는 포함하지 않습니다.

## Python

```bash
source .venv/bin/activate
python --version
```

주요 용도:

- 포인트클라우드 처리 및 시각화
- 머신러닝 및 딥러닝
- 데이터 분석과 노트북
- Python 코드 생성, 정리, 테스트

원본 데이터는 호스트의 `~/data_raw`에 둘 수 있습니다. 실행 격리 환경에서는 `/data_raw`로 읽기 전용 마운트됩니다.

## Discord 관제 명령

- `/status`: OpenClaw 기본 상태, uptime, 현재 모델
- `/model`: 현재 모델 확인 및 모델 선택
- `/gpu`: GPU 사용률, 온도, VRAM
- `/disk`: 디스크 사용량
- `/mem`: RAM/Swap 사용량
- `/log`: 최근 OpenClaw/실험 로그 요약
- `/report`: 최근 24시간 관제 보고
- `/top5`: `experiments/leaderboard.csv` 최고 성능 5개
- `/failed`: 최근 실패 실행/로그 5개

관제 수집기는 고정된 읽기 전용 명령만 실행합니다. 임의 셸 인자를 받지 않으며,
`data_raw`는 샌드박스 안에서 `/data_raw`로 읽기 전용 마운트됩니다.

## 자동 보고

- 매일 09:00 (Asia/Seoul): 시스템 상태 보고
- 매일 23:00 (Asia/Seoul): 최근 24시간 실험/시스템 보고
- 전달 채널: 현재 Discord `#일반` 채널

기본 모델은 `ollama/qwen3:8b`입니다. 복잡한 로그 분석을 시도할 때는 Discord의
`/model`에서 `ollama/deepseek-r1:14b`를 선택할 수 있으며, 새 세션으로 돌아오면
기본 모델은 다시 `qwen3:8b`를 사용합니다.

## 구성 파일

- `scripts/research_control.py`: 읽기 전용 시스템·실험 상태 수집기
- `control-plugin/`: 모델을 거치지 않는 고정 Discord 슬래시 명령 플러그인
- `environment.yml`: 포인트클라우드·ML·DL 연구용 Python 환경 예시

기본 작업공간은 `~/openclaw-workspace`입니다. 다른 위치를 사용하려면 Gateway
환경에 `OPENCLAW_RESEARCH_WORKSPACE`를 설정합니다. 격리 실행기의 위치를 바꿀
때는 `OPENCLAW_WORKSPACE_RUNNER`를 설정합니다.
