# ICSE 2027 #6658 공개 자료 — 2026-11-05 v2

논문: **Beyond %Resolved:Reassessing SWE-bench Through Human and LLM Code Review**

- 저자 순서: Myeongmuk Kang, Geunseok Yang.
- ORCID: 강명묵 0009-0002-5351-0269, 양근석 0000-0001-5677-5129.
- `paper/main.pdf`: 본문 9쪽＋참고문헌 1쪽, 총 **10쪽**. 페이지 추가 없음.
- `historical_analysis/`: 과거 패킷·판정·분석 및 원래 파일 검증 목록.
- `binary_pilots/`: 핵심 선행연구 2편의 신규 적응 실험. 과거 결과와 분리해 보존.
- `submission_metadata.json`: 제목·저자·ORCID·PDF 해시·제출 준비 상태.

## 이번에 완료한 범위

Shi와 Cihan의 방법을 공통 Qwen2.5-Coder-7B binary judge 조건에 적응했다.
최초 20개와 서로 겹치지 않는 후속 20개 이슈, 총 80개 패치에서 240개 판정과
40개 draft rubric을 생성했다. 최초 strict parser의 형식 실패 37개는 원래 결과로
보존했고, 사후 fence 제거 분석을 별도로 기록했다. 후속 실행은 허용 형식을
미리 고정했으며 120개 판정이 모두 유효했다.

논문 Table IX는 후속 표본만 보고한다. Agent 기능 라벨 일치는 maintainer 14/20,
Cihan 13/20, Shi draft 15/20이다. 이 수치는 새 테스트 실행·사람 합의 라벨·전체
시스템 재현·방법 우열의 증거가 아니다. Shi에는 추가 reference 정보가 있으며,
실제 두 사람의 rubric refinement는 수행하지 않았다.

Shi의 정식 서지는 AI-SQE 2026, pp. 19–28, DOI 10.1145/3786175.3788348로
Crossref에서 확인했다. 실험 방법은 arXiv:2511.10865v1을 따랐다.
Cihan은 확인한 arXiv:2505.20206v1로 인용한다.

## 저장 응답으로 재분석

Python 표준 라이브러리만으로 새 추론 없이 실행한다. 출력은 저장소 밖의 새 폴더로 지정한다.

```bash
python tools/verify_manifest.py
python tools/reproduce_pilots.py --output ../icse6658-reanalysis
```

요약·CSV·분석 보고서 8개 파일의 SHA-256이 보존 결과와 일치하는지 확인한다.
과거 전체 분석의 별도 의존성과 실행법은 `historical_analysis/REPRODUCE.md`에 있다.
원래 frozen manifest의 서버 절대경로는 당시 기록이다. 다른 환경에서 새 GPU 추론을
수행하려면 모델·경로·실행 환경을 새 버전으로 설정해야 한다.

## 최종 제출에서 별도 확인할 사실

최신 비공개 author kit, 교신저자 지정, 출판사가 발급하는 권리·DOI 정보,
요구되는 출판사 PDF 검사 및 실제 학회 업로드는 이 GitHub 배포와 별도다.
과거 hosted 모델의 정확한 snapshot, 누락된 rubric 수정 이력, 독립 사람 검증은
자료만으로 복원할 수 없어 한계로 명시했다. 식별자나 검토 결과를 임의로 만들지 않았다.

제3자 자료의 권리는 원래 고지에 따른다. 혼합된 전체 자료에 새 blanket license를
부여하지 않았다. `historical_analysis/THIRD_PARTY_NOTICES.md`를 참고한다.
