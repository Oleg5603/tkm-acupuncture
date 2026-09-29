# ТКМ — приложение для клиентов

Настольное клиентское приложение. Профессиональный ТКМП и сайт Малахова ведутся в отдельных репозиториях; ссылки и границы продуктов приведены в PRODUCTS.md.

## Запуск в Windows

    python -m venv .venv
    .venv\Scripts\python -m pip install -r requirements-build.txt
    .venv\Scripts\python app/main.py

Сборка: powershell -ExecutionPolicy Bypass -File build_release.ps1
Спецификации: app/TKM-demo.spec и app/TKM-full.spec.

Тесты: python -m pip install pytest && python -m pytest tests -q

Папка landing содержит рекламную страницу клиентского установщика. Сайт ТКМ Малахова находится в Oleg5603/tkm-web. Старая Python-веб-версия перенесена в tkm-web/legacy/python-web.

Код профессионального приложения, его база пациентов и сборка TKMP в текущую клиентскую версию не входят. Предыдущие версии исходников сохранены в истории Git. Пользовательские данные и готовые сборки не добавляются в репозиторий.