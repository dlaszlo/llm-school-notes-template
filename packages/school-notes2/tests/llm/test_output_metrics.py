import json

from school_notes2.llm import metrics, output


def test_read_file_missing_and_invalid(tmp_path):
    path = tmp_path / "result.json"
    assert output.read_file(path, "result")[0] is None
    path.write_text('{"status": "maybe"}')
    value, problems = output.read_file(path, "result")
    assert value is None and problems
    path.write_text('{"status": "question", "questions": [{"text": "Melyik tantárgy?"}]}')
    assert output.read_file(path, "result")[0]["status"] == "question"


def test_extract_stdout_takes_last_valid_object():
    text = 'x {"verdict": "bogus", "findings": []}\n{"verdict": "changes", "findings": []} y\n{"a": 1}'
    value, _ = output.extract_stdout(text, "review")
    assert value == {"verdict": "changes", "findings": []}
    assert output.extract_stdout("no json here", "review")[0] is None


def test_metrics_claude_result_event(tmp_path):
    path = tmp_path / "t.log"
    events = [{"type": "assistant", "message": {"usage": {"input_tokens": 5}}},
              {"type": "result", "usage": {"input_tokens": 100, "output_tokens": 20,
                                           "cache_read_input_tokens": 80},
               "total_cost_usd": 0.12, "num_turns": 7}]
    path.write_text("\n".join(json.dumps(e) for e in events) + "\nplain line\n")
    assert metrics.from_transcript(path) == {"input_tokens": 100, "output_tokens": 20,
                                             "cache_read_input_tokens": 80, "cost_usd": 0.12,
                                             "turns": 7}


def test_metrics_codex_turns_summed(tmp_path):
    path = tmp_path / "t.log"
    line = {"type": "turn.completed", "usage": {"input_tokens": 10, "cached_input_tokens": 4,
                                                "output_tokens": 2}}
    path.write_text(json.dumps(line) + "\n" + json.dumps(line) + "\n")
    assert metrics.from_transcript(path) == {"input_tokens": 20, "cached_input_tokens": 8,
                                             "output_tokens": 4}


def test_metrics_missing_file_is_empty(tmp_path):
    assert metrics.from_transcript(tmp_path / "none.log") == {}
