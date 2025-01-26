# meta developer: Azu-nyyyyyyaaaaan
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

import os

# Текст, который нужно добавить
header = """# meta developer: Azu-nyyyyyyaaaaan
# 🔐 This code is licensed under CC-BY-NC Licence! - https://creativecommons.org/licenses/by-nc/4.0/

"""

# Путь к директории с файлами
directory = "D:\sillyrepo-main"  # Замените на путь к вашей директории

# Перебор всех файлов в директории и поддиректориях
for root, _, files in os.walk(directory):
    for filename in files:
        # Проверка, что файл имеет расширение .py
        if filename.endswith(".py"):
            file_path = os.path.join(root, filename)
            
            # Чтение содержимого файла
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
            
            # Добавление текста в начало файла
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(header + content)

print("Текст успешно добавлен в начало всех .py файлов!")