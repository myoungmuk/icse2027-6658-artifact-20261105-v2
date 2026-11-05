# 추가 문헌 검토 (2026-09-08)

## 범위와 중복 확인

- 대상 원고: `review_swe/paper/main.tex`, `paper_ko/main_ko.tex`, `references.bib`.
- 목적: 원고의 핵심인 **LLM 리뷰 판정의 측정 타당성·편향**을 보강할 수 있는 문헌만 제안한다.
- 아래 2편은 현재 `references.bib` 및 영문·국문 원고에서 제목 검색 결과가 없었다. 전체 감사 범위의 다른 3편과 합쳐 **신규 고유 문헌 5편**이다.
- 원고나 BibTeX에는 삽입하지 않았다.

## 1. Chen et al. (2024): 다양한 판정 편향

**서지정보.** Guiming Hardy Chen, Shunian Chen, Ziche Liu, Feng Jiang, and Benyou Wang, “Humans or LLMs as the Judge? A Study on Judgement Bias,” *Proceedings of EMNLP 2024*, pp. 8301–8327, 2024. DOI: [10.18653/v1/2024.emnlp-main.474](https://doi.org/10.18653/v1/2024.emnlp-main.474). [ACL Anthology 원문·메타데이터](https://aclanthology.org/2024.emnlp-main.474/)

**확인 깊이.** ACL Anthology의 출판 메타데이터와 초록 확인(초록 수준; 본문 전체를 읽었다고 주장하지 않음).

**정확히 지지하는 주장.** 저자들은 정답 주석을 참조하지 않는 교란 프레임워크로 misinformation oversight, gender, authority, beauty bias를 조사했고, 인간과 LLM 판정자 모두 교란에 취약하며 최신 판정자에도 상당한 편향이 남는다고 보고한다. 따라서 “LLM 판정 결과는 판정자 자체의 취약성과 편향을 검증하지 않은 채 객관적 품질 척도로 취급할 수 없다”는 일반적 측정 주장을 지지한다.

**적용 한계.** 일반 지식·응답 평가 설정이며 코드 패치 병합 가능성이나 SWE-bench를 직접 평가하지 않는다. 이 논문만으로 본 원고의 false-rejection 수치, 판정자 간 불일치, gold-positive-control 보정 효과를 뒷받침해서는 안 된다.

## 2. Shi et al. (2025): 위치 편향과 반복 안정성

**서지정보.** Lin Shi, Chiyu Ma, Wenhua Liang, Xingjian Diao, Weicheng Ma, and Soroush Vosoughi, “Judging the Judges: A Systematic Study of Position Bias in LLM-as-a-Judge,” *Proceedings of IJCNLP-AACL 2025*, pp. 292–314, 2025. DOI: [10.18653/v1/2025.ijcnlp-long.18](https://doi.org/10.18653/v1/2025.ijcnlp-long.18). [ACL Anthology 원문·메타데이터](https://aclanthology.org/2025.ijcnlp-long.18/)

**확인 깊이.** ACL Anthology의 출판 메타데이터와 초록 확인(초록 수준).

**정확히 지지하는 주장.** 15개 LLM 판정자, MTBench·DevBench의 22개 과제, 약 15만 회 평가에서 위치 편향이 우연으로 설명되지 않고 판정자·후보·과제 요인에 따라 달라진다고 보고한다. 반복 안정성, 위치 일관성, 선호 공정성을 분리 측정한다는 점은 단일 판정 결과가 아니라 반복·교란·판정자 간 강건성을 점검해야 한다는 본 원고의 논거를 보강한다.

**적용 한계.** 주된 실험은 pairwise/list-wise 응답 비교다. 본 원고의 독립적인 이진 mergeability 판정과 동일한 프로토콜이 아니므로, 이 결과를 본 원고의 구체적 보정 방식이나 양성 대조군 결과로 직접 일반화할 수 없다.

## 바로 사용할 수 있는 관련연구 문단

**권장 위치:** 영문 `main.tex`의 Related Work 중 LLM-as-a-judge 단락에서 기존 `llmjudge`, `wang2024fair`, `panickssery2024selfpref` 논의 직후. 국문 원고에도 대응 위치에 번역 삽입 가능하다.

> 최근 연구는 LLM 판정자의 오류가 단일한 정확도 저하가 아니라 입력 표현과 판정 절차에 체계적으로 의존함을 보였다. Chen et al.은 권위·외관 등 내용 외 교란에 인간과 LLM 판정자가 모두 취약함을 보고했고, Shi et al.은 다수의 판정자와 과제에 걸쳐 위치 편향과 반복 비일관성이 판정자·후보·과제 특성에 따라 달라짐을 보였다. 이 결과들은 LLM 리뷰 판정을 고정된 객관 척도로 가정하기보다, 양성 대조군과 반복·교란 검사를 포함한 측정 도구로 먼저 검증해야 함을 뒷받침한다.

## 인용 시 피해야 할 과장

- 두 논문 모두 “LLM 코드 리뷰어가 인간 유지보수자를 대체할 수 없다”를 직접 검증한 연구는 아니다.
- 본 연구의 gold patch 기각률이나 reviewer-family 상관·카파 값은 오직 본 연구 결과로만 제시해야 한다.
- 위치 편향 결과를 현재의 단일 후보 이진 판정에 발생했다고 단정하지 말고, 판정 절차 민감성의 선행 근거로만 사용한다.
