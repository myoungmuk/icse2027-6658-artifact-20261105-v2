"""Descriptive analysis; failures remain failures and gold stays separate."""
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def wilson(k, n):
    if n == 0:
        return None
    z = 1.959963984540054
    a = 1 + z*z/n
    mid = (k/n + z*z/(2*n))/a
    half = z*math.sqrt(k/n*(1-k/n)/n + z*z/(4*n*n))/a
    return [max(0, mid-half), min(1, mid+half)]

def ratio(a, b):
    return a/b if b else None

def main():
    tasks = json.loads((ROOT/'tasks.json').read_text())
    cfg = json.loads((ROOT/'config.json').read_text())
    run = ROOT/'run_v1'
    assert (run/'completion.json').is_file(), 'Run incomplete'
    out = ROOT/'analysis_v1'
    out.mkdir(exist_ok=False)
    rows = []
    for t in tasks:
        for source in ['agent', 'gold']:
            for arm in cfg['arms']:
                p = run/'raw'/f'{t["task_code"]}_{source}_{arm}.json'
                r = json.loads(p.read_text())
                valid = r['status'] == 'ok' and r.get('parsed') is not None
                decision = r['parsed']['verdict'] if valid else None
                rows.append({'task_code': t['task_code'], 'instance_id': t['instance_id'],
                    'repo': t['repo'], 'source': source, 'arm': arm,
                    'agent_resolved_reference': t['agent_resolved'], 'status': r['status'],
                    'decision': decision, 'reason': r['parsed']['reason'] if valid else '',
                    'input_tokens': r.get('input_tokens'), 'output_tokens': r.get('output_tokens'),
                    'raw_file': str(p.relative_to(ROOT)),
                    'raw_sha256': hashlib.sha256(p.read_bytes()).hexdigest()})
    with (out/'verdicts.csv').open('x', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    summary = {'task_count': len(tasks), 'candidate_count': 2*len(tasks),
               'planned_judgments': 6*len(tasks),
               'repo_counts': dict(Counter(t['repo'] for t in tasks)),
               'label_provenance': 'Inherited official Agentless resolved IDs; no fresh harness execution or human annotation.',
               'arms': {}, 'paired_decisions': {}}
    for arm in cfg['arms']:
        agent = [r for r in rows if r['arm'] == arm and r['source'] == 'agent']
        valid = [r for r in agent if r['decision'] is not None]
        tp = sum(r['decision'] == 'ACCEPT' and r['agent_resolved_reference'] for r in valid)
        tn = sum(r['decision'] == 'REJECT' and not r['agent_resolved_reference'] for r in valid)
        fp = sum(r['decision'] == 'ACCEPT' and not r['agent_resolved_reference'] for r in valid)
        fn = sum(r['decision'] == 'REJECT' and r['agent_resolved_reference'] for r in valid)
        gold = [r for r in rows if r['arm'] == arm and r['source'] == 'gold']
        goldvalid = [r for r in gold if r['decision'] is not None]
        sensitivity, specificity = ratio(tp, tp+fn), ratio(tn, tn+fp)
        summary['arms'][arm] = {
            'agent_planned': len(agent), 'agent_valid': len(valid),
            'agent_failures': len(agent)-len(valid), 'tp': tp, 'tn': tn, 'fp': fp, 'fn': fn,
            'agent_accuracy_valid': ratio(tp+tn, len(valid)),
            'agent_correct_planned_fraction': ratio(tp+tn, len(agent)),
            'agent_accuracy_wilson95': wilson(tp+tn, len(valid)),
            'sensitivity': sensitivity, 'sensitivity_wilson95': wilson(tp, tp+fn),
            'specificity': specificity, 'specificity_wilson95': wilson(tn, tn+fp),
            'balanced_accuracy': (sensitivity+specificity)/2 if sensitivity is not None and specificity is not None else None,
            'gold_planned': len(gold), 'gold_valid': len(goldvalid),
            'gold_accepted': sum(r['decision']=='ACCEPT' for r in goldvalid),
            'gold_acceptance_rate_valid': ratio(sum(r['decision']=='ACCEPT' for r in goldvalid), len(goldvalid)),
            'statuses': dict(Counter(r['status'] for r in rows if r['arm']==arm))}
    indexed = {(r['task_code'],r['source'],r['arm']):r for r in rows}
    for arm in cfg['arms'][1:]:
        for source in ['agent', 'gold']:
            pairs = [(indexed[t['task_code'],source,'icse_test_blind'],indexed[t['task_code'],source,arm]) for t in tasks]
            pairs = [(a,b) for a,b in pairs if a['decision'] is not None and b['decision'] is not None]
            summary['paired_decisions'][arm+'_'+source] = {
                'complete_pairs': len(pairs), 'same_decision': sum(a['decision']==b['decision'] for a,b in pairs),
                'icse_accept_baseline_reject': sum(a['decision']=='ACCEPT' and b['decision']=='REJECT' for a,b in pairs),
                'icse_reject_baseline_accept': sum(a['decision']=='REJECT' and b['decision']=='ACCEPT' for a,b in pairs)}
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    table = ['| 방식 | Agent 기능 라벨 일치 | 해결 패치 승인 | 미해결 패치 거절 | 개발자 패치 승인 | 실패 |',
             '|---|---:|---:|---:|---:|---:|']
    for arm,s in summary['arms'].items():
        table.append(f'| {arm} | {s["tp"]+s["tn"]}/{s["agent_valid"]} | {s["tp"]}/{s["tp"]+s["fn"]} | {s["tn"]}/{s["tn"]+s["fp"]} | {s["gold_accepted"]}/{s["gold_valid"]} | {40-s["agent_valid"]-s["gold_valid"]} |')
    report = '''# ICSE 핵심 선행연구 2편: 신규 binary judge 예비 비교

20개 이슈, 40개 패치, 3가지 프롬프트 방식으로 새 추론을 실행했다.
원 논문의 전체 시스템 재현이 아니라 Qwen2.5-Coder-7B-Instruct를 고정한 **적응 실험**이다.
기존 ICSE 결과를 재집계한 수치가 아니다. 최초 프로토콜·선택·프롬프트는 새 판정 전에 해시로 고정했다.

'''+ '\n'.join(table) + '''

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
'''
    (out/'RESULTS_KO.md').write_text(report)
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__ == '__main__':
    main()
