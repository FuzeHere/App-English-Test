from fastapi.testclient import TestClient
from app.main import app


def test_complete_api_integration_flows():
    with TestClient(app) as client:
        # 1. Health & Bank Health
        r_health = client.get("/api/health")
        assert r_health.status_code == 200
        assert r_health.json()["status"] == "ok"

        r_bank = client.get("/api/content/bank-health")
        assert r_bank.status_code == 200
        bank_data = r_bank.json()
        assert bank_data["overall_healthy"] is True
        assert bank_data["total_approved_tasks"] >= 20

        # 2. Reading Practice Flow + Exam Integrity Check
        r_start = client.post("/api/practice/start", json={"skill": "reading", "timed": False, "target_units": 5})
        assert r_start.status_code == 200
        state = r_start.json()
        session_id = state["session_id"]
        q = state["question"]

        # Exam Integrity (PRD Section 31.2): correct_option_id / accepted_answers must NEVER be in active payload
        content = q["content"]
        assert "correct_option_id" not in content
        assert "correct" not in content
        assert "explanation" not in content

        # Submit answer in Practice Mode -> must return immediate explanation & updated theta
        r_ans = client.post(
            f"/api/practice/{session_id}/answer",
            json={
                "question_id": q["question_id"],
                "answer": {"selected_option_id": "A", "answers": {"g1": "on", "q1": "A", "gap1": "B"}},
                "response_time_seconds": 12,
            },
        )
        assert r_ans.status_code == 200
        ans_data = r_ans.json()
        assert ans_data["practice_feedback"] is not None
        assert "explanation" in ans_data["practice_feedback"]
        assert "updated_theta" in ans_data["practice_feedback"]

        # Finish Reading practice & check Result report
        client.post(f"/api/practice/{session_id}/finish")
        r_res = client.get(f"/api/results/{session_id}")
        assert r_res.status_code == 200
        res_data = r_res.json()
        assert res_data["skill_levels"]["reading"] in ("A1", "A2", "B1", "B2", "C1")

        # 3. Writing Practice & AI Evaluation Flow
        w_start = client.post("/api/practice/start", json={"skill": "writing", "timed": False, "writing_part_mode": "full"})
        assert w_start.status_code == 200
        w_session_id = w_start.json()["session_id"]

        p1_sample = (
            "Dear Alex,\n\nThank you so much for helping me set up the photography exhibition on Saturday morning. "
            "The rest of the afternoon went wonderfully, and more than sixty neighbours visited the gallery. "
            "Could we meet at the Riverside Café this Thursday at 5 p.m. so you can return the camera tripod? "
            "Let me know if that time works for you.\n\nBest wishes,\nJordan"
        )
        p2_sample = (
            "Learning to Repair Bicycles in a Community Workshop\n\n"
            "Two years ago, I decided to learn bicycle mechanics outside a formal classroom by volunteering at our neighbourhood repair cooperative. "
            "Every Saturday afternoon, experienced mechanics showed me how to true wheels, adjust derailleur cables, and replace worn brake pads.\n\n"
            "Initially, diagnosing subtle gear-shifting problems was challenging because different bicycle brands use distinct component standards. "
            "However, troubleshooting real commuters' bikes taught me patience and systematic observation.\n\n"
            "In my view, self-directed community learning is often more rewarding than a rigid classroom course. "
            "Not only can learners progress at their own pace, but solving practical problems alongside neighbours builds lasting confidence and community spirit."
        )
        w_ans = client.post(
            f"/api/practice/{w_session_id}/answer",
            json={"part1_text": p1_sample, "part2_text": p2_sample},
        )
        assert w_ans.status_code == 200
        assert w_ans.json()["module_finished"] is True
        assert w_ans.json()["estimated_cefr"] in ("A1", "A2", "B1", "B2", "C1")

        # 4. History & Safe Deletion Check
        r_hist = client.get("/api/history")
        assert r_hist.status_code == 200
        assert len(r_hist.json()["history"]) >= 2

        r_del = client.delete(f"/api/history/{session_id}")
        assert r_del.status_code == 200

        # Verify approved bank is untouched after deleting history
        r_bank_after = client.get("/api/content/bank-health")
        assert r_bank_after.json()["total_approved_tasks"] == bank_data["total_approved_tasks"]
