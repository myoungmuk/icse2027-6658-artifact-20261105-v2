# 핵심 2편: 이번 실험의 재현 범위

| 조건 | ICSE 비교군 | Cihan 적응 | Shi 적응 |
|---|---|---|---|
| 공통 backbone | Qwen2.5-Coder-7B-Instruct, 불변 revision | 동일 | 동일 |
| 후보·이슈 | 같은 20개 이슈, Agentless/개발자 패치 각 20개 | 동일 | 동일 |
| 판정 출력 | ACCEPT/REJECT + 짧은 이유, JSON | 동일 | 동일 |
| 테스트 결과 안내 | 없음 | 없음 | 없음 |
| 추가 개발자 패치 정보 | 없음 | 없음 | **루브릭 생성에 사용** |
| 원 연구에서 남긴 핵심 | maintainer의 blocking 기준·11개 차원 | 기능·edge case·변경 필요 여부 | 버그별 루브릭 생성 후 후보 판정 |
| 변경 사항 | 거짓 pass 안내 제거, 공통 출력으로 축약 | 함수→diff, 수정 코드 생성 제외, YAML→공통 JSON | 미수정 draft ablation, 재구성한 프롬프트 |
| 원래 모델 | 기존 Qwen/DeepSeek/hosted와 다름 | GPT-4o/Gemini와 다름 | Gemini 2.5 Pro와 다름 |
| 이번에 수행하지 않은 것 | 독립 사람 mergeability 검증 | 수정 코드 실행·correction/regression 평가, 3회 반복 | **두 사람의 루브릭 수정·확인, 사람 합의 라벨** |

공통 조건은 **후보·이슈, 모델, 생성 설정, binary 출력·파싱·분모**다.
각 연구의 입력 정보량·판단 목표·추가 호출 수까지 동일하다는 뜻은 아니다.
특히 Shi에는 reference 정보가 있어, 이 비교로 “동일 정보에서 어느 시스템이 우월하다”는
주장을 해서는 안 된다. 사람 절차를 LLM 자체 검토로 대체하고 이를 사람 검토라고 부르지도 않는다.

기능적 공식 resolved 라벨과의 일치는 보조적인 판별 지표다. maintainer mergeability와
동일한 구성개념이 아니므로, 단순 정확도 순위로 ICSE 방법의 좋고 나쁨을 판단하지 않는다.
개발자 패치 승인율도 새로운 테스트 통과나 판단 정당성의 증거는 아니다.

원 논문 방법의 요약 근거:

- Shi: arXiv 2511.10865v1 §3.1–3.2, §6.1. Google sanitizer bug 도메인.
- Cihan: arXiv 2505.20206v1 §III-B–III-D, Figure 2. HumanEval 도메인.
- Cihan 실제 공개 프롬프트: Zenodo 14962566, `Replication Package/test-setup/prompt_templates/prompt_with_desc.toml`.
- 원문 내려받기·응답은 `sources/`에 별도 보존. 해당 preprint 페이지에는 proceedings 권·호·쪽수
  정보가 확인되지 않았다. 이번 실험으로 정식 출판 서지 검증까지 완료되는 것은 아니다.

논문 페이지 추가는 절대로 없다. 표·코드·원시 응답·사람 검토 양식은 논문과 별도 산출물이다.
