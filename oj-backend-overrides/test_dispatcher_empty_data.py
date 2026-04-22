import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import django

sys.path.insert(0, "/app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oj.settings")
django.setup()

from judge.dispatcher import JudgeDispatcher
from problem.models import ProblemRuleType
from submission.models import JudgeStatus


class DispatcherEmptyDataTestCase(unittest.TestCase):
    def test_empty_judge_data_marks_system_error(self):
        dispatcher = JudgeDispatcher.__new__(JudgeDispatcher)
        dispatcher.contest_id = None
        dispatcher.last_result = None
        dispatcher.submission = SimpleNamespace(
            id="submission-empty-data",
            language="Python3",
            code="print(1)",
            result=JudgeStatus.PENDING,
            info={},
            statistic_info={},
            save=MagicMock(),
        )
        dispatcher.problem = SimpleNamespace(
            id="problem-empty-data",
            spj_code="",
            spj_language="",
            template={},
            time_limit=1000,
            memory_limit=128,
            test_case_id="dummy-test-case",
            spj_version="",
            io_mode={"io_mode": "Standard IO"},
            rule_type=ProblemRuleType.ACM,
        )

        fake_response = {"err": None, "data": []}

        with patch("judge.dispatcher.ChooseJudgeServer") as mock_choose_server, \
                patch.object(dispatcher, "_request", return_value=fake_response), \
                patch("judge.dispatcher.Submission.objects.filter") as mock_filter, \
                patch.object(dispatcher, "update_problem_status"), \
                patch.object(dispatcher, "update_problem_status_rejudge"), \
                patch("judge.dispatcher.process_pending_task"):
            mock_choose_server.return_value.__enter__.return_value = type(
                "Server", (), {"service_url": "http://judge-server"}
            )()
            mock_choose_server.return_value.__exit__.return_value = False
            mock_filter.return_value.update.return_value = 1

            dispatcher.judge()

        self.assertEqual(dispatcher.submission.result, JudgeStatus.SYSTEM_ERROR)
        self.assertEqual(dispatcher.submission.statistic_info["score"], 0)
        self.assertEqual(
            dispatcher.submission.statistic_info["err_info"],
            "Judge server returned empty test case results.",
        )
        self.assertEqual(dispatcher.submission.info, fake_response)
        dispatcher.submission.save.assert_called_once()


if __name__ == "__main__":
    unittest.main()
