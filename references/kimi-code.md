# Kimi Code

Инструкция относится к текущему runtime Kimi Code, исследованному в Desktop 1.1.4, и его нативному инструменту `Agent`. Старый Python `kimi-cli` не является основанием для этого контракта.

## Подключение

Нужен Python 3.10+. Помести каталог скилла в `$KIMI_CODE_HOME/skills/arch-simplicity-guard`; без `KIMI_CODE_HOME` используется `~/.kimi-code/skills/arch-simplicity-guard`. Загружай скилл нативным Skill или командой `/skill:arch-simplicity-guard`, чтобы подставился session ID из тела `SKILL.md`.

## Один субагент, два вызова

Если ты уже выполняющий проверку субагент с переданными нативными ID, сразу переходи к команде селектора. Не создавай нового агента и не повторяй подготовительный вызов.

Родительский агент:

1. Получи подставленный session ID и путь скилла из `SKILL.md`. Запусти `Agent` с `run_in_background=false`, без `subagent_type` и без Swarm. Если текущая схема предлагает параметр `model`, передай `"primary"` для наследования текущей модели и thinking. Иначе опусти `model`: среда применит собственные настройки. Это допускает `secondary_model.force`; конфигурацию не меняй. Агенту нужны Bash и чтение, встроенный `plan` без Bash не подходит.
2. Первое поручение: «Подготовка проверки Architecture Simplicity Guard. Пока не анализируй материалы и не вызывай инструменты или субагентов. Ответь READY. Задача и нативные ID будут переданы следующим вызовом». Возьми `agent_id` из нативного результата инструмента, а не из текста ответа модели.
3. Вызови `Agent` с `resume` этого ID и `run_in_background=false`. Не передавай `subagent_type` или `model` при resume. Передай session ID, agent ID, абсолютный путь скилла, задачу, материалы, ограничения и способ первоначального запуска. Поручи самостоятельно прочитать скилл, выполнить селектор и вернуть проверку без дальнейшего делегирования.

Оба вызова относятся к одному субагенту. Для следующей независимой проверки повтори последовательность с новым агентом: resume сохраняет прежние настройки ребёнка. Если подготовительный вызов не завершился успешно, не считай проверку выполненной и не запускай автоматически дубликаты.

## Получение инструкций внутри проверяющего

```sh
python3 -B /absolute/path/to/arch-simplicity-guard/scripts/render_instructions.py \
  --harness kimi-code --session-id SESSION_ID --agent-id AGENT_ID
```

Замени путь и ID значениями, полученными от родителя из нативной среды. Это адресация журнала, а не ручной выбор модели. Прочитай весь `instructions` и выполни проверку по контракту `SKILL.md`.

Reader находит точное совпадение session ID в `$KIMI_CODE_HOME/session_index.jsonl` и читает только `agents/<agent_id>/wire.jsonl` этой сессии. Модель берётся из `model` текущего `llm.request` с `kind: "loop"` внутри активного turn, effort — из `thinkingEffort`. `modelAlias`, конфигурационные defaults, compaction и история другого агента не подставляются. Отсутствующий effort возвращается как `null`.

Журнал и индекс внутренние; при несовместимости или недоступности текущей модели проверка остаётся невыполненной. Hook, дополнительный журнал и фиксация состояния проекта не требуются.

Источники: [Agent и resume](https://moonshotai.github.io/kimi-code/en/customization/agents), [наследование и defaults](https://moonshotai.github.io/kimi-code/en/configuration/config-files#secondary_model), [расположение данных](https://moonshotai.github.io/kimi-code/en/configuration/data-locations), [Skill](https://moonshotai.github.io/kimi-code/en/customization/skills). Нативная подстановка `${KIMI_SESSION_ID}` и формат `llm.request` дополнительно проверены в коде установленного Desktop 1.1.4.
