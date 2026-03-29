from pathlib import Path

projects = Path("/home/mikelange64/PycharmMiscProjects")

print(projects.exists())

for i in projects.rglob("*"):
    if not i.is_file():
        continue
    if i.suffix.lower() == ".toml":
        with i.open() as f:
            print(f.read())