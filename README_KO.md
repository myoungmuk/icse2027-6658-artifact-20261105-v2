# ICSE 2027 #6658 공개 자료 — 2026-11-05 v7

논문: **Beyond %Resolved:Reassessing SWE-bench Through Human and LLM Code Review**

- 저자 순서: Myeongmuk Kang, Geunseok Yang.
- 교신저자: **Geunseok Yang(양근석)**, `gsyang@hknu.ac.kr` — 사용자 명시 확인.
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

최신 비공개 author kit, 출판사가 발급하는 권리·DOI 정보,
요구되는 출판사 PDF 검사 및 실제 학회 업로드는 이 GitHub 배포와 별도다.
과거 hosted 모델의 정확한 snapshot, 누락된 rubric 수정 이력, 독립 사람 검증은
자료만으로 복원할 수 없어 한계로 명시했다. 식별자나 검토 결과를 임의로 만들지 않았다.

제3자 자료의 권리는 원래 고지에 따른다. 혼합된 전체 자료에 새 blanket license를
부여하지 않았다. `historical_analysis/THIRD_PARTY_NOTICES.md`를 참고한다.

## v5에서 확인한 사실·서지 (보존 기록)

기존 인간 파일럿의 평가자는 강명묵이며 연구에 참여했다는 사용자 확인을 유지한다.
리뷰 경력·루브릭 개발의 정확한 역할은 미기록이다. 새 인간 검토·추론·실험 수치는 추가하지 않았다.

인용된 정식 출판 논문 26편의 쪽수를 확인했다. 정확한 DOI 23건과 공식 ICLR proceedings 3건을 근거로 한다.
v5에서 추가 8편을 보강했다. Agentless는 제목이 변경된 2025 정식 출판본으로,
OpenHands·SWE-bench Multimodal은 ICLR 2025, LLaMA-Reviewer는 ISSRE 2023으로 인용했다.
Cihan과 Qwen technical report 2편은 preprint로 유지하고 웹 자료 2건과 구분한다.
기존 HTTP 429 두 건의 보존 응답 재사용 사실도 유지한다. 세부 출처는 `bibliography/`에 있다.
논문은 본문 9쪽＋참고문헌 1쪽, 총 10쪽이다. 실제 학회 업로드 완료를 뜻하지 않는다.

## v6 추가 설명

조건명 Adjusted, 14B의 예시 역할, rationale·병합후 추적 미실시, 적용판단 예시와 결과순서를 보완했다. 기존 저장응답의 동일과제 pair 사후분석과 고정선택 rationale 예시2건을 추가했다. 과거 원시판정·수치입력은 유지했고 새 추론·사람평가는 없다. 총10쪽이며 실제 최종 학회 업로드는 미실시다.

## v7 기술적 거절 사유 점검과 제출 대조

agent·gold·실패 패치에서 각2건을 사전순으로 골라 당시 base commit의 코드와 대조했다.
선택한 국소 주장5건은 근거가 있었고 django-11179의 일반삭제 PK 미정리 주장은 기존
정리 코드와 모순됐다. 전체 프로젝트 테스트·독립 인간 adjudication·정확도 추정은 아니다.
원본 코드·patch 적용 결과·probe 입력/바인딩·결과·해시·해당 commit의 라이선스를 보존했다.

새 제출 대조 도구 tools/verify_submission.py는 이 체크아웃의 최신 metadata/PDF를
기본으로 사용한다. PDF metadata 제목과 실제 첫 페이지 제목을 별도로 확인한다.
기존 v5 고정 경로를 쓰는 과거 도구 대신 새 도구를 사용한다. 실제 포털 접속·업로드는 하지 않는다.
