"""RAG smoke evaluator -- 3 pre-shipped questions, binary PASS/FAIL per question.

The Lab smoke evaluator proves the grounding-check logic that the Integration's
RAG grounding-rate harness scales up. It is binary by design (PASS/FAIL per
question, exit 0 iff all PASS); it does not aggregate a rate, and it does NOT
apply decline-exclusion -- the three smoke questions are all answerable
against the seeded fixtures, so a decline at the Lab tier is a defect.

Grounding-check methodology (Lab smoke):

  A response is grounded iff (a) response.citations has length >= 1 AND
  (b) every chunk_id in response.citations is present in the candidate set
  returned by the retrieval call for the same question. The Lab smoke does
  NOT apply decline-exclusion (the Lab's 3 questions are all answerable
  against the seeded Weaviate; decline is not in scope at the Lab tier).

The same paragraph appears in the published Applied Lab page so the
documented methodology and the code that scores against it stay in sync.
"""

import json
import os
import sys
import httpx


API_URL = os.environ.get("API_URL", "http://localhost:8000")


def score_grounding(response: dict, candidate_ids: set) -> bool:
    """Return True iff `response` is grounded per the Lab smoke methodology.

    `response` is the JSON body returned by POST /rag/answer.
    `candidate_ids` is the set of chunk_ids returned for the same question.
    """
    citations = response.get("citations", [])
    
    # Condition (a): At least one citation must be present
    if len(citations) < 1:
        return False
        
    # Condition (b): Every cited chunk_id must be in the candidate set
    for citation in citations:
        # استخراج المعرف النصي من داخل القاموس لتفادي الـ TypeError
        cid = citation.get("chunk_id")
        if cid not in candidate_ids:
            return False
            
    return True


def evaluate_question(question: dict) -> bool:
    """Issue one POST /rag/answer; return True iff the response is grounded."""
    url = f"{API_URL}/rag/answer"
    payload = {
        "question": question["question"],
        "k": question.get("k", 4)
    }
    
    try:
        # استخدام httpx.post المباشر بدلاً من فتح Client ليتوافق مع الـ Test Stub
        res = httpx.post(url, json=payload, timeout=60.0)
            
        if res.status_code != 200:
            return False
            
        response_body = res.json()
        
        # استخراج الـ candidate_ids
        candidate_ids = {chunk["chunk_id"] for chunk in response_body.get("retrieved", [])}
        
        return score_grounding(response_body, candidate_ids)
        
    except Exception:
        return False


def main() -> int:
    """Iterate the three smoke questions, print PASS/FAIL, return 0 iff all PASS."""
    fixture_path = os.path.join(os.path.dirname(__file__), "data", "rag_smoke.json")
    with open(fixture_path, encoding="utf-8") as fh:
        questions = json.load(fh)

    all_passed = True
    
    for i, q in enumerate(questions, 1):
        is_grounded = evaluate_question(q)
        if is_grounded:
            print(f"Question {i}: PASS")
        else:
            print(f"Question {i}: FAIL")
            all_passed = False

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())