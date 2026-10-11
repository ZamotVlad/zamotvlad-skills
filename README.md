# ZamotVlad Skills

Колекція скілів для Claude (Claude Code, claude.ai), які я використовую у своїх проєктах.

A collection of Claude skills (Claude Code, claude.ai) I use in my projects.

## Скіли

| Скіл | Що робить |
|---|---|
| [vyshyvankadaily-blog](skills/vyshyvankadaily-blog) | Повний цикл статті для блогу [VyshyvankaDaily](https://vyshyvankadaily.live): вибір теми з оцінкою, ключі, бриф, текст українською й англійською, чистка від шаблонних AI-зворотів, перевірка фактів, SEO-аудит скриптом і HTML-звіт для рев'ю |

## Як встановити

**claude.ai:** Settings -> Capabilities -> Skills -> Upload skill. Завантажте zip з папкою скілу (наприклад, `vyshyvankadaily-blog/` з `SKILL.md` усередині).

**Claude Code:** скопіюйте папку скілу в `.claude/skills/` проєкту або в `~/.claude/skills/`.

```bash
git clone https://github.com/ZamotVlad/zamotvlad-skills
cp -r zamotvlad-skills/skills/vyshyvankadaily-blog ~/.claude/skills/
```

## Структура скілу

```
skills/<назва>/
  SKILL.md        інструкції й метадані (name, description)
  references/     довідкові файли, які скіл читає за потреби
  scripts/        допоміжні скрипти
```

## Ліцензія

MIT
