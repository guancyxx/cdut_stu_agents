Classify the student's intent from a programming competition training session.
Current problem: $problem_hint
NOTE: A problem may be selected, but that does NOT mean the student wants teaching right now.
Classify based on what the student ACTUALLY says, not on what problem is open.
If the student is just chatting or greeting, classify as "casual" — do NOT force it into a teaching category.
IMPORTANT CONTEXT — You must consider the conversation history and what the previous AI agent was doing.
If the student is clearly responding to a previous agent's question or following that agent's guidance,
the intent should stay in the SAME flow, not jump to an unrelated category.
Current student message: "$user_input"
Previous conversation (most recent messages):
$history_summary
Previous AI agent: $last_agent_ctx
Possible intents:
- code_review: Request for code analysis, optimization, or style feedback (for the CURRENT problem's code)
- problem_help: Need help understanding or solving the CURRENT problem
- contest_prep: Seeking competition strategies or pressure simulation
- emotional_support: Expressing frustration, confusion, or need for motivation
- learning_plan: Request for study recommendations, progress tracking, OR continuing a learning-coaching dialogue about the CURRENT problem
- answer_to_coach: Student is answering a question or following instructions from the previous agent (this keeps the conversation in the same teaching flow)
- casual: Student is greeting, chatting, making small talk, or asking a non-programming question with NO teaching need. Examples: "hello", "you there?", "how's the weather", "who are you", random conversation that does NOT ask for help with the current problem or any programming topic.
- off_topic: Student explicitly asks about a DIFFERENT programming topic unrelated to the current problem (but still technical, e.g., asking about a different algorithm or language). NOT the same as casual — off_topic is still technical, just not about this problem.
RULES:
- If the student is clearly answering a question from the previous agent, classify as "answer_to_coach"
- Short acknowledgments like "ok", "got it", "understood", "mm-hmm", "yes" that are NOT direct answers to a question should be classified as "casual" — not as "problem_help" or "learning_plan"
- If the student is following up on the previous agent's topic, prefer the same intent category as the previous turn
- IMPORTANT: Having a problem selected does NOT mean every message should be classified as a teaching need.
- Only classify as "problem_help" or "learning_plan" when the student EXPLICITLY asks for help with the problem or is following a teaching flow.
- Classify as "off_topic" only when the student switches to a different technical/programming topic unrelated to the current problem.
- For general questions about algorithms/data structures, if they relate to the current problem, classify as "problem_help"; otherwise classify as "off_topic"
Return ONLY the intent name (one word or phrase, lowercase with underscores).