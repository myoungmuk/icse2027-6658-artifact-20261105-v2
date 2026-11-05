"""Validate parsing, frozen selection and no-label judging payloads."""
import json
from pathlib import Path
from prompts import parse, judge_messages, rubric_messages

ROOT = Path(__file__).resolve().parent

def main():
    assert parse('{"verdict":"ACCEPT","reason":"supported"}')['verdict']=='ACCEPT'
    for bad in ['', '{}', '{"verdict":"yes","reason":""}',
                '{"verdict":"reject","reason":""}',
                '{"verdict":"REJECT","reason":"","extra":1}',
                '{"verdict":"REJECT","reason":1}']:
        assert parse(bad) is None, bad
    assert parse('```json\n{"verdict":"REJECT","reason":""}\n```')["verdict"] == "REJECT"
    assert parse('text\n```json\n{"verdict":"REJECT","reason":""}\n```') is None
    tasks = json.loads((ROOT/'tasks.json').read_text())
    assert len(tasks)==20 and sum(t['agent_resolved'] for t in tasks)==10
    for t in tasks:
        for source in ['agent', 'gold']:
            for arm in ['icse_test_blind','cihan_binary_diff','shi_draft_rubric']:
                messages = judge_messages(arm,t,t[source+'_diff'],
                                         'DRAFT_SENTINEL' if arm=='shi_draft_rubric' else None)
                prompt = json.dumps(messages)
                for secret_key in ['agent_resolved','original_packet_id','source_split','candidate_source']:
                    assert secret_key not in prompt
                assert t['original_packet_id'] not in prompt
                assert t[source+'_diff'] in messages[-1]['content']
        rm = rubric_messages(t)[-1]['content']
        assert t['gold_diff'] in rm
        # Agent candidate is never supplied to rubric creation (unless same bytes as reference).
        if t['agent_diff'] != t['gold_diff']:
            assert t['agent_diff'] not in rm
    print('PASS: strict parsing, 20-task balanced sample, 120 complete candidate payloads, label separation.')

if __name__ == '__main__':
    main()
