"""Rebuild the ASO Bash courses and their Docker acceptance solutions from scripts/aso_bash."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))
from lab.schema import Course, course_yaml
from aso_bash import p11, p12, p13, p21, p22, p31, p32

PRACTICES = [module.practice for module in (p11, p12, p13, p21, p22, p31, p32)]


def main():
    for practice in PRACTICES:
        course = Course.model_validate(practice.course())
        stem = f"aso-bash-p{practice.slug}"
        (ROOT / "courses" / f"{stem}.yaml").write_text(course_yaml(course), encoding="utf-8", newline="\n")
        (ROOT / "courses" / f"{stem}-solutions.json").write_text(json.dumps(practice.solutions, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        print(f"{stem}: {len(course.exercises)} exercises")


if __name__ == "__main__":
    main()
