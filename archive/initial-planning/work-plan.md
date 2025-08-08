# Work Plan: Claude SDK Business Idea Evaluator

This document outlines the initial implementation plan for a prototype that evaluates business ideas using the Claude SDK. The goal is to keep things lean and modular while building up a scalable evaluation pipeline.

---

## Project Summary

- Use Claude SDK to evaluate business ideas stored in text files.
- Evaluate each idea based on two criteria (initially): **market potential** and **competitive landscape**.
- Store the evaluation results for each idea in a structured, easily reviewable format.
- Later phases will introduce criteria like **personal fit** (interests, skills, etc.).
- outcome should be a ranked list of ideas and top reasons why the top ones are the most promising.

---

## Project Structure

```md
project-root/
├── ideas/
│   ├── idea1.md
│   ├── idea2.md
│   └── ...
├── evaluations/
│   ├── idea1.analysis.json
│   ├── idea2.analysis.json
│   └── ...
├── prompts/
│   └── evaluation_prompt.md
├── results/
│   └── summary.md
├── scripts/
│   ├── evaluate_idea.py
│   ├── batch_evaluate.py
│   └── summarize_results.py
├── WORK_PLAN.md
└── requirements.txt
```

---

## 🛠️ Phase 1: Core Evaluation Pipeline

### 1. Create a Claude Prompt Template

- Define prompt in `prompts/evaluation_prompt.txt`
- Prompt should ask Claude to analyze:
  - Market potential (e.g., TAM, trends, urgency)
  - Competitive landscape (e.g., number of players, defensibility)

**Example Template Snippet**:

```md
Analyze the following business idea and score it on:
1. Market potential (1–10)
2. Competitive landscape (1–10)

Return JSON:
{
  "market_potential_score": ...,
  "competitive_landscape_score": ...,
  "reasoning": "..."
}
```

---

### 2. Write a Script: `evaluate_idea.py`

- Reads a single `ideaN.md`
- Fills prompt template
- Sends to Claude via SDK
- Saves results in `evaluations/ideaN.analysis.json`

---

### 3. Write a Batch Script: `batch_evaluate.py`

- Loops over files in `ideas/`
- Calls `evaluate_idea.py` on each
- Skips already evaluated ideas

---

## 📊 Phase 2: Result Aggregation

### 4. Write a Summarization Script: `summarize_results.py`

- Reads all `*.analysis.json` files
- Outputs:
  - `results/summary.csv`: ID, scores, averages
  - Optionally rank by composite score

---

## 💡 Phase 3: Personalization Layer (Future)

- Add criteria like:
  - Alignment with your skills
  - Level of interest or passion
  - Time and capital required
- Could be a second Claude pass with a personal profile prompt

---

## 📦 Dependencies (`requirements.txt`)

```txt
anthropic
tqdm
pandas
python-dotenv
```

---

## 🔧 Suggested Improvements (Later)

- Add YAML frontmatter to idea files for metadata (e.g., author, date)
- Parallelize batch evaluations
- Add CLI with `argparse` for flexibility
- Track evaluations in SQLite or lightweight NoSQL DB
- Integrate Claude API cost tracking

---

## ✅ Next Steps

1. [ ] Define the JSON schema for evaluation results
2. [ ] Write and test `evaluate_idea.py`
3. [ ] Build prompt template
4. [ ] Populate `ideas/` with 3–5 seed files
5. [ ] Run batch evaluation and inspect output
6. [ ] Generate summary CSV
7. [ ] Add README and document usage

---
