New-Item -ItemType File -Force -Path app\__init__.py
New-Item -ItemType File -Force -Path app\core\__init__.py
New-Item -ItemType File -Force -Path app\api\__init__.py
New-Item -ItemType File -Force -Path app\api\v1\__init__.py
New-Item -ItemType File -Force -Path app\schemas\__init__.py
New-Item -ItemType File -Force -Path app\services\__init__.py
New-Item -ItemType File -Force -Path app\ml\__init__.py

# Создаём папку db и seeds (их нет)
New-Item -ItemType Directory -Force -Path app\db
New-Item -ItemType Directory -Force -Path app\seeds
New-Item -ItemType File -Force -Path app\db\__init__.py
New-Item -ItemType File -Force -Path app\seeds\__init__.py

Write-Host "✅ Все __init__.py созданы!"