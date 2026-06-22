import json
from pathlib import Path

BASE_DIR = Path("/home/james/cca-f-study")
SEED_GLOB = "seed_data*.json"

def generate_markdown():
    output = ["# CCAF Exam Questions\n"]
    
    seen_stems = set()
    question_num = 1
    
    for path in sorted(BASE_DIR.glob(SEED_GLOB)):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for row in data:
                stem = row.get("stem")
                if not stem or stem in seen_stems:
                    continue
                seen_stems.add(stem)
                
                output.append(f"## Question {question_num}")
                output.append(f"**Domain:** {row.get('domain', 'N/A')} | **Scenario:** {row.get('scenario', 'N/A')}\n")
                output.append(f"{stem}\n")
                
                output.append(f"- **A**: {row.get('choice_a', '')}")
                output.append(f"- **B**: {row.get('choice_b', '')}")
                output.append(f"- **C**: {row.get('choice_c', '')}")
                output.append(f"- **D**: {row.get('choice_d', '')}\n")
                
                correct = row.get("correct", "")
                output.append(f"**Correct Answer:** {correct}")
                output.append(f"\n**Rationales:**")
                output.append(f"- **A**: {row.get('rationale_a', '')}")
                output.append(f"- **B**: {row.get('rationale_b', '')}")
                output.append(f"- **C**: {row.get('rationale_c', '')}")
                output.append(f"- **D**: {row.get('rationale_d', '')}\n")
                
                if row.get("principle"):
                    output.append(f"**Principle:** {row.get('principle')}\n")
                if row.get("anti_pattern"):
                    output.append(f"**Anti-Pattern:** {row.get('anti_pattern')}\n")
                
                output.append("---\n")
                question_num += 1
                
    with open("/home/james/CCAF_Exam_Questions.md", "w", encoding='utf-8') as f:
        f.write("\n".join(output))

if __name__ == "__main__":
    generate_markdown()
    print("Markdown file generated at /home/james/CCAF_Exam_Questions.md")
