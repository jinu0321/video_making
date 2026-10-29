"""Create the next numbered blog draft folder under z_블로그작성/.

  python3 .claude/skills/blog/scripts/new_post.py "MySQL 인덱스는 왜 빠를까"
  -> video_making/z_블로그작성/0_mysql_인덱스는_왜_빠를까/

Prints the new folder's absolute path. Exits with an error if a folder for the same topic exists.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]   # video_making/ (.claude/skills/blog/scripts -> up four)
BLOG = ROOT / "z_블로그작성"


def slug(topic):
    # same rule as the shorts folders: "mysql 인덱스" -> "mysql_인덱스", Latin and Hangul runs split by "_"
    s = topic.strip().lower()
    s = re.sub(r"([a-z])([가-힣])", r"\1_\2", s)
    s = re.sub(r"([가-힣])([a-z])", r"\1_\2", s)
    return re.sub(r"\W+", "_", s).strip("_")


def main():
    if len(sys.argv) != 2 or not sys.argv[1].strip():
        raise SystemExit('usage: new_post.py "<주제>"')
    name = slug(sys.argv[1])
    BLOG.mkdir(exist_ok=True)
    posts = [p for p in BLOG.iterdir() if p.is_dir() and re.match(r"\d+_", p.name)]
    same = [p.name for p in posts if p.name.split("_", 1)[1] == name]
    if same:
        raise SystemExit(f"already exists: {', '.join(same)}")
    n = max((int(p.name.split("_", 1)[0]) for p in posts), default=-1) + 1
    dest = BLOG / f"{n}_{name}"
    dest.mkdir()
    print(dest)


if __name__ == "__main__":
    main()
