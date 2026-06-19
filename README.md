# 로컬 통계 대시보드

TLS와 RF postprocess 결과를 비교하는 Streamlit 기반 통계 대시보드입니다.

GitHub Pages용 정적 대시보드는 아래 주소에서 볼 수 있습니다.

```text
https://kimyeonhom1-commits.github.io/-_-/
```

이 저장소에는 앱 코드와 정적 대시보드 HTML만 포함합니다. 원본 CSV는 공개 저장소에 올리지 않으며,
로컬 실행 또는 정적 대시보드 재생성 시 `data/` 폴더에 직접 넣어 사용합니다.

설치:

```bash
pip install -r requirements.txt
```

실행:

```bash
streamlit run app.py
```

Windows:

```text
run_windows.bat
```

브라우저:

```text
http://localhost:8501
```

필요한 로컬 데이터 파일:

```text
data/RF_단계별_지표.csv
data/tls_결과차.csv
data/runtime_metrics.csv
```

`runtime_metrics.csv`는 런타임 분석 탭에서만 사용합니다.

정적 대시보드 재생성:

```bash
python scripts/build_static_dashboard.py
```
