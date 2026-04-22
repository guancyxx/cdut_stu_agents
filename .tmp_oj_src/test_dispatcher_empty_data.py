import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oj.settings")

import django

django.setup()

from judge.dispatcher import JudgeDispatcher
from problem.models import ProblemRuleType
from submission.models import JudgeStatus


class DummyServer:
    service_url = "http://judge-server"


class DummyChooseJudgeServer:
    def __enter__(self):
        return DummyServer()

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


class DummySubmissionQuerySet:
    def __init__(self, update_calls):
        self.update_calls = update_calls

    def update(self, **kwargs):
        self.update_calls.append(kwargs)


class DummySubmissionModel:
    def __init__(self, update_calls):
        self.objects = self
        self.update_calls = update_calls

    def filter(self, **kwargs):
        return DummySubmissionQuerySet(self.update_calls)


class JudgeDispatcherEmptyDataTest(unittest.TestCase):
    def test_judge_marks_system_error_when_judge_server_returns_empty_data(self):
        update_calls = []
        submission = SimpleNamespace(
            id="submission-id",
            contest_id=None,
            result=JudgeStatus.PENDING,
            info={},
            statistic_info={},
            language="Python3",
            code="print(1)",
            user_id=1,
            save=lambda: None,
        )
        problem = SimpleNamespace(
            id=1,
            _id="fps-7681",
            rule_type=ProblemRuleType.ACM,
            time_limit=1000,
            memory_limit=256,
            test_case_id="test-case-id",
            spj_code="",
            spj_language="",
            spj_version="",
            template={},
            io_mode={"io_mode": "Standard IO"},
        )

        dispatcher = JudgeDispatcher.__new__(JudgeDispatcher)
        dispatcher.submission = submission
        dispatcher.contest_id = None
        dispatcher.last_result = None
        dispatcher.problem = problem

        with patch("judge.dispatcher.ChooseJudgeServer", DummyChooseJudgeServer), \
             patch("judge.dispatcher.Submission", DummySubmissionModel(update_calls)), \
             patch("judge.dispatcher.SysOptions", SimpleNamespace(languages=[{"name": "Python3", "config": {}}])), \
             patch.object(dispatcher, "_request", return_value={"err": None, "data": []}), \
             patch("judge.dispatcher.process_pending_task", lambda: None), \
             patch.object(JudgeDispatcher, "update_problem_status", lambda self: None), \
             patch.object(JudgeDispatcher, "update_problem_status_rejudge", lambda self: None), \
             patch.object(JudgeDispatcher, "update_contest_problem_status", lambda self: None), \
             patch.object(JudgeDispatcher, "update_contest_rank", lambda self: None):
            dispatcher.judge()

        self.assertEqual(update_calls, [{"result": JudgeStatus.JUDGING}])
        self.assertEqual(submission.result, JudgeStatus.SYSTEM_ERROR)
        self.assertEqual(submission.info, {"err": None, "data": []})
        self.assertEqual(submission.statistic_info["score"], 0)
        self.assertIn("empty", submission.statistic_info["err_info"].lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
