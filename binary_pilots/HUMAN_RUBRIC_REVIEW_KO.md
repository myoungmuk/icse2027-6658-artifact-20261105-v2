# Shi 계열의 사람 단계 — 아직 수행하지 않은 실제 검토

현재 실행은 draft-rubric ablation이다. 아래 절차와 기록이 완료되기 전에는
human-refined / golden rubric / human-in-the-loop 재현 완료라고 표시하지 않는다.
AI가 작성·재검토한 내용을 사람 평가자 기록으로 기재하지 않는다.

각 이슈의 입력은 `tasks.json`의 issue / gold_diff와
`run_v1/rubrics/tNNN.json`의 raw draft다. 후보 판정 결과와 공식 resolved 라벨을
가린 상태로 루브릭을 검토한다. 새 루브릭은 별도 버전에 저장한다.

1. 실제 개발자 1이 root cause와 각 요구사항을 확인한다. 정답 구현만 강제하는 문구,
   근거 없는 요구, 누락, 잘못된 해석을 수정하고 이유를 남긴다.
2. 실제 개발자 2가 수정과 근거를 독립적으로 확인하고 승인 또는 이견을 기록한다.
3. 두 사람의 신원 표기 또는 익명 평가자 코드, 전문성, 작업 시각, 이해충돌,
   draft 및 revised 루브릭 해시, 변경 근거, 최종 합의 상태를 기록한다.
4. 동결한 revised 루브릭으로 동일 후보를 새 run 버전에서 판정한다. 기존 draft 결과를
   덮어쓰지 않는다. 사람의 후보 patch label까지 확보하지 않았다면 LLM-human agreement는 계산하지 않는다.

검토 양식:

| 필드 | 작성 |
|---|---|
| instance_id / task_code | |
| reviewer_1 코드·전문성·시각 | |
| reviewer_2 코드·전문성·시각 | |
| draft SHA256 | |
| 항목별 원문 → 수정문 | |
| 수정 이유와 원문 근거 | |
| reviewer_2 확인·이견 | |
| 최종 합의 여부 | |
| revised rubric 경로·SHA256 | |

이 양식의 존재는 사람 검토 완료의 증거가 아니다. 현재 20개 이슈 모두 사람 검토 미완료다.
