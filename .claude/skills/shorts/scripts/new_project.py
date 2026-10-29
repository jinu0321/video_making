"""Create the next numbered Shorts project folder from the template.

  python3 .claude/skills/shorts/scripts/new_project.py "Redis란 무엇이고 왜 쓰는가"
  -> video_making/1_redis_란_무엇이고_왜_쓰는가/

Prints the new folder's absolute path. Exits with an error if a folder for the same topic exists.
"""
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
ROOT = SKILL.parents[2]          # video_making/ (.claude/skills/shorts -> up three)


def slug(topic):
    s = topic.strip().lower()
    # "redis란" -> "redis_란": Latin and Hangul runs are split by "_"
    s = re.sub(r"([a-z])([가-힣])", r"\1_\2", s)
    s = re.sub(r"([가-힣])([a-z])", r"\1_\2", s)
    return re.sub(r"\W+", "_", s).strip("_")


def main():
    if len(sys.argv) != 2 or not sys.argv[1].strip():
        raise SystemExit('usage: new_project.py "<주제>"')
    name = slug(sys.argv[1])
    projects = [p for p in ROOT.iterdir() if p.is_dir() and re.match(r"\d+_", p.name)]
    same = [p.name for p in projects if p.name.split("_", 1)[1] == name]
    if same:
        raise SystemExit(f"already exists: {', '.join(same)}")
    n = max((int(p.name.split("_", 1)[0]) for p in projects), default=-1) + 1
    dest = ROOT / f"{n}_{name}"

    shutil.copytree(SKILL / "template", dest)
    # fonts are kept once in video_making/fonts/; each project links to them
    (dest / "assets").mkdir(exist_ok=True)
    (dest / "assets/fonts").symlink_to("../../fonts")
    (dest / "meta.json").write_text(json.dumps({
        "id": f"shorts-{n}",
        "name": dest.name,
        "createdAt": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
    }, ensure_ascii=False, indent=2) + "\n")
    print(dest)


if __name__ == "__main__":
    main()
