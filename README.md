# CortexClient

Статический сайт легит-клиента CortexClient для Minecraft: сведения о проекте, гайд, FAQ и карточка загрузки. HTML, CSS и обычный JavaScript, без npm и серверной части. Страница адаптируется к мобильным устройствам; эффекты учитывают настройку уменьшения движения.

## Публикация на GitHub Pages

1. Создайте отдельный публичный репозиторий для CortexClient.
2. Загрузите **всё содержимое этой папки** в корень ветки `main`, включая `.github/workflows/pages.yml`, `scripts/`, `assets/` и `.nojekyll`. Не помещайте сайт во вложенную папку внутри репозитория.
3. Откройте **Settings → Pages → Source → GitHub Actions**.
4. Откройте **Actions → Publish GitHub Pages → Run workflow**. Следующие коммиты в `main` публикуются автоматически.
5. Дождитесь задач `build` и `deploy`; адрес сайта появится в **Settings → Pages**.

Сборка (`scripts/build_site.py`) получает адрес от GitHub Pages автоматически, добавляет canonical, Open Graph, социальную карточку, sitemap и robots.txt в папку `_site`. Публикуется только `_site`.

## Файл для скачивания и данные релиза

Заполните `config.js` (формат JSON внутри `window.SITE_CONFIG = { ... };`, все значения — строки):

| Поле | Что указать |
| --- | --- |
| `product` | Название проекта |
| `downloadUrl` | Прямая HTTPS-ссылка на файл (например, asset из GitHub Releases) |
| `releaseUrl` | HTTPS-ссылка на страницу релиза |
| `version` / `platform` / `fileName` / `fileSize` | Фактические данные выпуска |
| `sha256` | Контрольная сумма из 64 hex-символов (`Get-FileHash -Algorithm SHA256`) |
| `siteUrl` | Только для ручной сборки; в Actions определяется автоматически |

Пока `downloadUrl` пуст, сайт сообщает, что файл ещё не опубликован.

## Локальная проверка

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\prepare-seo.ps1
python -m http.server 8080 --directory .\_site
```

Откройте `http://localhost:8080`. Кроссплатформенный эквивалент: `python scripts/build_site.py`.

## Индексация

- Меняйте `title` и `meta description` в `index.html` — сборка синхронизирует с ними метаданные.
- Картинка предпросмотра: `assets/social-card.png`, 1200 × 630.
- После публикации добавьте URL в Google Search Console и Яндекс Вебмастер, отправьте `sitemap.xml`.

CortexClient — независимый проект, не связан с Mojang и Microsoft. Сайт не выполняет Java-код и не подключается к Minecraft.
