"""Simple next-problem recommendation service based on recent submission events."""
from __future__ import annotations

from typing import Any

import psycopg2

from app.config import settings


class SubmissionRecommendationService:
    """Recommend next problem by existing QDUOJ statistics as fallback strategy."""

    def _get_db_connection(self):
        db_url = settings.db_url.replace("+asyncpg", "")
        return psycopg2.connect(db_url)

    def recommend_next_problem(self, user_id: str, current_problem_id: str) -> dict[str, Any] | None:
        """Recommend one not-yet-accepted problem with similar difficulty first."""
        if not user_id or not current_problem_id:
            return None

        conn = self._get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT difficulty FROM problem WHERE _id = %s",
                    (current_problem_id,),
                )
                row = cur.fetchone()
                difficulty = row[0] if row and row[0] else None

                if difficulty:
                    cur.execute(
                        """
                        SELECT p._id, p.title, p.difficulty
                        FROM problem p
                        LEFT JOIN submission s
                          ON s.problem_id = p.id AND s.username = %s AND s.result = 0
                        WHERE p.visible = TRUE
                          AND p._id <> %s
                          AND p.difficulty = %s
                          AND s.id IS NULL
                        ORDER BY p.accepted_number DESC, p.submission_number ASC
                        LIMIT 1
                        """,
                        (user_id, current_problem_id, difficulty),
                    )
                    candidate = cur.fetchone()
                    if candidate:
                        return {
                            "problem_id": candidate[0],
                            "title": candidate[1],
                            "difficulty": candidate[2],
                            "reason": "similar_difficulty_not_solved",
                        }

                cur.execute(
                    """
                    SELECT p._id, p.title, p.difficulty
                    FROM problem p
                    LEFT JOIN submission s
                      ON s.problem_id = p.id AND s.username = %s AND s.result = 0
                    WHERE p.visible = TRUE
                      AND p._id <> %s
                      AND s.id IS NULL
                    ORDER BY p.accepted_number DESC, p.submission_number ASC
                    LIMIT 1
                    """,
                    (user_id, current_problem_id),
                )
                candidate = cur.fetchone()
                if candidate:
                    return {
                        "problem_id": candidate[0],
                        "title": candidate[1],
                        "difficulty": candidate[2],
                        "reason": "popular_not_solved",
                    }
                return None
        finally:
            conn.close()
