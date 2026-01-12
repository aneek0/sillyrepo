import os

with open("full.txt", "w", encoding="utf-8") as f:
    for file in os.listdir('.'):
        if file.endswith('.py'):
            f.write(os.path.splitext(file)[0] + "\n")