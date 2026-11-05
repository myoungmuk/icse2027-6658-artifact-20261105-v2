# ICSE 핵심 선행연구 2편: 신규 binary judge 예비 비교

20개 이슈, 40개 패치, 3가지 프롬프트 방식으로 새 추론을 실행했다.
원 논문의 전체 시스템 재현이 아니라 Qwen2.5-Coder-7B-Instruct를 고정한 **적응 실험**이다.
기존 ICSE 결과를 재집계한 수치가 아니다. 최초 프로토콜·선택·프롬프트는 새 판정 전에 해시로 고정했다.

| 방식 | Agent 기능 라벨 일치 | 해결 패치 승인 | 미해결 패치 거절 | 개발자 패치 승인 | 실패 |
|---|---:|---:|---:|---:|---:|
| icse_test_blind | 14/20 | 7/10 | 7/10 | 9/20 | 0 |
| cihan_binary_diff | 13/20 | 6/10 | 7/10 | 8/20 | 0 |
| shi_draft_rubric | 15/20 | 9/10 | 6/10 | 11/20 | 0 |

## 이 표가 측정하는 것

Agent 기능 라벨 일치는 공식 Agentless 결과(해결 10개/미해결 10개)와 새 판정의 일치다.
새로운 테스트 실행이나 사람의 mergeability 라벨은 아니다. 개발자 패치 20개는 별도 승인율로
표시했으며, 새로 테스트한 정답으로 간주해 정확도에 합치지 않았다. 실패는 거절로 바꾸지 않는다.
표의 각 승인·거절 분모는 유효 응답 수다. 계획 분모와 Wilson 95% 구간은 summary.json에 있다.

## 두 연구를 반영한 범위

- Cihan: 공개 Zenodo 패키지의 설명 포함 프롬프트에서 기능·edge case·변경 필요성 판단을
  가져왔다. HumanEval 함수 대신 저장소 diff를 넣고, 코드 수정 생성은 제외하고 binary JSON으로
  통일했다. 원 논문의 GPT-4o/Gemini 결과나 correction/regression 측정 재현은 아니다.
- Shi: 이슈와 개발자 패치로 버그별 draft rubric을 생성하고 판정에 사용했다. 원 논문 §6.1의
  **미수정 루브릭 ablation을 적응**했다. 두 사람의 수정·확인, golden rubric, 사람 합의
  라벨은 아직 없다. 따라서 완전한 human-in-the-loop 시스템 실험 완료라고 쓰면 안 된다.
- ICSE 비교군: 기존 calibrated maintainer 프롬프트를 test-blind 조건으로 적응했다.
  과거의 잘못된 ‘테스트 통과’ 안내를 새 실행에서 제거했다. 기존 instrument와 동일하다고
  주장하지 않는다.

## 해석 한계

Shi 방식은 루브릭 생성에 개발자 정답 패치를 보는 추가 정보와 호출 비용이 있다. 다른 두 방식은
이 정답 패치를 보지 않는다. 공통 모델·후보·binary 출력 조건을 맞췄으나 정보량까지 같은 비교는
아니다. 특히 개발자 패치 승인율은 reference bias가 있다. 이 20개 이슈의 결과로 전체 시스템의
우열이나 사람 리뷰 일치도를 결론낼 수 없다. 단일 모델·한 번의 greedy generation이고, 길이
제한으로 제외한 이슈와 표본 저장소 구성이 있다. 공식 기능 라벨도 mergeability truth가 아니다.

## 논문 분량 제약

사용자 명시 지시: **논문 페이지 추가는 절대로 없다.** 기존 9쪽 본문+1쪽 참고문헌 PDF는
변경하지 않았다. 본 실험의 보고서는 별도 산출물이며, 본문 반영 시 기존 분량 안에서 문장·표를
교체해야 한다. 아직 카메라레디 원본이나 기존 ZIP을 덮어쓰지 않았다.

## 재현 및 후속 작업

원문·공개 패키지: sources/. 사전 프로토콜: protocol_v1.md. 고정 해시: freeze_manifest.json.
표본·제외: tasks.json / selection_audit.json. 모든 실제 프롬프트·응답: run_v1/raw/,
run_v1/rubrics/. 설정·패키지: run_v1/environment.json. 전체 120개 판정: analysis_v1/verdicts.csv.
사람의 루브릭 검토를 위한 별도 양식은 HUMAN_RUBRIC_REVIEW_KO.md에 있다.
GPU 작업의 종료·반납 확인은 gpu_execution_record.json을 확인한다.
