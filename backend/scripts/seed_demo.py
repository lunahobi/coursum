from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from html import escape

from sqlalchemy import select, text

from app.core.content_localization import follow_up_recommendation, is_russian, review_topic_recommendation
from app.core.db import Base, SessionLocal, engine
from app.core.security import hash_password
from app.core.text_repair import repair_mojibake_text, repair_text_payload
from app.models.models import (
    AnswerOption,
    Attempt,
    AttemptAnswer,
    Course,
    CourseAssignment,
    Enrollment,
    Group,
    GroupMember,
    Lesson,
    Membership,
    Question,
    QuestionTopic,
    Recommendation,
    Result,
    Role,
    RoleName,
    Tenant,
    Test,
    Topic,
    User,
)


@dataclass
class TopicSeed:
    key: str
    title: str
    description: str


@dataclass
class LessonSeed:
    topic_key: str
    title: str
    summary: str
    content: str
    content_pages: list[dict]
    image_url: str
    video_url: str
    duration_minutes: int = 8


@dataclass
class QuestionSeed:
    topic_key: str
    difficulty: int
    text: str
    explanation: str
    options: list[tuple[str, bool]]
    estimated_seconds: int = 30


@dataclass
class CourseSeed:
    title: str
    description: str
    topics: list[TopicSeed]
    lessons: list[LessonSeed]
    test_title: str
    questions: list[QuestionSeed]


def reset_database() -> None:
    dialect = engine.dialect.name
    if dialect == "postgresql":
        with engine.begin() as connection:
            connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
            connection.execute(text("GRANT ALL ON SCHEMA public TO public"))
    else:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def lesson_image(name: str, locale: str) -> str:
    suffix = "ru" if is_russian(locale) else "en"
    return f"/media/{name}-{suffix}.png"


def lesson_video(name: str, locale: str) -> str:
    suffix = "ru" if is_russian(locale) else "en"
    return f"/media/{name}-{suffix}.mp4"


def localized_text(locale: str, *, ru: str, en: str) -> str:
    return ru if is_russian(locale) else en


def localized_question_seed(
    *,
    locale: str,
    topic_key: str,
    difficulty: int,
    text_ru: str,
    text_en: str,
    explanation_ru: str,
    explanation_en: str,
    options_ru: list[tuple[str, bool]],
    options_en: list[tuple[str, bool]],
    estimated_seconds: int = 30,
) -> QuestionSeed:
    return QuestionSeed(
        topic_key=topic_key,
        difficulty=difficulty,
        text=localized_text(locale, ru=text_ru, en=text_en),
        explanation=localized_text(locale, ru=explanation_ru, en=explanation_en),
        options=options_ru if is_russian(locale) else options_en,
        estimated_seconds=estimated_seconds,
    )


def topic_profile(locale: str, topic_key: str) -> dict[str, object]:
    profiles = {
        "org": {
            "signals_intro": localized_text(
                locale,
                ru="В этой теме важно быстро понять, кто принимает решения, а кто помогает с исполнением. Ошибки здесь редко выглядят драматично, но почти всегда съедают время и создают ненужную тревогу.",
                en="This topic is about quickly understanding who makes decisions and who helps execute them. Mistakes here rarely look dramatic, but they almost always waste time and create avoidable anxiety.",
            ),
            "mistakes": [
                localized_text(locale, ru="Писать один общий запрос всем подряд вместо того, чтобы разделить его по владельцам.", en="Send one broad request to everyone instead of splitting it by owner."),
                localized_text(locale, ru="Путать роли наставника, руководителя и HR, поэтому получать частичный или запоздалый ответ.", en="Mix up the roles of mentor, manager, and HR, then get only partial or delayed help."),
                localized_text(locale, ru="Ждать, пока проблема станет критичной, вместо раннего уточнения маршрута эскалации.", en="Wait until the issue becomes critical instead of clarifying the escalation route early."),
            ],
            "coach_tip": localized_text(
                locale,
                ru="Хороший признак освоения темы: сотрудник не просто знает имена, а понимает, какую проблему какому владельцу нести первой.",
                en="A strong signal of mastery is not just knowing names, but knowing which problem goes to which owner first.",
            ),
            "action_prompts": [
                localized_text(locale, ru="Как вы покажете новому сотруднику разницу между наставником и руководителем без длинной теории?", en="How would you show a new employee the difference between a mentor and a manager without a long lecture?"),
                localized_text(locale, ru="Какой один маршрут эскалации стоит закрепить у команды уже на этой неделе?", en="Which single escalation route is worth reinforcing with the team this week?"),
            ],
        },
        "tools": {
            "signals_intro": localized_text(
                locale,
                ru="Здесь ключевой вопрос не в том, есть ли инструмент, а в том, становится ли работа после него прозрачнее. Хороший процесс видно по владельцу, сроку и зафиксированному решению.",
                en="The key question here is not whether a tool exists, but whether work becomes more visible because of it. A strong process shows an owner, a deadline, and a recorded decision.",
            ),
            "mistakes": [
                localized_text(locale, ru="Оставлять важное решение только в чате, а затем спорить о том, кто что понял.", en="Leave an important decision only in chat and later argue about what was agreed."),
                localized_text(locale, ru="Искать актуальную форму или политику в старой переписке вместо утвержденного портала.", en="Search for the latest form or policy in old messages instead of the approved portal."),
                localized_text(locale, ru="Заводить работу без владельца или дедлайна, рассчитывая, что команда сама все удержит в памяти.", en="Start work with no owner or deadline and hope the team will keep it all in memory."),
            ],
            "coach_tip": localized_text(
                locale,
                ru="Если после обсуждения нельзя быстро показать карточку задачи, ссылку на портал или текущий статус, значит система еще не стала источником правды.",
                en="If you cannot quickly point to the task, portal page, or current status after a discussion, the system has not become the source of truth yet.",
            ),
            "action_prompts": [
                localized_text(locale, ru="Какой тип решений у вашей команды чаще всего остается только в чате?", en="What type of decisions in your team most often remain only in chat?"),
                localized_text(locale, ru="Какой один ритуал поможет быстрее переносить договоренности в трекер или портал?", en="What single ritual would help move agreements into the tracker or portal faster?"),
            ],
        },
        "comms": {
            "signals_intro": localized_text(
                locale,
                ru="Деловое сообщение считается сильным не по тону «вежливо/невежливо», а по тому, может ли адресат ответить на него за один проход. Чем меньше ему приходится догадываться, тем лучше работает коммуникация.",
                en="A business message is strong not because it sounds 'polite enough', but because the recipient can answer it in one pass. The less guessing required, the better the communication works.",
            ),
            "mistakes": [
                localized_text(locale, ru="Начинать с формулировки «нужно срочно», не объясняя, что произошло и что именно требуется.", en="Open with 'urgent' without explaining what happened or what is needed."),
                localized_text(locale, ru="Смешивать несколько запросов и несколько адресатов в одном сообщении.", en="Mix several asks and several recipients into one message."),
                localized_text(locale, ru="Оставлять дедлайн в голове или в созвоне, а не в явном тексте сообщения.", en="Keep the deadline in your head or in a meeting instead of writing it explicitly."),
            ],
            "coach_tip": localized_text(
                locale,
                ru="Если получатель может переслать ваше сообщение дальше без дополнительных пояснений, значит формулировка уже достаточно ясная.",
                en="If the recipient can forward your message without adding explanations, the wording is already clear enough.",
            ),
            "action_prompts": [
                localized_text(locale, ru="Как вы сократите следующее срочное сообщение до трех понятных элементов: контекст, действие, срок?", en="How would you reduce your next urgent message to three clear parts: context, action, and timing?"),
                localized_text(locale, ru="Какую фразу вы уберете из переписки, потому что она звучит вежливо, но не помогает двигаться дальше?", en="Which phrase would you remove from your messaging because it sounds polite but does not help move work forward?"),
            ],
        },
        "support": {
            "signals_intro": localized_text(
                locale,
                ru="Тема поддержки и эскалации работает хорошо, когда блокер становится понятным раньше, чем превращается в кризис. Здесь ценятся факты, четкий следующий шаг и правильный канал.",
                en="Support and escalation work well when a blocker becomes clear before it turns into a crisis. Facts, a clear next step, and the right channel matter most here.",
            ),
            "mistakes": [
                localized_text(locale, ru="Эскалировать слишком поздно, когда времени защитить срок уже почти не осталось.", en="Escalate too late, when there is barely any time left to protect the deadline."),
                localized_text(locale, ru="Писать эмоциональное сообщение без статуса, влияния и конкретного запроса на помощь.", en="Write an emotional message with no status, impact, or concrete request for help."),
                localized_text(locale, ru="Скрывать, что уже было попробовано, и заставлять следующего владельца начинать расследование заново.", en="Hide what has already been tried and force the next owner to restart the investigation."),
            ],
            "coach_tip": localized_text(
                locale,
                ru="Хорошая эскалация не драматизирует ситуацию, а экономит время другой стороне на входе в проблему.",
                en="A good escalation does not dramatize the issue; it saves the next person time when entering the problem.",
            ),
            "action_prompts": [
                localized_text(locale, ru="Как вы поймете, что запрос уже пора эскалировать, а не просто напоминать о нем?", en="How will you know that a request should be escalated instead of merely followed up?"),
                localized_text(locale, ru="Какую минимальную структуру сообщения об эскалации вы хотите закрепить у команды?", en="What minimum escalation-message structure do you want to reinforce with the team?"),
            ],
        },
        "passwords": {
            "signals_intro": localized_text(
                locale,
                ru="Парольная гигиена почти всегда выглядит скучно, пока не становится причиной инцидента. Сильная практика здесь — это дисциплина, а не героизм после ошибки.",
                en="Password hygiene looks boring right up until it causes an incident. Strong practice here is disciplined routine, not heroics after a mistake."),
            "mistakes": [
                localized_text(locale, ru="Использовать один и тот же пароль в нескольких рабочих системах.", en="Reuse the same password across several work systems."),
                localized_text(locale, ru="Передавать коды, пароли или временные доступы 'в порядке исключения'.", en="Share codes, passwords, or temporary access 'just this once'."),
                localized_text(locale, ru="Хранить чувствительные учетные данные вне менеджера паролей или одобренной процедуры.", en="Store sensitive credentials outside the password manager or the approved process."),
            ],
            "coach_tip": localized_text(
                locale,
                ru="Если сотрудник знает, как быстро заменить скомпрометированный пароль без хаоса, тема усвоена лучше, чем при знании одной теории.",
                en="If a learner knows how to replace a compromised password quickly and calmly, the topic is better mastered than if they only know the theory.",
            ),
            "action_prompts": [
                localized_text(locale, ru="Какой ваш текущий парольный ритуал нужно упростить, чтобы не тянуться к небезопасным shortcut'ам?", en="Which part of your password routine needs simplification so you stop reaching for unsafe shortcuts?"),
                localized_text(locale, ru="Где в вашей среде нужен более явный сценарий действий после подозрения на компрометацию?", en="Where in your environment do you need a clearer playbook for suspected credential compromise?"),
            ],
        },
        "phishing": {
            "signals_intro": localized_text(
                locale,
                ru="Фишинг редко выглядит как 'очевидное зло'. Чаще он маскируется под обычный рабочий поток, поэтому ценится не интуиция, а спокойная проверка нескольких сигналов.",
                en="Phishing rarely looks like obvious evil. It usually imitates normal work, so what matters is not intuition but a calm check of a few signals.",
            ),
            "mistakes": [
                localized_text(locale, ru="Верить знакомому логотипу или тону письма, не проверив домен и ссылку.", en="Trust a familiar logo or tone without checking the domain and link target."),
                localized_text(locale, ru="Открывать вложение из-за срочности, не останавливаясь на верификацию отправителя.", en="Open an attachment because of urgency without stopping to verify the sender."),
                localized_text(locale, ru="Рассылать подозрительное письмо коллегам вместо отправки в утвержденный канал проверки.", en="Forward a suspicious email to coworkers instead of using the approved reporting path."),
            ],
            "coach_tip": localized_text(
                locale,
                ru="Если сотрудник умеет остановить себя на первой секунде срочности и проверить домен, это уже снимает значительную часть риска.",
                en="If a learner can interrupt the first moment of urgency and verify the domain, that already removes a large part of the risk.",
            ),
            "action_prompts": [
                localized_text(locale, ru="Какой сигнал фишинга вы лично чаще всего замечаете слишком поздно?", en="Which phishing signal do you personally notice too late most often?"),
                localized_text(locale, ru="Как вы сделаете проверку домена и ссылки частью автоматического поведения?", en="How will you make checking domains and links part of your automatic behavior?"),
            ],
        },
        "data": {
            "signals_intro": localized_text(
                locale,
                ru="Работа с чувствительными файлами обычно ломается не в момент кражи, а в момент 'удобного' шеринга. Здесь важны канал, адресат и жизненный цикл копий.",
                en="Sensitive-file handling usually breaks not at the moment of theft, but at the moment of convenient sharing. The key variables are the channel, the recipient, and the lifecycle of copies.",
            ),
            "mistakes": [
                localized_text(locale, ru="Пересылать рабочие файлы через личную почту или неутвержденный обменник.", en="Send work files through personal email or an unapproved file-sharing tool."),
                localized_text(locale, ru="Давать доступ по принципу 'ну это же коллега', а не по бизнес-необходимости.", en="Grant access because 'they are a colleague' instead of because they have a business need."),
                localized_text(locale, ru="Оставлять лишние копии файла после того, как официальная версия уже зафиксирована.", en="Leave unnecessary copies after the approved record already exists."),
            ],
            "coach_tip": localized_text(
                locale,
                ru="Самый полезный вопрос перед отправкой файла: кто увидит его после меня и нужен ли ему этот уровень доступа на самом деле?",
                en="The most useful question before sending a file is: who will be able to see it after me, and do they really need that level of access?",
            ),
            "action_prompts": [
                localized_text(locale, ru="Какой самый частый 'удобный' путь пересылки файлов в вашей среде нужно заменить безопасным?", en="Which convenient file-sharing habit in your environment most needs a safer replacement?"),
                localized_text(locale, ru="Какая проверка перед отправкой файла должна стать обязательной?", en="What pre-send file check should become non-negotiable?"),
            ],
        },
        "incident": {
            "signals_intro": localized_text(
                locale,
                ru="После подозрительного события главная ошибка — ждать полной уверенности. Для инцидентов ценнее ранний сигнал и сохраненные детали, чем поздний идеальный диагноз.",
                en="After a suspicious event, the main mistake is waiting for certainty. Early reporting and preserved details matter more than a late perfect diagnosis.",
            ),
            "mistakes": [
                localized_text(locale, ru="Откладывать сообщение об инциденте до момента, когда 'станет точно понятно'.", en="Delay reporting until it becomes 'completely clear' what happened."),
                localized_text(locale, ru="Стирать следы события, потому что хочется сначала разобраться самостоятельно.", en="Delete traces of the event because you want to figure it out on your own first."),
                localized_text(locale, ru="Исправлять последствия в одиночку, не дав команде ИБ своевременно среагировать.", en="Try to fix the impact alone without giving the security team a timely chance to respond."),
            ],
            "coach_tip": localized_text(
                locale,
                ru="Полезный навык — не только сообщить о событии, но и сразу сохранить минимальный набор деталей: время, система, действие, что уже было сделано.",
                en="A useful skill is not only reporting the event, but preserving the minimum detail set right away: time, system, action, and what has already been tried.",
            ),
            "action_prompts": [
                localized_text(locale, ru="Какое первое сообщение вы отправите, если увидите подозрительный вход или странное письмо прямо сейчас?", en="What first message would you send if you saw a suspicious login or strange email right now?"),
                localized_text(locale, ru="Как вы убедитесь, что в момент стресса не начнете скрывать или 'чинить' инцидент в одиночку?", en="How will you stop yourself from hiding or self-fixing an incident under stress?"),
            ],
        },
        "sla": {
            "signals_intro": localized_text(
                locale,
                ru="Тема SLA — это не только о сроках, а о предсказуемости для клиента. Когда владелец и следующий апдейт понятны, даже сложный кейс воспринимается спокойнее.",
                en="SLA is not only about deadlines; it is about predictability for the client. When the owner and next update are clear, even a difficult case feels more manageable.",
            ),
            "mistakes": [
                localized_text(locale, ru="Молчать до полного решения, вместо того чтобы обозначить владение и следующий контрольный срок.", en="Stay silent until full resolution instead of establishing ownership and the next checkpoint."),
                localized_text(locale, ru="Поднимать риск SLA слишком поздно, когда времени на маневр уже почти нет.", en="Raise SLA risk too late, when there is barely any room left to react."),
                localized_text(locale, ru="Передавать кейс между командами без явного владельца и без обновления клиента.", en="Move the case between teams without a clear owner and without updating the client."),
            ],
            "coach_tip": localized_text(
                locale,
                ru="Хороший контроль SLA заметен заранее: риск виден в системе еще до того, как клиент спрашивает, что происходит.",
                en="Good SLA control is visible early: the risk appears in the system before the client asks what is happening.",
            ),
            "action_prompts": [
                localized_text(locale, ru="Как вы будете замечать риск SLA до того, как срок реально сорвется?", en="How will you notice SLA risk before the deadline is actually missed?"),
                localized_text(locale, ru="Что в вашем процессе мешает удерживать одного явного владельца кейса?", en="What in your process gets in the way of maintaining a single visible case owner?"),
            ],
        },
        "tone": {
            "signals_intro": localized_text(
                locale,
                ru="Профессиональный тон не означает холодность. Он означает, что клиент слышит уважение и ясность вместо обороны, раздражения и пустых обещаний.",
                en="A professional tone does not mean being cold. It means the client hears respect and clarity instead of defensiveness, irritation, or empty promises.",
            ),
            "mistakes": [
                localized_text(locale, ru="Подменять эмпатию пустыми фразами без конкретного следующего шага.", en="Replace empathy with polite-sounding phrases that contain no next step."),
                localized_text(locale, ru="Пытаться 'успокоить' клиента приказным тоном.", en="Try to calm the client down with a commanding tone."),
                localized_text(locale, ru="Обещать то, что не контролируется вашей ролью или командой.", en="Promise outcomes that your role or team does not actually control."),
            ],
            "coach_tip": localized_text(
                locale,
                ru="Самая сильная сервисная фраза одновременно признает влияние на клиента и объясняет следующий проверяемый шаг.",
                en="The strongest service phrase both acknowledges client impact and explains the next verifiable step.",
            ),
            "action_prompts": [
                localized_text(locale, ru="Какую фразу вы будете использовать вместо сухого 'ожидайте'?", en="What phrase will you use instead of a dry 'please wait'?"),
                localized_text(locale, ru="Как вы проверите, что обещание в ответе действительно находится в вашей зоне контроля?", en="How will you verify that a promise in your response is really within your control?"),
            ],
        },
        "complaints": {
            "signals_intro": localized_text(
                locale,
                ru="Жалоба становится управляемой, когда разговор получает структуру. Пока структура не появилась, даже правильное решение может прозвучать как оборона или формальность.",
                en="A complaint becomes manageable when the conversation gains structure. Until that structure appears, even the right solution can sound defensive or formulaic.",
            ),
            "mistakes": [
                localized_text(locale, ru="Переходить к защите процесса раньше, чем клиент увидел, что вы поняли саму проблему.", en="Defend the process before the client sees that you understood the issue itself."),
                localized_text(locale, ru="Пропускать этап переформулировки и уточнения, из-за чего разговор крутится по кругу.", en="Skip restating and clarifying, which makes the conversation loop endlessly."),
                localized_text(locale, ru="Предлагать решение до проверки ожиданий, влияния и ограничений.", en="Offer a resolution before checking expectations, impact, and constraints."),
            ],
            "coach_tip": localized_text(
                locale,
                ru="Если после вашего ответа клиенту не нужно повторять проблему второй раз, значит структура разговора уже работает.",
                en="If the client does not need to restate the issue after your reply, the conversation structure is already working.",
            ),
            "action_prompts": [
                localized_text(locale, ru="Как вы покажете клиенту, что правильно услышали проблему, не повторяя его слова механически?", en="How will you show the client you understood the issue without parroting their exact words?"),
                localized_text(locale, ru="Какой шаг в обработке жалоб у вашей команды чаще всего пропускается?", en="Which step in complaint handling does your team skip most often?"),
            ],
        },
        "deescalation": {
            "signals_intro": localized_text(
                locale,
                ru="Деэскалация — это не мягкость ради мягкости, а возвращение разговора в предсказуемое русло. Здесь выигрывает тот, кто удерживает процесс, а не тот, кто отвечает быстрее или жестче.",
                en="De-escalation is not softness for its own sake; it is bringing the conversation back into a predictable path. The winner is the person who holds the process, not the one who responds fastest or hardest.",
            ),
            "mistakes": [
                localized_text(locale, ru="Зеркалить раздражение клиента и постепенно поднимать тон разговора.", en="Mirror the client's irritation and slowly escalate the tone."),
                localized_text(locale, ru="Читать политику вместо того, чтобы сначала зафиксировать факты и следующий шаг.", en="Read policy at the client instead of first grounding the facts and next step."),
                localized_text(locale, ru="Заканчивать ответ без нового контрольного момента, оставляя клиента в той же неопределенности.", en="End the reply with no new checkpoint, leaving the client in the same uncertainty."),
            ],
            "coach_tip": localized_text(
                locale,
                ru="Лучший индикатор деэскалации — клиент еще может быть недоволен, но разговор снова становится управляемым и конкретным.",
                en="The best indicator of de-escalation is that the client may still be unhappy, but the conversation becomes manageable and concrete again.",
            ),
            "action_prompts": [
                localized_text(locale, ru="Что поможет вам не зеркалить агрессию в следующем напряженном разговоре?", en="What will help you avoid mirroring aggression in the next tense conversation?"),
                localized_text(locale, ru="Какой один next step вы будете называть раньше, чтобы быстрее вернуть разговор в рабочее русло?", en="Which single next step will you name earlier to bring the conversation back on track faster?"),
            ],
        },
    }
    return profiles.get(
        topic_key,
        {
            "signals_intro": localized_text(
                locale,
                ru="Сильная практика здесь видна по ясному следующему шагу, понятному владельцу и отсутствию лишней импровизации.",
                en="Strong practice here is visible when the next step, the owner, and the rationale are all clear.",
            ),
            "mistakes": [
                localized_text(locale, ru="Действовать без понятного владельца вопроса.", en="Act without a clear owner for the issue."),
                localized_text(locale, ru="Оставлять решение только в устных договоренностях.", en="Leave the decision only in verbal agreements."),
                localized_text(locale, ru="Переходить дальше без проверки следующего шага.", en="Move forward without checking the next step."),
            ],
            "coach_tip": localized_text(
                locale,
                ru="Если человек может объяснить не только что делать, но и почему именно так, тема уже начинает работать в реальной практике.",
                en="If the learner can explain not only what to do but why that action matters, the topic is already landing in real work.",
            ),
            "action_prompts": [
                localized_text(locale, ru="Какой один новый рабочий ритуал вы добавите после этого урока?", en="Which one new work ritual will you add after this lesson?"),
                localized_text(locale, ru="Как вы поймете, что тема уже начала работать в вашей практике?", en="How will you know this topic has started working in your actual practice?"),
            ],
        },
    )


def lesson_profile(locale: str, image_key: str) -> dict[str, object]:
    if not is_russian(locale):
        return {}
    profiles = {
        "onboarding-org-roles": {
            "context_page_title": "Кто снимает какой блокер",
            "signals_page_title": "Как быстро выбрать правильного владельца",
            "practice_page_title": "Разведите один запрос на три адресата",
            "pitfalls_page_title": "Где новички теряют время в первую неделю",
            "apply_page_title": "Соберите свою карту ролей",
            "signals_intro": "В этой теме полезнее всего научиться за тридцать секунд отвечать на вопрос: это разговор с руководителем, наставником, HR, IT или ИБ. Чем быстрее человек отделяет роли друг от друга, тем меньше шума и лишних копий в переписке.",
            "mistakes": [
                "Писать в общий чат, потому что так кажется быстрее, вместо адресного запроса владельцу процесса.",
                "Сначала идти к самому доступному человеку, а не к тому, кто реально принимает решение или снимает блокер.",
                "Смешивать кадровый вопрос, техническую проблему и ожидания от руководителя в одно длинное сообщение.",
            ],
            "coach_tip": "Если новичок может объяснить, почему один вопрос он несет в HR, а другой в IT, значит карта ролей уже превратилась в рабочее поведение.",
            "action_prompts": [
                "Как вы визуально покажете новому сотруднику разницу между владельцем процесса и человеком, который просто помогает с адаптацией?",
                "Какие три маршрута эскалации вы закрепили бы у команды уже в первый день?",
            ],
            "template_lines": [
                "Блокер: ...",
                "Кому пишу первым: ...",
                "Кого ставлю в копию: ...",
                "Когда повышаю уровень: ...",
            ],
        },
        "onboarding-portal": {
            "context_page_title": "Где искать утвержденную информацию",
            "signals_page_title": "Как отличить актуальную инструкцию от старой",
            "practice_page_title": "Проверьте политику до отправки заявки",
            "pitfalls_page_title": "Что ломает работу, если жить по скринам из чата",
            "apply_page_title": "Настройте свой маршрут по порталу",
            "signals_intro": "Портал ценен не количеством страниц, а тем, что на него можно сослаться как на утвержденный источник. Если команда продолжает жить скринами, файлами из переписки и пересказами, портал формально есть, но управляемости не добавляет.",
            "mistakes": [
                "Верить скрину из старой переписки, не проверяя дату версии и владельца страницы.",
                "Хранить у себя личную копию шаблона и не замечать, что в портале уже опубликована новая редакция.",
                "Обходить встроенный путь подачи заявки и решать типовой запрос через личные сообщения знакомому сотруднику.",
            ],
            "coach_tip": "Хороший маркер зрелости — сотрудник не просто знает, что портал существует, а умеет быстро проверить там актуальность документа и владельца процесса.",
            "action_prompts": [
                "Какие две темы в вашей команде сильнее всего выиграли бы, если бы все перестали пересылать старые скрины и начали ссылаться на портал?",
                "Какие страницы портала вы бы закрепили как обязательные для первого дня и первой недели?",
            ],
            "template_lines": [
                "Документ или процесс: ...",
                "Где проверяю актуальность: ...",
                "Кто владелец страницы: ...",
                "Какой запрос оформляю через портал: ...",
            ],
        },
        "onboarding-task-tracker": {
            "context_page_title": "Когда чат уже не справляется",
            "signals_page_title": "Что обязательно должно быть видно в карточке задачи",
            "practice_page_title": "Разберите переписку, которую пора превратить в задачу",
            "pitfalls_page_title": "Почему работа теряется между сообщениями",
            "apply_page_title": "Соберите минимальный стандарт задачи",
            "signals_intro": "Этот урок не о том, что чат 'плохой'. Он о границе, после которой переписка перестает удерживать договоренность: появляется срок, владелец, зависимость или внешний риск, и без карточки задача начинает расползаться.",
            "mistakes": [
                "Оставлять решение только в треде, где через день уже невозможно быстро найти итоговую договоренность.",
                "Не назначать владельца, потому что 'и так понятно, кто делает', а потом спорить, кто должен был двигать задачу.",
                "Считать, что дедлайн можно держать в голове команды, а не в карточке с проверяемым статусом.",
            ],
            "coach_tip": "Сильная команда не переносит в трекер все подряд; она хорошо чувствует момент, когда переписка уже не гарантирует исполнение.",
            "action_prompts": [
                "Какая договоренность в вашей текущей работе чаще всего остается только в мессенджере, хотя давно должна жить в трекере?",
                "Какие три поля карточки задачи вы считаете обязательными без исключений?",
            ],
            "template_lines": [
                "Результат задачи: ...",
                "Владелец: ...",
                "Дедлайн: ...",
                "Откуда взялась договоренность: ...",
            ],
        },
        "onboarding-business-message": {
            "context_page_title": "Сообщение, на которое можно ответить за минуту",
            "signals_page_title": "Как сделать запрос понятным с первого чтения",
            "practice_page_title": "Перепишите расплывчатое сообщение",
            "pitfalls_page_title": "Какие формулировки тормозят ответ",
            "apply_page_title": "Соберите шаблон сильного сообщения",
            "signals_intro": "Сила делового сообщения в том, что адресату не нужно догадываться, чего от него ждут. Чем быстрее он понимает контекст, действие и срок, тем меньше лишних циклов уточнений и переспросов.",
            "mistakes": [
                "Начинать с эмоции или срочности, но не давать человеку опорных фактов и ссылки на материал.",
                "Прятать реальный вопрос в середину длинного текста, где его легко пропустить.",
                "Ставить дедлайн только в голове или на созвоне, не фиксируя его прямо в сообщении.",
            ],
            "coach_tip": "Если сообщение можно безопасно переслать дальше без дополнительного комментария, значит в нем уже достаточно контекста и ясности.",
            "action_prompts": [
                "Какие два элемента вы будете всегда проверять перед отправкой срочного сообщения руководителю или смежной команде?",
                "Как сократить ваш следующий запрос так, чтобы человек понял его без второго прочтения?",
            ],
            "template_lines": [
                "Контекст: ...",
                "Что нужно от адресата: ...",
                "Почему это важно сейчас: ...",
                "До какого времени нужен ответ: ...",
            ],
        },
        "onboarding-escalation": {
            "context_page_title": "Когда проблему уже пора поднимать выше",
            "signals_page_title": "Какие сигналы говорят, что время эскалировать",
            "practice_page_title": "Соберите сообщение без паники",
            "pitfalls_page_title": "Что делает эскалацию бесполезной",
            "apply_page_title": "Подготовьте свой early-warning сценарий",
            "signals_intro": "Хорошая эскалация нужна не тогда, когда все уже сорвалось, а когда еще можно защитить срок и снять блокер. Поэтому ключ к теме — не драматичность, а своевременность и ясная структура сообщения.",
            "mistakes": [
                "Ждать идеальной уверенности в причине проблемы, хотя уже понятно, что срок или обязательство под риском.",
                "Писать эмоционально и общими словами вместо статуса, влияния и конкретной просьбы о помощи.",
                "Не показывать, что уже пробовали, и тем самым заставлять следующего владельца повторять тот же круг действий.",
            ],
            "coach_tip": "Сильная эскалация экономит время другой стороне на входе в проблему. Если человек быстро понимает риск и нужное действие, сообщение сработало.",
            "action_prompts": [
                "По каким двум признакам вы поймете, что напоминание уже не помогает и пора повышать уровень?",
                "Какой минимальный набор полей должен быть у любой эскалации в вашей команде?",
            ],
            "template_lines": [
                "Статус сейчас: ...",
                "Что блокирует срок или обязательство: ...",
                "Что уже пробовали: ...",
                "Какой помощи ждем: ...",
            ],
        },
        "security-passwords": {
            "context_page_title": "Какие привычки реально защищают аккаунт",
            "signals_page_title": "Как выглядит зрелая работа с доступом",
            "practice_page_title": "Разберите просьбу «скинь код на минуту»",
            "pitfalls_page_title": "Где парольная дисциплина ломается первой",
            "apply_page_title": "Соберите свой безопасный ритуал доступа",
            "signals_intro": "Парольная безопасность обычно ломается не на сложной атаке, а на бытовой уступке: скинуть код, сохранить пароль вне менеджера, использовать один и тот же секрет там, где 'не так важно'. Поэтому эта тема про рутину, а не про героизм.",
            "mistakes": [
                "Передавать одноразовый код или пароль как дружеское одолжение, считая это маленьким исключением.",
                "Хранить рабочие доступы в заметках, скринах или переписке, потому что так удобнее зайти с другого устройства.",
                "Рассматривать MFA как помеху, а не как последний барьер между человеком и чужим входом в систему.",
            ],
            "coach_tip": "Если человек умеет быстро объяснить, что делать вместо передачи кода коллеге, тема усвоена лучше, чем при простом знании правил на словах.",
            "action_prompts": [
                "Какая часть вашего текущего ритуала входа толкает к shortcut'ам и как ее убрать без потери скорости?",
                "Какой сценарий восстановления доступа должен быть у команды понятен всем, чтобы не возникало соблазна делиться кодами?",
            ],
            "template_lines": [
                "Система: ...",
                "Как защищен вход: ...",
                "Где хранится пароль: ...",
                "Что делаю, если кто-то просит код: ...",
            ],
        },
        "security-password-reuse": {
            "context_page_title": "Как локальная утечка становится корпоративной",
            "signals_page_title": "По каким признакам видно повторное использование",
            "practice_page_title": "Оцените цепочку ущерба после утечки",
            "pitfalls_page_title": "Какие оправдания толкают к повтору",
            "apply_page_title": "Выберите, что менять в первую очередь",
            "signals_intro": "Повторный пароль редко выглядит опасно до первого инцидента. Но как только одна внешняя утечка совпадает с рабочей системой, личная привычка превращается в организационный риск с очень коротким плечом атаки.",
            "mistakes": [
                "Использовать знакомый 'слегка измененный' пароль и считать, что это уже другой секрет.",
                "Оставлять повторный пароль в критичной системе только потому, что до нее неудобно дотянуться менеджером паролей.",
                "Недооценивать скорость, с которой credential stuffing превращает старую утечку в новый инцидент.",
            ],
            "coach_tip": "Урок считается освоенным не тогда, когда человек знает термин credential stuffing, а когда он может показать, где именно у него раньше возникал соблазн повторить пароль.",
            "action_prompts": [
                "Какие аккаунты вы бы проверили первыми, если бы узнали об утечке одного из своих паролей сегодня?",
                "Где в вашей среде повтор пароля принес бы самый дорогой ущерб и почему именно там?",
            ],
            "template_lines": [
                "Где утек пароль: ...",
                "Какие рабочие системы под риском: ...",
                "Что меняю сразу: ...",
                "Что проверяю затем: ...",
            ],
        },
        "security-phishing": {
            "context_page_title": "Где письмо перестает быть обычным",
            "signals_page_title": "Какие сигналы надо проверить перед кликом",
            "practice_page_title": "Разберите письмо с ложной срочностью",
            "pitfalls_page_title": "На чем чаще всего ловят внимательных людей",
            "apply_page_title": "Соберите свой антифишинговый стоп-лист",
            "signals_intro": "Фишинг работает не потому, что человек невнимателен всегда, а потому, что письмо похоже на нормальный рабочий поток и торопит принять решение без паузы. Поэтому задача — не найти 'странность вообще', а быстро проверить несколько конкретных сигналов.",
            "mistakes": [
                "Доверять знакомому бренду или тону письма и не смотреть на домен отправителя и реальный адрес ссылки.",
                "Открывать вложение в момент срочности, а проверку делать уже после первого клика.",
                "Отправлять подозрительное письмо в обычный рабочий чат вместо защищенного канала проверки.",
            ],
            "coach_tip": "Лучший навык здесь — поставить себе микропаузу на пару секунд и проверить домен, прежде чем делать что-либо с письмом.",
            "action_prompts": [
                "Какие два сигнала в письме вы обязуетесь проверять первыми даже в состоянии спешки?",
                "Какой путь сообщения о подозрительном письме должен быть у вас буквально под рукой?",
            ],
            "template_lines": [
                "От кого пришло письмо: ...",
                "Какой домен вижу: ...",
                "Куда ведет ссылка: ...",
                "Куда отправляю на проверку: ...",
            ],
        },
        "security-confidential-files": {
            "context_page_title": "Когда удобная пересылка становится риском",
            "signals_page_title": "Что надо проверить перед отправкой файла",
            "practice_page_title": "Разберите доступ к конфиденциальному документу",
            "pitfalls_page_title": "Какие привычки создают лишние копии и лишние доступы",
            "apply_page_title": "Соберите правила безопасной передачи файла",
            "signals_intro": "В этой теме важен не только сам файл, но и весь маршрут его жизни: где лежит оригинал, кто получит ссылку, останется ли лишняя копия и как быстро можно отозвать доступ. Именно на этих мелочах и строится реальная защита данных.",
            "mistakes": [
                "Пересылать файл через удобный, но неутвержденный канал, чтобы 'не задерживать коллегу'.",
                "Давать доступ шире, чем требуется, и надеяться, что получатель сам не поделится ссылкой дальше.",
                "Оставлять на локальном диске или в мессенджере копии, которые уже не нужны после отправки официальной версии.",
            ],
            "coach_tip": "Самый полезный вопрос перед отправкой — не 'можно ли открыть файл', а 'кто увидит его после меня и можно ли быстро отозвать доступ'.",
            "action_prompts": [
                "Какой тип файлов в вашей работе чаще всего отправляют 'по-быстрому' и что нужно изменить в этом ритуале?",
                "Какая проверка перед шарингом должна стать обязательной для всей команды?",
            ],
            "template_lines": [
                "Файл или папка: ...",
                "Кому нужен доступ: ...",
                "На какой срок: ...",
                "Как отзываю доступ и удаляю лишние копии: ...",
            ],
        },
        "security-incident-response": {
            "context_page_title": "Что считать сигналом инцидента",
            "signals_page_title": "Какие первые действия помогают, а не вредят",
            "practice_page_title": "Отработайте первые десять минут после тревоги",
            "pitfalls_page_title": "Почему люди тянут с сообщением о проблеме",
            "apply_page_title": "Соберите свой сценарий первого сообщения",
            "signals_intro": "Самая дорогая ошибка после тревожного сигнала — ждать стопроцентной уверенности. В первые минуты важнее сохранить детали и дать команде ИБ ранний, но качественный сигнал, чем самостоятельно строить идеальную версию случившегося.",
            "mistakes": [
                "Сначала пытаться тайно 'починить' ситуацию, а уже потом думать, нужно ли кому-то сообщать.",
                "Удалять письмо, событие или лог, потому что хочется убрать проблему с глаз и не поднимать шум.",
                "Тянуть до конца рабочего дня, хотя уже понятно, что произошло подозрительное действие или вход.",
            ],
            "coach_tip": "Хороший первый ответ на инцидент — это минимум паники и максимум фактов: где, когда, что увидели и что уже успели сделать.",
            "action_prompts": [
                "Какое первое сообщение вы отправите, если прямо сейчас увидите подозрительный вход или массовую рассылку от своего имени?",
                "Как вы поможете себе не скрывать инцидент в момент стресса, а сразу перевести его в правильный канал?",
            ],
            "template_lines": [
                "Когда заметил событие: ...",
                "В какой системе: ...",
                "Что именно увидел: ...",
                "Что успел сделать до сообщения: ...",
            ],
        },
        "service-request-ownership": {
            "context_page_title": "Кто отвечает перед клиентом прямо сейчас",
            "signals_page_title": "Как выглядит видимое владение кейсом",
            "practice_page_title": "Разберите передачу запроса между командами",
            "pitfalls_page_title": "Почему кейс зависает даже без технической ошибки",
            "apply_page_title": "Соберите стандарт апдейта клиенту",
            "signals_intro": "Для клиента 'владеет кейсом' означает не внутреннюю структуру команд, а очень простой опыт: есть ли человек, который держит следующий шаг и вернется с обновлением. Если этого не видно, тишина воспринимается как потеря контроля.",
            "mistakes": [
                "Считать, что после передачи в другую очередь ответственность за коммуникацию автоматически исчезает.",
                "Не называть клиенту следующий контрольный момент, пока команда внутри еще разбирается, кто дальше ведет кейс.",
                "Давать несколько частичных ответов от разных людей вместо одного понятного владельца и маршрута.",
            ],
            "coach_tip": "Владение кейсом видно не по громким обещаниям, а по тому, что клиент всегда понимает, кто его следующий контакт и когда ждать обновление.",
            "action_prompts": [
                "Какая точка передачи запроса у вашей команды чаще всего размывает владельца перед глазами клиента?",
                "Какой минимум информации должен получать клиент при любом роутинге кейса между командами?",
            ],
            "template_lines": [
                "Текущий владелец кейса: ...",
                "Почему нужен роутинг: ...",
                "Когда клиент получит апдейт: ...",
                "Кто контролирует следующий шаг: ...",
            ],
        },
        "service-empathy": {
            "context_page_title": "Как звучит сочувствие без пустых обещаний",
            "signals_page_title": "Какие формулировки снижают напряжение",
            "practice_page_title": "Перепишите ответ раздраженному клиенту",
            "pitfalls_page_title": "Где эмпатия превращается в раздражающий шаблон",
            "apply_page_title": "Соберите честный и теплый ответ",
            "signals_intro": "Эмпатия в сервисе нужна не для украшения фразы, а для того, чтобы клиент увидел: вы поняли влияние проблемы на него и не прячетесь за процедурой. Но если за сочувствием не идет реальный шаг, оно быстро начинает раздражать.",
            "mistakes": [
                "Использовать заученные фразы вроде 'понимаем ваше неудобство', не связывая их с конкретной проблемой клиента.",
                "Обещать скорость или результат, которые ваша команда не контролирует, только чтобы временно снизить напряжение.",
                "Пытаться звучать сочувственно, но одновременно уходить в оборону и объяснения, почему случилась задержка.",
            ],
            "coach_tip": "Сильная сервисная эмпатия всегда опирается на факт: что именно затронуло клиента и какой следующий проверяемый шаг вы берете на себя.",
            "action_prompts": [
                "Какая фраза в вашей переписке звучит вежливо, но на деле ничего не объясняет и не двигает разговор?",
                "Как вы покажете клиенту, что услышали именно его риск или неудобство, а не просто вставили шаблон?",
            ],
            "template_lines": [
                "Что именно затронуло клиента: ...",
                "Как это признаю в ответе: ...",
                "Какой реальный следующий шаг беру: ...",
                "Когда вернусь с апдейтом: ...",
            ],
        },
        "service-complaints": {
            "context_page_title": "Как дать жалобе структуру",
            "signals_page_title": "Какие этапы должен пройти разговор",
            "practice_page_title": "Разберите жалобу от первого ответа до фиксации решения",
            "pitfalls_page_title": "Что заставляет клиента повторять проблему снова",
            "apply_page_title": "Соберите опорный сценарий обработки жалобы",
            "signals_intro": "Жалоба становится управляемой, когда разговор перестает быть хаотичным: вы подтверждаете понимание, уточняете влияние, обозначаете ограничения и только потом переходите к решению. Если этот ритм нарушен, клиенту приходится объяснять проблему заново.",
            "mistakes": [
                "Сразу защищать процесс или политику, не показав, что вы сначала поняли саму суть жалобы.",
                "Перепрыгивать этап уточнения и предлагать решение, не проверив ожидания и влияние на клиента.",
                "Не фиксировать итог разговора, из-за чего следующему сотруднику клиент снова рассказывает историю с нуля.",
            ],
            "coach_tip": "Если после вашего ответа клиенту не нужно второй раз формулировать исходную проблему, значит структура разговора уже начинает работать.",
            "action_prompts": [
                "Какая часть обработки жалоб у вашей команды чаще всего выпадает — подтверждение понимания, уточнение влияния или фиксация решения?",
                "Как вы дадите клиенту увидеть, что разговор не обнуляется при передаче кейса дальше?",
            ],
            "template_lines": [
                "Что произошло по версии клиента: ...",
                "Какое влияние это создало: ...",
                "Какие ограничения нужно честно озвучить: ...",
                "Что фиксируем как следующий шаг: ...",
            ],
        },
        "service-deescalation": {
            "context_page_title": "Как вернуть разговор в рабочее русло",
            "signals_page_title": "Какие сигналы показывают, что конфликт растет",
            "practice_page_title": "Отработайте ответ на повышенный тон",
            "pitfalls_page_title": "Что чаще всего рушит деэскалацию",
            "apply_page_title": "Соберите свой нейтральный сценарий ответа",
            "signals_intro": "Деэскалация не делает разговор мягким любой ценой. Она возвращает управляемость: меньше взаимных оценок, больше фактов, один следующий шаг и понятный контрольный момент. Именно за это клиент и цепляется, даже если все еще недоволен.",
            "mistakes": [
                "Зеркалить скорость и резкость клиента, потому что хочется немедленно отстоять свою позицию.",
                "Отвечать длинной ссылкой на политику до того, как вы собрали разговор обратно в факты и следующий шаг.",
                "Заканчивать разговор без нового checkpoint, оставляя клиента в той же неопределенности, с которой он пришел.",
            ],
            "coach_tip": "Хорошая деэскалация заметна по тому, что разговор становится конкретнее, даже если эмоция пока не ушла полностью.",
            "action_prompts": [
                "Какая короткая фраза помогает вам не зеркалить агрессию и вернуть разговор к фактам?",
                "Какой следующий шаг вы будете называть раньше, чтобы быстрее снижать напряжение?",
            ],
            "template_lines": [
                "Что я услышал от клиента: ...",
                "Что подтверждаю как факт: ...",
                "Какой следующий шаг называю: ...",
                "Когда обещаю следующий контакт: ...",
            ],
        },
        "service-overdue-escalation": {
            "context_page_title": "Когда просрочка уже требует усиления",
            "signals_page_title": "Как показать риск другой команде и клиенту",
            "practice_page_title": "Соберите эскалацию по просроченному кейсу",
            "pitfalls_page_title": "Почему срочная просьба без фактов не работает",
            "apply_page_title": "Подготовьте шаблон для overdue-кейсов",
            "signals_intro": "Просрочка опасна не самим фактом опоздания, а тем, что без правильной эскалации она начинает множить ущерб: клиенту неясно, кто управляет риском, а смежная команда не понимает, почему кейс нужно брать сейчас. Поэтому нужен короткий и очень фактический язык риска.",
            "mistakes": [
                "Писать 'нужно срочно помочь', не показывая, какой срок уже под угрозой и что это меняет для клиента.",
                "Поднимать вопрос слишком поздно, когда у другой команды уже не остается пространства на маневр.",
                "Эскалировать только внутрь, но не обновлять клиента о том, что риск признан и уже управляется.",
            ],
            "coach_tip": "Сильная overdue-эскалация объясняет риск без драматизации: что срывается, для кого это важно и какой шаг нужен прямо сейчас.",
            "action_prompts": [
                "Какие два факта вы будете ставить в начало сообщения о просроченном кейсе, чтобы другая команда сразу поняла риск?",
                "Как вы покажете клиенту, что просрочка не игнорируется, а уже управляется по понятному сценарию?",
            ],
            "template_lines": [
                "Что уже просрочено или под риском: ...",
                "Как это влияет на клиента или обязательство: ...",
                "Что уже сделано командой: ...",
                "Какая помощь нужна прямо сейчас: ...",
            ],
        },
    }
    return profiles.get(image_key, {})


def derived_common_mistakes(locale: str, topic_key: str, checklist: list[str]) -> list[str]:
    profile = topic_profile(locale, topic_key)
    mistakes = list(profile["mistakes"])[:3]
    if checklist:
        mistakes.append(
            localized_text(
                locale,
                ru=f"Идти дальше, не проверив ключевой маркер готовности: {checklist[0].rstrip('?')}.",
                en=f"Move on without checking the readiness marker: {checklist[0].rstrip('?')}.",
            )
        )
    return mistakes


def derived_action_prompts(locale: str, topic_key: str, reflection: str) -> list[str]:
    profile = topic_profile(locale, topic_key)
    return [*list(profile["action_prompts"])[:2], reflection]


def resolved_lesson_profile(
    *,
    locale: str,
    topic_key: str,
    image_key: str,
    checklist: list[str],
    reflection: str,
) -> dict[str, object]:
    topic = topic_profile(locale, topic_key)
    lesson = lesson_profile(locale, image_key)
    ru = is_russian(locale)
    return {
        "signals_intro": lesson.get("signals_intro", str(topic["signals_intro"])),
        "mistakes": lesson.get("mistakes", derived_common_mistakes(locale, topic_key, checklist)),
        "coach_tip": lesson.get("coach_tip", str(topic["coach_tip"])),
        "action_prompts": lesson.get("action_prompts", derived_action_prompts(locale, topic_key, reflection)),
        "context_page_title": lesson.get("context_page_title", "Зачем изучать этот урок" if ru else "Why this lesson matters"),
        "signals_page_title": lesson.get("signals_page_title", "Как тема проявляется в работе" if ru else "How the topic shows up at work"),
        "practice_page_title": lesson.get("practice_page_title", "Разберите мини-кейс" if ru else "Work through the mini case"),
        "pitfalls_page_title": lesson.get("pitfalls_page_title", "Что чаще всего ломает результат" if ru else "What most often breaks the outcome"),
        "apply_page_title": lesson.get("apply_page_title", "Что закрепить перед следующим шагом" if ru else "What to lock in before the next step"),
        "template_lines": lesson.get(
            "template_lines",
            [
                "Контекст: ...",
                "Что уже сделано: ...",
                "Нужное действие: ...",
                "Срок: ...",
            ]
            if ru
            else [
                "Context: ...",
                "What is already done: ...",
                "Action needed: ...",
                "Deadline: ...",
            ],
        ),
    }


def html_list(items: list[str], *, ordered: bool = False) -> str:
    tag = "ol" if ordered else "ul"
    return f"<{tag}>" + "".join(f"<li>{escape(item)}</li>" for item in items) + f"</{tag}>"
def lesson_content(
    *,
    locale: str,
    topic_key: str,
    image_key: str,
    why_it_matters: str,
    practice: list[str],
    scenario: str,
    checklist: list[str],
    reflection: str,
) -> str:
    ru = is_russian(locale)
    profile = resolved_lesson_profile(
        locale=locale,
        topic_key=topic_key,
        image_key=image_key,
        checklist=checklist,
        reflection=reflection,
    )
    common_mistakes = list(profile["mistakes"])
    next_actions = list(profile["action_prompts"])
    sections = [
        (
            "## Цель урока\nПонять тему так, чтобы применить ее в реальной рабочей ситуации."
            if ru
            else "## Lesson goal\nUnderstand the topic well enough to use it in a real workplace situation."
        ),
        f"{'## Почему это важно' if ru else '## Why this matters'}\n{why_it_matters}",
        f"{'## Как тема проявляется в работе' if ru else '## How the topic shows up at work'}\n{profile['signals_intro']}",
        f"{'## Как выглядит хорошая практика' if ru else '## What good practice looks like'}\n" + "\n".join(f"- {item}" for item in practice),
        f"{'## Рабочий сценарий' if ru else '## Workplace scenario'}\n{scenario}",
        f"{'## Типичные ошибки' if ru else '## Common mistakes'}\n" + "\n".join(f"- {item}" for item in common_mistakes),
        f"{'## Чек-лист перед продолжением' if ru else '## Checklist before you continue'}\n" + "\n".join(f"- {item}" for item in checklist),
        f"{'## Что взять в работу сразу' if ru else '## What to apply immediately'}\n" + "\n".join(f"- {item}" for item in next_actions),
        f"{'## Вопрос для рефлексии' if ru else '## Reflection prompt'}\n{reflection}",
    ]
    return "\n\n".join(sections)


def lesson_pages(
    *,
    locale: str,
    topic_key: str,
    image_key: str,
    title: str,
    summary: str,
    image_url: str,
    video_url: str,
    why_it_matters: str,
    practice: list[str],
    scenario: str,
    checklist: list[str],
    reflection: str,
) -> list[dict]:
    ru = is_russian(locale)
    profile = resolved_lesson_profile(
        locale=locale,
        topic_key=topic_key,
        image_key=image_key,
        checklist=checklist,
        reflection=reflection,
    )
    common_mistakes = list(profile["mistakes"])
    action_prompts = list(profile["action_prompts"])
    context_label = "Контекст" if ru else "Context"
    why_label = str(profile["context_page_title"])
    signals_label = "Ключевые ориентиры" if ru else "Operational cues"
    signals_title = str(profile["signals_page_title"])
    practice_label = "Практика" if ru else "Guided practice"
    practice_title = str(profile["practice_page_title"])
    pitfalls_label = "Риски и ошибки" if ru else "Pitfalls and risks"
    pitfalls_title = str(profile["pitfalls_page_title"])
    apply_label = "Применение и выводы" if ru else "Apply and reflect"
    apply_title = str(profile["apply_page_title"])
    summary_html = (
        f"<h2>{'Коротко о теме' if ru else 'At a glance'}</h2>"
        f"<p>{escape(summary)}</p>"
        f"<p>{escape(why_it_matters)}</p>"
    )
    practice_items_html = html_list(practice)
    checklist_items_html = html_list(checklist, ordered=True)
    common_mistakes_html = html_list(common_mistakes)
    action_prompts_html = html_list(action_prompts)
    template_html = "<pre><code>" + escape("\n".join(str(item) for item in profile["template_lines"])) + "</code></pre>"
    decision_map_html = (
        f"<h2>{'На что смотреть в ежедневной работе' if ru else 'What to look for in daily work'}</h2>"
        f"<p>{escape(str(profile['signals_intro']))}</p>"
        f"<div><h3>{'Признаки сильной практики' if ru else 'Signals of strong practice'}</h3>{practice_items_html}</div>"
        f"<div><h3>{'Что должно быть видно в системе или коммуникации' if ru else 'What should be visible in systems or communication'}</h3>{checklist_items_html}</div>"
    )
    scenario_lab_html = (
        f"<h2>{'Мини-кейс' if ru else 'Mini case'}</h2>"
        f"<p>{escape(scenario)}</p>"
        f"<h3>{'Рекомендуемая последовательность действий' if ru else 'Recommended sequence'}</h3>"
        f"{html_list(practice[:3], ordered=True)}"
        f"<h3>{'Что стоит зафиксировать сразу' if ru else 'What to record immediately'}</h3>"
        f"{template_html}"
    )
    risk_page_html = (
        f"<h2>{'Типичные ошибки' if ru else 'Common mistakes'}</h2>"
        f"{common_mistakes_html}"
        f"<h3>{'Подсказка для руководителя или наставника' if ru else 'Manager or mentor tip'}</h3>"
        f"<p>{escape(str(profile['coach_tip']))}</p>"
    )
    apply_html = (
        f"<h2>{'Чек-лист перед следующим шагом' if ru else 'Checklist before the next step'}</h2>"
        f"{checklist_items_html}"
        f"<h3>{'Мини-самопроверка' if ru else 'Mini self-check'}</h3>"
        f"{action_prompts_html}"
        f"<blockquote><strong>{'Вопрос для рефлексии' if ru else 'Reflection prompt'}:</strong> {escape(reflection)}</blockquote>"
    )
    return [
        {
            "page_id": f"{title.lower().replace(' ', '-')}-context",
            "chapter_title": context_label,
            "page_title": why_label,
            "blocks": [
                {"type": "html", "html": summary_html},
                {"type": "image", "url": image_url, "alt": title},
                {"type": "video", "url": video_url, "title": f"{title}: {'разбор' if ru else 'walkthrough'}"},
            ],
        },
        {
            "page_id": f"{title.lower().replace(' ', '-')}-signals",
            "chapter_title": signals_label,
            "page_title": signals_title,
            "blocks": [{"type": "html", "html": decision_map_html}],
        },
        {
            "page_id": f"{title.lower().replace(' ', '-')}-practice",
            "chapter_title": practice_label,
            "page_title": practice_title,
            "blocks": [{"type": "html", "html": scenario_lab_html}],
        },
        {
            "page_id": f"{title.lower().replace(' ', '-')}-pitfalls",
            "chapter_title": pitfalls_label,
            "page_title": pitfalls_title,
            "blocks": [{"type": "html", "html": risk_page_html}],
        },
        {
            "page_id": f"{title.lower().replace(' ', '-')}-apply",
            "chapter_title": apply_label,
            "page_title": apply_title,
            "blocks": [{"type": "html", "html": apply_html}],
        },
    ]


def lesson_seed(
    *,
    locale: str = "en",
    topic_key: str,
    title: str,
    summary: str,
    image_key: str,
    video_url: str,
    duration_minutes: int,
    why_it_matters: str,
    practice: list[str],
    scenario: str,
    checklist: list[str],
    reflection: str,
) -> LessonSeed:
    topic_key = repair_mojibake_text(topic_key)
    title = repair_mojibake_text(title)
    summary = repair_mojibake_text(summary)
    why_it_matters = repair_mojibake_text(why_it_matters)
    scenario = repair_mojibake_text(scenario)
    reflection = repair_mojibake_text(reflection)
    practice = [repair_mojibake_text(item) for item in practice]
    checklist = [repair_mojibake_text(item) for item in checklist]
    image_url = lesson_image(image_key, locale)
    video_url = lesson_video(image_key, locale)
    return LessonSeed(
        topic_key=topic_key,
        title=title,
        summary=summary,
        content=lesson_content(
            locale=locale,
            topic_key=topic_key,
            image_key=image_key,
            why_it_matters=why_it_matters,
            practice=practice,
            scenario=scenario,
            checklist=checklist,
            reflection=reflection,
        ),
        content_pages=lesson_pages(
            locale=locale,
            topic_key=topic_key,
            image_key=image_key,
            title=title,
            summary=summary,
            image_url=image_url,
            video_url=video_url,
            why_it_matters=why_it_matters,
            practice=practice,
            scenario=scenario,
            checklist=checklist,
            reflection=reflection,
        ),
        image_url=image_url,
        video_url=video_url,
        duration_minutes=duration_minutes,
    )


def localized_cover_path(course_title: str, locale: str) -> str:
    suffix = "ru" if is_russian(locale) else "en"
    normalized = repair_mojibake_text(course_title).lower()
    if "онбординг" in normalized or "onboarding" in normalized:
        return f"/media/onboarding-cover-{suffix}.png"
    if "безопас" in normalized or "security" in normalized:
        return f"/media/security-cover-{suffix}.png"
    return f"/media/service-cover-{suffix}.png"


def extra_onboarding_questions(locale: str) -> list[QuestionSeed]:
    return [
        localized_question_seed(
            locale=locale,
            topic_key="org",
            difficulty=1,
            text_ru="К кому лучше идти с вопросом по отпуску, больничному или кадровым документам?",
            text_en="Who should usually handle questions about leave, sick days, or employment documents?",
            explanation_ru="Кадровые документы и льготы обычно находятся в зоне HR.",
            explanation_en="Employment documents and benefits are usually handled by HR.",
            options_ru=[("К HR", True), ("К внешнему подрядчику", False), ("К любому коллеге из соседней команды", False)],
            options_en=[("HR", True), ("An external vendor", False), ("Any colleague from another team", False)],
        ),
        localized_question_seed(
            locale=locale,
            topic_key="tools",
            difficulty=2,
            text_ru="Что лучше сделать после решения, принятого в рабочем чате?",
            text_en="What is the best follow-up after a decision is made in a work chat?",
            explanation_ru="Важные решения нужно закреплять в управляемой системе, а не оставлять только в переписке.",
            explanation_en="Important decisions should be captured in a managed system, not left only in chat history.",
            options_ru=[("Зафиксировать решение в задаче или комментарии", True), ("Ничего не делать, если все поняли устно", False), ("Переслать сообщение в личный чат себе и на этом остановиться", False)],
            options_en=[("Capture the decision in the task or its comments", True), ("Do nothing if everyone seemed to understand it verbally", False), ("Forward the chat message to yourself and stop there", False)],
        ),
        localized_question_seed(
            locale=locale,
            topic_key="comms",
            difficulty=2,
            text_ru="Какой элемент сильнее всего помогает получить быстрый ответ на рабочее сообщение?",
            text_en="Which element most improves the chance of a fast response to a work message?",
            explanation_ru="Когда адресат видит контекст, нужное действие и срок, он отвечает быстрее и точнее.",
            explanation_en="Responses are faster and better when the recipient sees the context, required action, and timing.",
            options_ru=[("Ясный контекст, конкретный запрос и срок", True), ("Только пометка «срочно» без деталей", False), ("Несколько пересланных скриншотов без объяснения", False)],
            options_en=[("Clear context, specific request, and timing", True), ("Only an 'urgent' label with no details", False), ("Several forwarded screenshots with no explanation", False)],
        ),
        localized_question_seed(
            locale=locale,
            topic_key="support",
            difficulty=3,
            text_ru="Что обязательно должно быть в хорошем сообщении об эскалации?",
            text_en="What should always be included in a good escalation message?",
            explanation_ru="Сильная эскалация содержит текущий статус, блокер, влияние и нужное действие.",
            explanation_en="A strong escalation includes current status, blocker, impact, and the requested action.",
            options_ru=[("Статус, блокер, влияние и запрос на помощь", True), ("Только эмоциональное описание того, что все идет плохо", False), ("Только номер задачи без контекста", False)],
            options_en=[("Status, blocker, impact, and requested help", True), ("Only an emotional description that everything is going badly", False), ("Only the task number with no context", False)],
        ),
        localized_question_seed(
            locale=locale,
            topic_key="org",
            difficulty=4,
            text_ru="У нового сотрудника сломался доступ к VPN и завтра контрольная встреча с руководителем. Что лучше сделать?",
            text_en="A new employee loses VPN access and has a manager check-in tomorrow. What is the best approach?",
            explanation_ru="Проблему с доступом нужно адресовать в IT, а ожидания по встрече синхронизировать с руководителем отдельно.",
            explanation_en="The access issue should go to IT, while expectations for the upcoming meeting should be aligned separately with the manager.",
            options_ru=[("Разделить запрос: IT для доступа, руководитель для приоритетов и ожиданий", True), ("Отправить один общий эмоциональный текст всем сразу", False), ("Подождать до завтра и надеяться, что доступ восстановится сам", False)],
            options_en=[("Split the requests: IT for access, manager for priorities and expectations", True), ("Send one emotional message to everyone at once", False), ("Wait until tomorrow and hope access returns on its own", False)],
        ),
        localized_question_seed(
            locale=locale,
            topic_key="tools",
            difficulty=5,
            text_ru="Какой подход лучше всего поддерживает управляемую внутреннюю работу команды?",
            text_en="Which approach best supports controlled internal team operations?",
            explanation_ru="Управляемая работа требует, чтобы правила, решения и статусы были видимы в утвержденных системах.",
            explanation_en="Controlled operations depend on policies, decisions, and statuses being visible in approved systems.",
            options_ru=[("Хранить важные решения, статусы и шаблоны в утвержденных системах", True), ("Полагаться на память команды и личные переписки", False), ("Сохранять критичные договоренности только в устном виде после созвона", False)],
            options_en=[("Keep important decisions, statuses, and templates in approved systems", True), ("Rely on team memory and private chats", False), ("Leave critical agreements only in verbal form after calls", False)],
            estimated_seconds=35,
        ),
    ]


def extra_security_questions(locale: str) -> list[QuestionSeed]:
    return [
        localized_question_seed(
            locale=locale,
            topic_key="passwords",
            difficulty=1,
            text_ru="Коллега просит ваш одноразовый код MFA, потому что ему нужно быстро проверить доступ. Что делать?",
            text_en="A colleague asks for your one-time MFA code so they can quickly test access. What should you do?",
            explanation_ru="Одноразовые коды — часть вашей аутентификации, их нельзя передавать даже из добрых намерений.",
            explanation_en="One-time codes are part of your authentication and should never be shared, even with good intentions.",
            options_ru=[("Не передавать код и предложить правильный путь через поддержку", True), ("Передать код один раз, если это срочно", False), ("Переслать код в общий чат, чтобы ускорить проверку", False)],
            options_en=[("Do not share the code and point them to the proper support path", True), ("Share the code once if it is urgent", False), ("Post the code in a team chat to speed up the check", False)],
        ),
        localized_question_seed(
            locale=locale,
            topic_key="phishing",
            difficulty=2,
            text_ru="В письме просят срочно открыть вложение, но домен отправителя не совпадает с обычным. Лучший первый шаг?",
            text_en="An email urges you to open an attachment, but the sender domain does not match the usual one. What is the best first step?",
            explanation_ru="Несовпадающий домен плюс срочность — сильный сигнал фишинга, сначала нужно проверить и сообщить по каналу безопасности.",
            explanation_en="A mismatched domain combined with urgency is a strong phishing signal, so verification and reporting come first.",
            options_ru=[("Не открывать вложение и отправить письмо на проверку по правилам ИБ", True), ("Открыть вложение на телефоне, чтобы проверить быстрее", False), ("Переслать письмо коллегам и спросить, выглядит ли оно нормально", False)],
            options_en=[("Do not open the attachment and submit the email through the security reporting path", True), ("Open it on your phone to check it faster", False), ("Forward it to coworkers and ask whether it looks normal", False)],
        ),
        localized_question_seed(
            locale=locale,
            topic_key="data",
            difficulty=3,
            text_ru="Что нужно проверить перед отправкой ссылки на конфиденциальный файл?",
            text_en="What should you verify before sending a link to a confidential file?",
            explanation_ru="Важно проверить и состав получателей, и права доступа, и то, что сама система одобрена для чувствительных данных.",
            explanation_en="You need to verify recipients, permissions, and that the platform itself is approved for sensitive data.",
            options_ru=[("Получателей, права доступа и одобренный канал хранения", True), ("Только то, что файл открывается у вас", False), ("Только название файла и дату создания", False)],
            options_en=[("Recipients, access permissions, and the approved storage channel", True), ("Only that the file opens correctly on your device", False), ("Only the file name and its creation date", False)],
        ),
        localized_question_seed(
            locale=locale,
            topic_key="incident",
            difficulty=3,
            text_ru="Почему после подозрительного события важно сохранить письмо, скриншот или время действия?",
            text_en="Why is it important to preserve the email, screenshot, or timestamp after a suspicious event?",
            explanation_ru="Эти данные помогают быстрее понять масштаб инцидента и сократить время на расследование.",
            explanation_en="Those details help responders understand the incident faster and reduce investigation time.",
            options_ru=[("Это сохраняет доказательства и ускоряет расследование", True), ("Это нужно только если уже точно произошла утечка", False), ("Это имеет значение только для внешнего аудита, а не для команды ИБ", False)],
            options_en=[("It preserves evidence and speeds up the investigation", True), ("It matters only if a leak is already confirmed", False), ("It matters only for external audit, not for the security team", False)],
        ),
        localized_question_seed(
            locale=locale,
            topic_key="passwords",
            difficulty=4,
            text_ru="Какой набор действий лучше всего снижает риск компрометации учетной записи?",
            text_en="Which combination best lowers the risk of account compromise?",
            explanation_ru="Самый сильный набор — уникальные пароли, MFA, менеджер паролей и отказ от шаринга доступа.",
            explanation_en="The strongest combination is unique passwords, MFA, a password manager, and no sharing of access.",
            options_ru=[("Уникальные пароли, MFA, менеджер паролей и запрет на шаринг", True), ("Длинный общий пароль команды и ежеквартальная смена", False), ("Один надежный пароль для почты и CRM, чтобы не забыть", False)],
            options_en=[("Unique passwords, MFA, a password manager, and no shared access", True), ("One long shared team password changed quarterly", False), ("One strong password reused for email and CRM to make it memorable", False)],
        ),
        localized_question_seed(
            locale=locale,
            topic_key="incident",
            difficulty=5,
            text_ru="Вы получили уведомление о подозрительном входе в рабочую систему. Что делать в правильном порядке?",
            text_en="You receive an alert about a suspicious login to a work system. What is the correct order of actions?",
            explanation_ru="Сначала нужно зафиксировать событие и сообщить о нем, а уже затем выполнять инструкции по смене доступа и проверке устройств.",
            explanation_en="You should first record and report the event, then follow containment steps such as password change or device review.",
            options_ru=[("Сообщить по каналу ИБ, сохранить детали события и затем следовать инструкциям по ограничению доступа", True), ("Сразу удалить уведомление и просто сменить пароль без сообщения", False), ("Написать в общий чат, что система, вероятно, снова сломалась", False)],
            options_en=[("Report through the security channel, preserve the details, and then follow containment instructions", True), ("Delete the alert and only change the password without reporting it", False), ("Post in a group chat that the system is probably broken again", False)],
            estimated_seconds=35,
        ),
    ]


def extra_service_questions(locale: str) -> list[QuestionSeed]:
    return [
        localized_question_seed(
            locale=locale,
            topic_key="sla",
            difficulty=1,
            text_ru="Запрос ушел в другую команду. Что клиент должен узнать сразу?",
            text_en="A request was routed to another team. What should the client be told immediately?",
            explanation_ru="Клиенту важно понимать, кто теперь координирует следующий шаг и когда ждать обновление.",
            explanation_en="The client should know who now coordinates the next step and when to expect the next update.",
            options_ru=[("Кто теперь ведет кейс и когда будет следующий апдейт", True), ("Ничего, пока новая команда сама не ответит", False), ("Только внутренний номер очереди без пояснений", False)],
            options_en=[("Who now owns the case and when the next update will come", True), ("Nothing until the new team replies on its own", False), ("Only the internal queue number with no explanation", False)],
        ),
        localized_question_seed(
            locale=locale,
            topic_key="tone",
            difficulty=2,
            text_ru="Какой ответ звучит профессионально и по-человечески?",
            text_en="Which reply sounds both professional and human?",
            explanation_ru="Лучший ответ сочетает признание влияния на клиента и конкретное следующее действие.",
            explanation_en="The strongest reply combines acknowledgment of impact with a concrete next action.",
            options_ru=[("Понимаю, что задержка мешает работе; проверю статус и вернусь к вам до 16:00", True), ("Наберитесь терпения, мы разберемся когда сможем", False), ("Это не от нас зависит, ждите", False)],
            options_en=[("I understand the delay affects your work; I will verify the status and update you by 16:00", True), ("Please be patient, we will look into it when we can", False), ("It is not on our side, just wait", False)],
        ),
        localized_question_seed(
            locale=locale,
            topic_key="complaints",
            difficulty=3,
            text_ru="Какова первая цель при обработке жалобы клиента?",
            text_en="What is the first goal when handling a client complaint?",
            explanation_ru="Сначала нужно убедиться, что вы одинаково понимаете проблему и ее влияние, а уже потом переходить к решению.",
            explanation_en="The first goal is to confirm a shared understanding of the issue and its impact before moving to resolution.",
            options_ru=[("Подтвердить понимание проблемы и ее влияния", True), ("Сразу перечислить все ограничения политики", False), ("Как можно быстрее закрыть разговор", False)],
            options_en=[("Confirm your understanding of the issue and its impact", True), ("Immediately list all policy limitations", False), ("Close the conversation as quickly as possible", False)],
        ),
        localized_question_seed(
            locale=locale,
            topic_key="deescalation",
            difficulty=3,
            text_ru="Что сильнее всего мешает деэскалации разговора?",
            text_en="What most undermines de-escalation in a difficult conversation?",
            explanation_ru="Оправдания и зеркалирование раздраженного тона усиливают конфликт вместо его снижения.",
            explanation_en="Defensiveness and mirroring the client's irritated tone intensify the conflict instead of reducing it.",
            options_ru=[("Оправдываться и отвечать тем же раздраженным тоном", True), ("Кратко резюмировать факты и следующий шаг", False), ("Признать неудобство и зафиксировать время апдейта", False)],
            options_en=[("Get defensive and answer with the same irritated tone", True), ("Briefly summarize the facts and the next step", False), ("Acknowledge the inconvenience and confirm the update time", False)],
        ),
        localized_question_seed(
            locale=locale,
            topic_key="sla",
            difficulty=4,
            text_ru="Что делает сообщение об эскалации кейса действительно полезным для другой команды?",
            text_en="What makes an escalation message genuinely useful for another team?",
            explanation_ru="Полезная эскалация показывает статус, риск, влияние на клиента и конкретный запрос на действие.",
            explanation_en="A useful escalation explains status, risk, client impact, and the specific action being requested.",
            options_ru=[("Фактический статус, риск по сроку, влияние и четкий запрос на помощь", True), ("Только фразу «нужно срочно помочь»", False), ("Подробную историю эмоций клиента без решения", False)],
            options_en=[("Factual status, deadline risk, impact, and a clear request for help", True), ("Only the phrase 'we need urgent help'", False), ("A detailed account of the client's emotions with no request", False)],
        ),
        localized_question_seed(
            locale=locale,
            topic_key="deescalation",
            difficulty=5,
            text_ru="Клиент несколько раз перебивает и повышает голос. Как лучше удержать разговор в рабочем русле?",
            text_en="A client keeps interrupting and raising their voice. What best keeps the conversation productive?",
            explanation_ru="Спокойное короткое резюме фактов и один следующий шаг помогает вернуть разговор в управляемую структуру.",
            explanation_en="A calm factual summary and a single next step help bring the conversation back into a manageable structure.",
            options_ru=[("Спокойно обозначить, что вы услышали, и перевести разговор к следующему шагу и сроку", True), ("Перебивать в ответ, чтобы быстрее договорить", False), ("Закрыть кейс до тех пор, пока клиент не успокоится сам", False)],
            options_en=[("Calmly restate what you heard and move the conversation to the next step and timing", True), ("Interrupt back so you can finish your point faster", False), ("Close the case until the client calms down on their own", False)],
            estimated_seconds=35,
        ),
    ]


def enrich_question_banks(catalog: list[CourseSeed], *, locale: str) -> list[CourseSeed]:
    extras = [
        extra_onboarding_questions(locale),
        extra_security_questions(locale),
        extra_service_questions(locale),
    ]
    for course, course_extras in zip(catalog, extras):
        course.questions = [*course.questions, *course_extras]
    return catalog


def build_course_catalog_en() -> list[CourseSeed]:
    onboarding_video = "/media/onboarding-demo.mp4"
    security_video = "/media/security-demo.mp4"
    service_video = "/media/service-demo.mp4"
    catalog = [
        CourseSeed(
            title="Corporate Onboarding and Internal Processes",
            description="A practical onboarding track for new employees: company structure, communication rules, and day-one workflows.",
            topics=[
                TopicSeed("org", "Company structure", "How teams, roles, and escalation paths are organized."),
                TopicSeed("tools", "Digital workspace", "Using the corporate portal, messenger, and task tracker."),
                TopicSeed("comms", "Business communication", "Rules for email, meetings, and response etiquette."),
                TopicSeed("support", "Escalation and support", "How to ask for help and route incidents correctly."),
            ],
            lessons=[
                lesson_seed(
                    topic_key="org",
                    title="Who does what in the company",
                    summary="A role map for the first weeks: who owns onboarding, daily management, HR questions, IT access, and security issues.",
                    image_key="onboarding-org-roles",
                    video_url=onboarding_video,
                    duration_minutes=9,
                    why_it_matters="New employees lose time when they ask the right question in the wrong place. A clear role map reduces delays, avoids duplicate requests, and lowers first-week anxiety.",
                    practice=[
                        "Use your line manager for priorities, workload, and approval boundaries.",
                        "Use your mentor for practical adaptation and unwritten team routines.",
                        "Use HR for employment documents, leave policy, and benefits.",
                        "Use IT support for devices, access, and business software issues.",
                    ],
                    scenario="You cannot access the analytics dashboard, your probation review is next week, and your VPN token stopped working. A strong employee separates the requests instead of writing one vague message to everyone.",
                    checklist=[
                        "Can you name the owner of HR, IT, and security issues?",
                        "Do you know where your team escalation map is stored?",
                        "Can you explain the difference between a mentor and a line manager?",
                    ],
                    reflection="Think about one issue from your first week. Which role should have handled it and how could the request have been clearer?",
                ),
                lesson_seed(
                    topic_key="tools",
                    title="Working with the corporate portal",
                    summary="The portal is the official source for policies, announcements, requests, and knowledge articles. This lesson shows what belongs there and what does not.",
                    image_key="onboarding-portal",
                    video_url=onboarding_video,
                    duration_minutes=8,
                    why_it_matters="When policy, forms, and internal news are spread across chat messages, employees act on outdated information. The portal reduces ambiguity by keeping approved content in one visible place.",
                    practice=[
                        "Check the portal before asking where a policy or template is stored.",
                        "Use the request flow inside the portal for repeatable HR and admin tasks.",
                        "Bookmark critical pages such as leave requests, policies, and knowledge base.",
                    ],
                    scenario="A colleague sends you a screenshot of an old vacation request form in chat. Before using it, you open the portal and confirm that the policy and the form version are still current.",
                    checklist=[
                        "You know where company policies are published.",
                        "You know where to submit routine admin requests.",
                        "You can find at least one knowledge base article without asking in chat.",
                    ],
                    reflection="Which repeated question in your team could be replaced by a portal article or a pinned portal link?",
                ),
                lesson_seed(
                    topic_key="tools",
                    title="Task tracker and messenger basics",
                    summary="Use chat for coordination and the task tracker for anything with ownership, a deadline, or a required outcome.",
                    image_key="onboarding-task-tracker",
                    video_url=onboarding_video,
                    duration_minutes=10,
                    why_it_matters="Teams move faster when a decision made in chat is translated into a visible task. Otherwise deadlines drift, owners change silently, and follow-up becomes emotional instead of factual.",
                    practice=[
                        "Create a task when the work has a deadline, deliverable, or dependency.",
                        "Use messenger for short coordination, not as the only source of truth.",
                        "Summarize important chat decisions in the task description or comments.",
                        "Keep due dates and owners current after each handoff.",
                    ],
                    scenario="A quick chat turns into three action items, one approval, and a design correction. Without a task, everyone remembers a different version of the agreement by the end of the day.",
                    checklist=[
                        "Important work items have an owner.",
                        "Deadlines are stored in the tracker, not only in chat.",
                        "Decisions from meetings or messenger are written back into the task.",
                    ],
                    reflection="What is one task in your current workflow that still depends too much on memory or chat history?",
                ),
                lesson_seed(
                    topic_key="comms",
                    title="How to write business messages",
                    summary="A good internal message gives context, asks for one clear action, and sets the expected timeline without sounding abrupt.",
                    image_key="onboarding-business-message",
                    video_url=onboarding_video,
                    duration_minutes=11,
                    why_it_matters="People answer faster when they understand why you are writing, what you need, and by when. Most urgent conversations become slower because the first message is too vague.",
                    practice=[
                        "Start with short context so the reader knows what this is about.",
                        "Ask for one explicit action or decision.",
                        "State the expected timeline and why it matters.",
                        "Attach the link, file, or task reference instead of expecting the reader to search for it.",
                    ],
                    scenario="You need approval for a client-facing report before 15:00. A strong message includes the report link, the decision needed, the reason for urgency, and who is waiting on the answer.",
                    checklist=[
                        "The message contains context, action, and deadline.",
                        "The reader can open the exact file or task from the message.",
                        "The tone stays respectful even when the request is urgent.",
                    ],
                    reflection="Rewrite the last vague work message you sent so it would be easier to answer in one pass.",
                ),
                lesson_seed(
                    topic_key="support",
                    title="Escalation map for a new employee",
                    summary="Escalation is not panic; it is a controlled way to move an issue to the person who can unblock it with the right context.",
                    image_key="onboarding-escalation",
                    video_url=onboarding_video,
                    duration_minutes=9,
                    why_it_matters="New employees often wait too long because they think escalation means failure. In reality, escalation protects deadlines and keeps small blockers from becoming team-wide delays.",
                    practice=[
                        "Escalate with facts: current status, blocker, impact, and requested help.",
                        "Use the approved channel for security or access incidents.",
                        "Tell the next owner what has already been tried.",
                        "Avoid emotional commentary that hides the actual blocker.",
                    ],
                    scenario="Your laptop access issue blocks the mandatory induction test. Instead of saying it still does not work, you send the ticket number, the deadline at risk, and what support already asked you to try.",
                    checklist=[
                        "You know which issues require immediate escalation.",
                        "You can describe a blocker in three factual sentences.",
                        "You know the correct path for IT, HR, and security incidents.",
                    ],
                    reflection="What kind of issue in your team is usually escalated too late, and what signal should trigger earlier action?",
                ),
            ],
            test_title="Onboarding Checkpoint",
            questions=[
                QuestionSeed("org", 1, "Who usually helps a new employee adapt during the first weeks?", "Mentor support is part of standard onboarding.", [("Assigned mentor", True), ("External client", False), ("Random colleague", False)]),
                QuestionSeed("tools", 1, "Where should a task with a deadline be recorded?", "Tasks with deadlines should be traceable in the task tracker.", [("Task tracker", True), ("Personal notebook only", False), ("Informal chat only", False)]),
                QuestionSeed("comms", 2, "Which message is best for a work request?", "The best message gives context, expected result, and timing.", [("A short message with context, request, and deadline", True), ("A vague message like 'Need help ASAP'", False), ("No message, only a missed call", False)]),
                QuestionSeed("support", 2, "Whom should you contact about laptop access issues?", "Access and device issues are handled by IT support.", [("IT support", True), ("Finance team", False), ("Reception desk", False)]),
                QuestionSeed("tools", 3, "Why is using the corporate messenger better than a personal chat app for work topics?", "Corporate tools preserve auditability, history, and access control.", [("Because communication stays in a managed company environment", True), ("Because personal apps are always blocked by law", False), ("Because it makes tasks optional", False)]),
                QuestionSeed("comms", 3, "What is the main problem with sending urgent requests without context?", "Lack of context slows down prioritization and response quality.", [("Colleagues must guess the issue and the expected outcome", True), ("It automatically closes the task", False), ("It makes the request legally invalid", False)]),
                QuestionSeed("support", 4, "A new employee notices suspicious access to shared files. What is the best first action?", "Potential security issues should be escalated immediately through the approved channel.", [("Report it to the security team and manager through approved channels", True), ("Ignore it if work continues", False), ("Post the issue in a public group chat", False)]),
                QuestionSeed("org", 4, "Why is it important to understand the escalation path during onboarding?", "Knowing the path reduces response time and operational confusion.", [("It helps route issues to the right team quickly", True), ("It removes the need for managers", False), ("It means policies can be skipped", False)]),
                QuestionSeed("tools", 5, "Which behavior best supports traceable operational work?", "Traceability requires business actions to be documented in managed systems.", [("Confirm decisions in the task tracker or portal after discussing them", True), ("Rely only on memory after a verbal agreement", False), ("Store approvals only in private messages", False)]),
                QuestionSeed("comms", 5, "A stakeholder asks for a report 'soon'. What is the best response?", "Clarifying deadline and scope protects quality and expectations.", [("Clarify deadline, expected format, and business priority", True), ("Promise delivery immediately without clarifying the request", False), ("Ignore until another reminder arrives", False)], estimated_seconds=35),
            ],
        ),
        CourseSeed(
            title="Information Security Essentials for Office Staff",
            description="Core security behavior for everyday office work: passwords, phishing, data handling, and incident response.",
            topics=[
                TopicSeed("passwords", "Password hygiene", "Creating, storing, and rotating strong credentials."),
                TopicSeed("phishing", "Phishing awareness", "How to detect suspicious emails and links."),
                TopicSeed("data", "Sensitive data handling", "Rules for client, employee, and internal information."),
                TopicSeed("incident", "Security incidents", "First response to suspicious activity and device compromise."),
            ],
            lessons=[
                lesson_seed(
                    topic_key="passwords",
                    title="Strong password policy",
                    summary="The goal is not just hard to guess passwords, but credentials that stay unique, manageable, and resistant to reuse across systems.",
                    image_key="security-passwords",
                    video_url=security_video,
                    duration_minutes=9,
                    why_it_matters="Password weakness creates avoidable incidents. The biggest risk in office environments is usually not a single weak password, but the combination of reuse, sharing, and poor storage habits.",
                    practice=[
                        "Use a password manager to generate and store unique passwords.",
                        "Enable multifactor authentication where the system supports it.",
                        "Never share a personal credential, even with a trusted colleague.",
                        "Treat reset emails and one-time codes as sensitive access data.",
                    ],
                    scenario="A teammate asks you to send your VPN password because they need to quickly test something. Strong practice means offering the right support path without sharing the credential.",
                    checklist=[
                        "Critical work accounts use unique passwords.",
                        "You know where your team stores emergency access procedures without sharing personal credentials.",
                        "You can explain why MFA is part of the normal login process, not an optional extra.",
                    ],
                    reflection="Which of your current work systems would create the biggest risk if the same password were reused elsewhere?",
                ),
                lesson_seed(
                    topic_key="passwords",
                    title="Why password reuse is dangerous",
                    summary="Reuse turns one external breach into a multi-system problem. This lesson explains the chain reaction behind credential stuffing.",
                    image_key="security-password-reuse",
                    video_url=security_video,
                    duration_minutes=8,
                    why_it_matters="Employees often underestimate the speed at which stolen credentials are tested against other services. Attackers do not need to know your company personally to reuse exposed passwords at scale.",
                    practice=[
                        "Assume public breach data is quickly tested on popular business services.",
                        "Reset exposed passwords immediately and anywhere they were reused.",
                        "Use unique passwords so one compromise does not cascade into others.",
                    ],
                    scenario="A social platform announces a breach. If you reused that password for email or CRM access, the event is no longer personal only. It becomes an enterprise risk.",
                    checklist=[
                        "You know what credential stuffing means.",
                        "You can identify where a reused password would create the biggest damage.",
                        "You have a practical way to replace reused passwords quickly.",
                    ],
                    reflection="What would happen in your team if a mailbox password were reused across two or three other business systems?",
                ),
                lesson_seed(
                    topic_key="phishing",
                    title="How to spot phishing",
                    summary="Phishing rarely looks obviously malicious. It imitates urgency, authority, or routine process to make a risky click feel normal.",
                    image_key="security-phishing",
                    video_url=security_video,
                    duration_minutes=11,
                    why_it_matters="Phishing succeeds when the reader is rushed, distracted, or overly trusting of familiar logos. Good detection habits are therefore practical behaviors, not theoretical knowledge.",
                    practice=[
                        "Check sender domain instead of trusting the display name.",
                        "Hover or inspect links before opening them.",
                        "Be suspicious of urgency, secrecy, or unusual payment or access requests.",
                        "Treat unexpected attachments as high risk until verified.",
                    ],
                    scenario="An email marked Finance urgent asks you to download a new payment form before the end of the day. The logo looks familiar, but the sender domain and the attachment type do not fit your normal process.",
                    checklist=[
                        "You inspect sender domain and link target first.",
                        "You know which channel to use when reporting suspicious mail.",
                        "You do not forward suspicious mail broadly before security review.",
                    ],
                    reflection="Which phishing signal are you personally most likely to miss when you are busy: sender mismatch, urgency, or an unusual attachment?",
                ),
                lesson_seed(
                    topic_key="data",
                    title="Working with confidential files",
                    summary="Sensitive data handling is mostly about choosing the right channel, the right audience, and the right storage location every time.",
                    image_key="security-confidential-files",
                    video_url=security_video,
                    duration_minutes=10,
                    why_it_matters="A file can be accurate and useful and still create a serious incident if it reaches the wrong mailbox, device, or shared folder. Most handling mistakes happen during routine work, not during dramatic breaches.",
                    practice=[
                        "Share files only through approved systems with managed access.",
                        "Check recipients and permissions before sending a link or attachment.",
                        "Store client and employee data only where retention and access are controlled.",
                        "Remove unnecessary copies once the approved record exists.",
                    ],
                    scenario="You need to review a client spreadsheet at home. The safe choice is to use the approved remote channel or secure workspace, not your personal mailbox or a consumer file-sharing account.",
                    checklist=[
                        "You know which systems are approved for confidential data.",
                        "You verify recipients before sharing a link or file.",
                        "You avoid creating unmanaged copies for convenience.",
                    ],
                    reflection="What is the most common shortcut with files in your environment, and why could it become a data leak?",
                ),
                lesson_seed(
                    topic_key="incident",
                    title="What to do after a suspected compromise",
                    summary="The first minutes after a suspicious click, device alert, or account anomaly matter more than a perfect diagnosis. Fast reporting is part of protection.",
                    image_key="security-incident-response",
                    video_url=security_video,
                    duration_minutes=9,
                    why_it_matters="People delay reporting because they want to be sure first. That delay often gives an attacker more time. Early reporting lets the security team contain risk while evidence is still available.",
                    practice=[
                        "Use the approved incident channel as soon as the event looks suspicious.",
                        "Follow containment instructions instead of improvising fixes.",
                        "Preserve evidence such as screenshots, timestamps, or suspicious emails.",
                        "Do not hide the mistake; security response depends on accurate timing.",
                    ],
                    scenario="You opened a suspicious attachment but nothing obvious happened. That is still enough reason to report the event and preserve the message details for the security team.",
                    checklist=[
                        "You know the incident channel and when to use it.",
                        "You can separate containment from guesswork.",
                        "You understand that quick reporting is valued more than false confidence.",
                    ],
                    reflection="If you suspected compromise right now, what exact first message would you send and to whom?",
                ),
            ],
            test_title="Security Awareness Adaptive Test",
            questions=[
                QuestionSeed("passwords", 1, "What is the safest way to store many unique passwords?", "A password manager is the recommended approach.", [("Use a password manager", True), ("Write them on a sticky note", False), ("Reuse one strong password everywhere", False)]),
                QuestionSeed("phishing", 1, "What should you check first in a suspicious email?", "Start with sender address and domain.", [("Sender address and domain", True), ("Only whether the logo looks good", False), ("Only the email color theme", False)]),
                QuestionSeed("data", 2, "Can you send confidential files to a personal mailbox to work from home?", "Sensitive data must stay in approved company systems.", [("No, only approved channels may be used", True), ("Yes, if the file is small", False), ("Yes, if you delete it later", False)]),
                QuestionSeed("incident", 2, "You clicked a suspicious link. What should you do first?", "Early reporting reduces impact.", [("Report the incident immediately through the approved channel", True), ("Wait to see if something breaks", False), ("Delete browser history and stay silent", False)]),
                QuestionSeed("passwords", 3, "Why is password reuse dangerous even with a strong password?", "Reuse creates cross-system compromise risk.", [("One leak can expose multiple accounts", True), ("Because strong passwords expire faster", False), ("Because password length becomes invalid", False)]),
                QuestionSeed("phishing", 3, "Which sign is the strongest indicator of phishing?", "A mismatch between displayed and actual link target is a major red flag.", [("A link that points to a different domain than expected", True), ("A polite greeting", False), ("A standard email signature", False)]),
                QuestionSeed("data", 4, "A colleague asks for client data but has no business need. What should you do?", "Access should be based on need-to-know.", [("Decline and route the request through the proper approval path", True), ("Send part of the file as a compromise", False), ("Share it if the colleague works in the same building", False)]),
                QuestionSeed("incident", 4, "Why should an employee report a security incident quickly even if unsure?", "Rapid reporting helps contain the threat before impact spreads.", [("Early response can reduce damage and preserve evidence", True), ("Because late reports automatically delete data", False), ("Because uncertainty means the issue is definitely harmless", False)]),
                QuestionSeed("passwords", 5, "Which combination best reflects good credential practice?", "Unique passwords, password manager, MFA, and no sharing.", [("Unique passwords, manager, MFA, no sharing", True), ("Shared team password and monthly reuse", False), ("Simple password with hidden notebook copy", False)]),
                QuestionSeed("phishing", 5, "A message pressures you to act 'within 10 minutes' and open an attachment from an unknown sender. Best action?", "Urgency plus unknown sender is a classic phishing pattern.", [("Do not open it and report it to security", True), ("Open it on your phone instead", False), ("Forward it to colleagues to ask if it looks safe", False)], estimated_seconds=35),
            ],
        ),
        CourseSeed(
            title="Client Service Standards and Difficult Conversations",
            description="A frontline service course on request intake, SLA expectations, complaint handling, and de-escalation.",
            topics=[
                TopicSeed("sla", "Service expectations", "Response windows, ownership, and prioritization."),
                TopicSeed("tone", "Professional tone", "Clear, empathetic, and outcome-focused communication."),
                TopicSeed("complaints", "Complaint handling", "Structure for listening, clarifying, and resolving."),
                TopicSeed("deescalation", "Conflict de-escalation", "Reducing tension while protecting policy compliance."),
            ],
            lessons=[
                lesson_seed(
                    topic_key="sla",
                    title="Who owns the request",
                    summary="The first responder owns the next step immediately, even when another team will complete the work later.",
                    image_key="service-request-ownership",
                    video_url=service_video,
                    duration_minutes=8,
                    why_it_matters="Clients experience delays as silence and confusion, not as internal routing problems. Ownership means the client always knows who is coordinating the next action.",
                    practice=[
                        "Acknowledge receipt quickly and state the next checkpoint.",
                        "Clarify whether you are the resolver or the coordinator.",
                        "If you hand work over, keep the ownership note visible in the system.",
                    ],
                    scenario="A request arrives in the wrong queue. Strong service means you do not just forward it silently. You tell the client what is happening, who now owns it, and when they will hear back.",
                    checklist=[
                        "Every live request has a visible owner.",
                        "The client knows the next update time.",
                        "Routing does not remove accountability.",
                    ],
                    reflection="Where in your process do requests most often lose ownership during handoff?",
                ),
                lesson_seed(
                    topic_key="tone",
                    title="Empathy without false promises",
                    summary="Empathy is not the same as agreeing to everything. The goal is to acknowledge impact while staying accurate about what can happen next.",
                    image_key="service-empathy",
                    video_url=service_video,
                    duration_minutes=10,
                    why_it_matters="In difficult conversations, tone either lowers pressure or amplifies it. A respectful, concrete answer builds trust even before the full solution is ready.",
                    practice=[
                        "Name the client's frustration without sounding defensive.",
                        "Promise only the next action you can actually deliver.",
                        "Use time commitments carefully and specifically.",
                        "Avoid generic phrases that sound polite but empty.",
                    ],
                    scenario="A client says they have already explained the same issue twice. A strong answer acknowledges the frustration, summarizes the issue accurately, and states the next concrete update point.",
                    checklist=[
                        "You used empathy and action in the same answer.",
                        "You avoided promises outside your control.",
                        "Your timeline statement is specific enough to be checked later.",
                    ],
                    reflection="Which phrase in your current service vocabulary sounds polite but does not actually help the client move forward?",
                ),
                lesson_seed(
                    topic_key="complaints",
                    title="Complaint handling structure",
                    summary="Good complaint handling is a repeatable sequence: listen, restate, clarify, propose options, and confirm the timeline.",
                    image_key="service-complaints",
                    video_url=service_video,
                    duration_minutes=11,
                    why_it_matters="Complaints feel chaotic when the employee tries to solve everything at once. A visible structure calms the conversation and protects decision quality.",
                    practice=[
                        "Let the client finish the initial problem statement.",
                        "Restate the issue in your own words to confirm understanding.",
                        "Ask only the clarifying questions needed for the next decision.",
                        "Close with options, owner, and timing.",
                    ],
                    scenario="A client complains about a missed promise and a poor prior response. Instead of defending the earlier interaction, you verify the facts, confirm the current business impact, and agree on the next checkpoint.",
                    checklist=[
                        "You confirmed the issue before proposing action.",
                        "You reduced repetition by summarizing clearly.",
                        "The final answer included next steps and timing.",
                    ],
                    reflection="Which part of the complaint sequence is hardest for you: listening fully, clarifying, or confirming the timeline?",
                ),
                lesson_seed(
                    topic_key="deescalation",
                    title="How to calm a tense client",
                    summary="De-escalation means reducing emotional heat while keeping the conversation useful, factual, and policy-compliant.",
                    image_key="service-deescalation",
                    video_url=service_video,
                    duration_minutes=9,
                    why_it_matters="Clients calm down when they feel heard and when the next step sounds real. They escalate further when they hear scripts, excuses, or vague promises.",
                    practice=[
                        "Lower your pace and use short factual sentences.",
                        "Separate feelings from facts without dismissing either.",
                        "Move the discussion toward a specific next checkpoint.",
                        "Avoid mirroring sarcasm, blame, or raised emotional language.",
                    ],
                    scenario="A caller says your team is useless after waiting too long. The best response is not to argue about fairness. It is to restate the case, confirm impact, and direct the conversation toward the next action and time.",
                    checklist=[
                        "Your answer lowered tension rather than matching it.",
                        "You did not take the client's tone personally.",
                        "You ended the reply with a controllable next step.",
                    ],
                    reflection="What personal habit helps you stay calm when the other person is angry or unfair?",
                ),
                lesson_seed(
                    topic_key="sla",
                    title="Escalating overdue cases",
                    summary="An overdue case should be escalated early with clean context, business impact, and a clear request for help.",
                    image_key="service-overdue-escalation",
                    video_url=service_video,
                    duration_minutes=8,
                    why_it_matters="Late escalation creates avoidable surprises for both the client and internal teams. Escalation works best when it happens while there is still time to protect the deadline.",
                    practice=[
                        "Raise the risk before the SLA is actually missed.",
                        "Share the current state, blocker, impact, and requested decision.",
                        "Use facts and timestamps instead of frustration.",
                        "Tell the client what is happening after the internal escalation is underway.",
                    ],
                    scenario="A vendor dependency blocks resolution and the promised response window is about to expire. Strong practice means escalating with evidence and impact, not waiting for the deadline to pass.",
                    checklist=[
                        "You can explain why the case is at risk in one short summary.",
                        "You know what exact decision or support you are asking for.",
                        "You can update the client honestly without blaming other teams.",
                    ],
                    reflection="Think of one overdue case pattern in your organization. What information is usually missing from the escalation message?",
                ),
            ],
            test_title="Client Service Simulation Test",
            questions=[
                QuestionSeed("sla", 1, "What should a support employee do first after receiving a client request?", "Acknowledge receipt and clarify next step.", [("Acknowledge the request and confirm next step", True), ("Wait until the full solution is ready", False), ("Forward it without reading", False)]),
                QuestionSeed("tone", 1, "Which tone is best in a tense conversation?", "Professional and empathetic tone reduces friction.", [("Calm, respectful, and specific", True), ("Cold and one-word replies", False), ("Defensive and sarcastic", False)]),
                QuestionSeed("complaints", 2, "Why is restating the client's issue useful?", "It confirms understanding and reduces repeated frustration.", [("It shows that the issue was understood correctly", True), ("It lets you end the conversation faster without action", False), ("It shifts blame to the client", False)]),
                QuestionSeed("deescalation", 2, "A client becomes emotional. What helps most?", "A calm structure and next steps help more than arguing.", [("Acknowledge frustration and guide toward next steps", True), ("Argue point by point immediately", False), ("Ignore emotional cues completely", False)]),
                QuestionSeed("sla", 3, "What is the biggest risk of not confirming request ownership?", "Unclear ownership leads to delays and dropped requests.", [("The request can stall between teams", True), ("It automatically changes SLA class", False), ("It prevents note-taking", False)]),
                QuestionSeed("tone", 3, "Which phrase is better?", "The stronger phrase combines empathy with a concrete action.", [("I understand the delay is frustrating; I will update you by 15:00", True), ("Calm down and wait", False), ("This is not my problem", False)]),
                QuestionSeed("complaints", 4, "What is a good complaint-resolution sequence?", "Structured resolution reduces ambiguity and rebuilds trust.", [("Listen, clarify, propose options, confirm timeline", True), ("Deflect, justify, and close quickly", False), ("Promise a refund before checking policy", False)]),
                QuestionSeed("deescalation", 4, "Why should you avoid making promises you cannot guarantee?", "Broken promises amplify frustration and erode trust.", [("It damages trust and creates a second complaint", True), ("It makes the CRM system slower", False), ("It is acceptable if your tone is friendly", False)]),
                QuestionSeed("sla", 5, "An issue is blocked by another team and SLA is at risk. Best action?", "Escalate early with facts, current status, and requested help.", [("Escalate early with context, impact, and requested action", True), ("Wait until SLA is already missed", False), ("Tell the client nothing until resolved", False)]),
                QuestionSeed("deescalation", 5, "What best supports de-escalation in a difficult call?", "Control of tone and process creates safety and momentum.", [("Use calm language, summarize facts, and agree on the next checkpoint", True), ("Mirror the client's aggressive tone", False), ("Read policy text without adaptation", False)], estimated_seconds=35),
            ],
        ),
    ]
    return enrich_question_banks(catalog, locale="en")


def build_course_catalog_ru() -> list[CourseSeed]:
    catalog = repair_text_payload([
        _ru_onboarding_course(),
        _ru_security_course(),
        _ru_service_course(),
    ])
    return enrich_question_banks(catalog, locale="ru")


def build_course_catalog(locale: str) -> list[CourseSeed]:
    return build_course_catalog_ru() if is_russian(locale) else build_course_catalog_en()


def _ru_onboarding_course() -> CourseSeed:
    video_url = "/media/onboarding-demo.mp4"
    return CourseSeed(
        title="Корпоративный онбординг и внутренние процессы",
        description="Практический курс для новых сотрудников: структура компании, рабочие инструменты, деловая коммуникация и эскалация вопросов.",
        topics=[
            TopicSeed("org", "Структура компании", "Как устроены команды, роли и цепочки эскалации."),
            TopicSeed("tools", "Цифровое рабочее место", "Портал, мессенджер и трекер задач в ежедневной работе."),
            TopicSeed("comms", "Деловая коммуникация", "Письма, рабочие сообщения и ожидания по срокам ответа."),
            TopicSeed("support", "Эскалация и поддержка", "Как быстро и правильно поднимать блокеры."),
        ],
        lessons=[
            lesson_seed(
                locale="ru",
                topic_key="org",
                title="Кто за что отвечает в компании",
                summary="Карта ролей на первые недели: кто помогает с адаптацией, задачами, HR-вопросами, доступами и инцидентами.",
                image_key="onboarding-org-roles",
                video_url=video_url,
                duration_minutes=9,
                why_it_matters="Новый сотрудник теряет время, когда задает правильный вопрос не тому человеку. Понимание роли руководителя, наставника, HR и IT помогает быстрее решать задачи и снижает стресс первых недель.",
                practice=[
                    "К руководителю идут с приоритетами, сроками и границами ответственности.",
                    "К наставнику обращаются за практической адаптацией и негласными правилами команды.",
                    "HR помогает с документами, отпусками и льготами.",
                    "IT-поддержка отвечает за доступы, устройства и рабочее ПО.",
                ],
                scenario="У вас одновременно сломался VPN-токен, не открывается аналитическая панель и приближается встреча по испытательному сроку. Сильная практика — разделить запросы по владельцам, а не писать всем один размытый текст.",
                checklist=[
                    "Вы можете назвать владельца HR-, IT- и security-вопросов.",
                    "Вы знаете, где хранится схема эскалации в вашей команде.",
                    "Вы понимаете разницу между наставником и руководителем.",
                ],
                reflection="Вспомните одну проблему из первых рабочих дней. Кто должен был помочь по ней первым и как можно было сформулировать запрос точнее?",
            ),
            lesson_seed(
                locale="ru",
                topic_key="tools",
                title="Как работать с корпоративным порталом",
                summary="Портал — официальный источник политик, новостей, заявок и базы знаний. Урок показывает, что искать там в первую очередь.",
                image_key="onboarding-portal",
                video_url=video_url,
                duration_minutes=8,
                why_it_matters="Когда инструкции, формы и объявления живут в чатах, сотрудники начинают опираться на устаревшую информацию. Портал снижает неопределенность, потому что там хранится утвержденная и актуальная версия процессов.",
                practice=[
                    "Проверяйте портал до того, как спрашивать, где лежит политика или шаблон.",
                    "Используйте внутренние формы портала для типовых административных запросов.",
                    "Сохраняйте важные страницы: отпуска, политики, база знаний и сервисные заявки.",
                ],
                scenario="Коллега прислал скрин старой формы на отпуск в мессенджере. Перед использованием вы открываете портал и убеждаетесь, что версия политики и формы актуальна.",
                checklist=[
                    "Вы знаете, где публикуются корпоративные политики.",
                    "Вы умеете заводить типовые заявки через портал.",
                    "Вы можете найти статью из базы знаний без вопроса в чате.",
                ],
                reflection="Какой повторяющийся вопрос в вашей команде можно было бы снять одной хорошей страницей на портале?",
            ),
            lesson_seed(
                locale="ru",
                topic_key="tools",
                title="Трекер задач и рабочий мессенджер",
                summary="Чат нужен для координации, а трекер — для всего, у чего есть владелец, дедлайн или ожидаемый результат.",
                image_key="onboarding-task-tracker",
                video_url=video_url,
                duration_minutes=10,
                why_it_matters="Команда двигается быстрее, когда решение из чата превращается в видимую задачу. Иначе сроки размываются, владельцы меняются молча, а контроль зависит от памяти, а не от системы.",
                practice=[
                    "Заводите задачу, если у работы есть дедлайн, результат или зависимость.",
                    "Используйте чат для короткой синхронизации, а не как единственный источник правды.",
                    "Фиксируйте решения из чатов и встреч в задаче или комментариях.",
                    "Обновляйте сроки и владельца после каждого handoff.",
                ],
                scenario="Короткий чат превратился в три действия, одно согласование и одно исправление. Без задачи к концу дня каждый помнит разную версию договоренности.",
                checklist=[
                    "У важных задач есть явный владелец.",
                    "Сроки хранятся в трекере, а не только в чате.",
                    "Решения из встреч и мессенджера возвращаются обратно в систему.",
                ],
                reflection="Какая задача в вашем потоке работы до сих пор слишком сильно зависит от памяти или истории чата?",
            ),
            lesson_seed(
                locale="ru",
                topic_key="comms",
                title="Как писать деловые сообщения",
                summary="Хорошее внутреннее сообщение дает контекст, просит одно понятное действие и сразу задает ожидаемый срок.",
                image_key="onboarding-business-message",
                video_url=video_url,
                duration_minutes=11,
                why_it_matters="Люди отвечают быстрее, когда понимают, зачем вы пишете, что именно нужно и к какому времени. Большинство срочных переписок тормозятся не из-за занятости, а из-за слишком расплывчатого первого сообщения.",
                practice=[
                    "Начинайте с короткого контекста, чтобы получатель сразу понял ситуацию.",
                    "Просите одно конкретное решение или действие.",
                    "Указывайте ожидаемый срок и причину срочности.",
                    "Прикладывайте нужную ссылку, файл или задачу, а не заставляйте искать их вручную.",
                ],
                scenario="До 15:00 нужно согласовать клиентский отчет. Сильное сообщение содержит ссылку на документ, нужное решение, причину дедлайна и указание, кто ждет ответ.",
                checklist=[
                    "В сообщении есть контекст, действие и срок.",
                    "Получатель может открыть нужный файл или задачу сразу из сообщения.",
                    "Тон остается уважительным даже при срочности.",
                ],
                reflection="Перепишите свое последнее расплывчатое рабочее сообщение так, чтобы на него можно было ответить за один проход.",
            ),
            lesson_seed(
                locale="ru",
                topic_key="support",
                title="Карта эскалации для нового сотрудника",
                summary="Эскалация — это не паника, а управляемый способ быстро донести блокер до того, кто может снять его с нужным контекстом.",
                image_key="onboarding-escalation",
                video_url=video_url,
                duration_minutes=9,
                why_it_matters="Новички часто ждут слишком долго, потому что считают эскалацию признаком слабости. На практике ранняя эскалация защищает сроки и не дает маленькому блокеру вырасти в командную проблему.",
                practice=[
                    "Эскалируйте через факты: статус, блокер, влияние и какая помощь нужна.",
                    "Для security- и access-инцидентов используйте утвержденный канал, а не общий чат.",
                    "Сообщайте, что уже было проверено и сделано.",
                    "Не прячьте реальную проблему за эмоциями и оправданиями.",
                ],
                scenario="Из-за проблем с доступом вы не можете пройти обязательный вводный тест. Вместо фразы «ничего не работает» вы отправляете номер тикета, дедлайн под риском и перечень уже выполненных шагов.",
                checklist=[
                    "Вы знаете, какие проблемы требуют немедленной эскалации.",
                    "Вы умеете описать блокер в трех фактических предложениях.",
                    "Вы знаете отдельные пути для IT-, HR- и security-вопросов.",
                ],
                reflection="Какие блокеры в вашей команде обычно эскалируются слишком поздно и по какому сигналу нужно действовать раньше?",
            ),
        ],
        test_title="Проверка по онбордингу",
        questions=[
            QuestionSeed("org", 1, "Кто обычно помогает новому сотруднику адаптироваться в первые недели?", "Наставник — часть стандартной схемы адаптации.", [("Назначенный наставник", True), ("Внешний клиент", False), ("Случайный коллега", False)]),
            QuestionSeed("tools", 1, "Где нужно фиксировать задачу с дедлайном?", "Задачи со сроками должны быть видимы в трекере.", [("В трекере задач", True), ("Только в личном блокноте", False), ("Только в неформальном чате", False)]),
            QuestionSeed("comms", 2, "Какое сообщение лучше для рабочего запроса?", "Сильное сообщение содержит контекст, запрос и срок.", [("Короткое сообщение с контекстом, действием и дедлайном", True), ("Размытое «Нужна помощь срочно»", False), ("Пропущенный звонок без текста", False)]),
            QuestionSeed("support", 2, "К кому обращаться по вопросам доступа к ноутбуку или системе?", "Доступы и устройства — зона ответственности IT-поддержки.", [("В IT-поддержку", True), ("В финансовый отдел", False), ("На ресепшен", False)]),
            QuestionSeed("tools", 3, "Почему рабочий мессенджер лучше личного чата для рабочих вопросов?", "Корпоративные инструменты дают историю и управляемый доступ.", [("Коммуникация остается в управляемой корпоративной среде", True), ("Личные мессенджеры всегда запрещены законом", False), ("Так задачи можно не заводить", False)]),
            QuestionSeed("comms", 3, "В чем проблема срочного запроса без контекста?", "Без контекста сложно правильно приоритизировать и быстро помочь.", [("Коллегам приходится догадываться о сути проблемы и результате", True), ("Запрос автоматически закрывается", False), ("Такое сообщение юридически недействительно", False)]),
            QuestionSeed("support", 4, "Сотрудник заметил подозрительный доступ к общим файлам. Что делать сначала?", "Потенциальный security-инцидент нужно сразу поднимать по утвержденному каналу.", [("Сообщить в security-команду и руководителю через утвержденный канал", True), ("Игнорировать, если работа пока не остановилась", False), ("Написать об этом в общий чат", False)]),
            QuestionSeed("org", 4, "Почему важно знать путь эскалации во время адаптации?", "Понимание пути сокращает время реакции и путаницу.", [("Это помогает быстро направлять проблему в правильную команду", True), ("Это полностью заменяет руководителя", False), ("Это позволяет игнорировать политики", False)]),
            QuestionSeed("tools", 5, "Какое поведение лучше всего поддерживает прозрачную операционную работу?", "Решения должны закрепляться в управляемых системах.", [("Подтверждать решения в трекере или на портале после обсуждения", True), ("Полагаться только на память после устной договоренности", False), ("Хранить согласования только в личных сообщениях", False)]),
            QuestionSeed("comms", 5, "Стейкхолдер просит отчет «как можно скорее». Что ответить лучше всего?", "Уточнение срока и формата защищает ожидания и качество.", [("Уточнить срок, формат результата и бизнес-приоритет", True), ("Сразу пообещать отправить, не уточняя детали", False), ("Игнорировать до следующего напоминания", False)], estimated_seconds=35),
        ],
    )


def _ru_security_course() -> CourseSeed:
    video_url = "/media/security-demo.mp4"
    return CourseSeed(
        title="Основы информационной безопасности для офисных сотрудников",
        description="Базовые ежедневные привычки ИБ: пароли, фишинг, работа с чувствительными данными и первые действия при инциденте.",
        topics=[
            TopicSeed("passwords", "Пароли и MFA", "Как создавать, хранить и обновлять надежные учетные данные."),
            TopicSeed("phishing", "Фишинг", "Как распознавать подозрительные письма, ссылки и вложения."),
            TopicSeed("data", "Чувствительные данные", "Правила работы с клиентской, кадровой и внутренней информацией."),
            TopicSeed("incident", "Инциденты ИБ", "Первые действия при подозрительной активности или компрометации."),
        ],
        lessons=[
            lesson_seed(
                locale="ru",
                topic_key="passwords",
                title="Надежные пароли и MFA",
                summary="Важно не только придумать сложный пароль, но и сделать его уникальным, управляемым и защищенным от повторного использования.",
                image_key="security-passwords",
                video_url=video_url,
                duration_minutes=9,
                why_it_matters="Слабая парольная дисциплина создает инциденты, которых легко избежать. Главный риск обычно не в одном простом пароле, а в сочетании повторного использования, пересылки и плохого хранения доступов.",
                practice=[
                    "Используйте менеджер паролей для генерации и хранения уникальных паролей.",
                    "Включайте MFA везде, где система это поддерживает.",
                    "Никогда не делитесь своим логином и паролем даже с доверенным коллегой.",
                    "Письма на сброс пароля и одноразовые коды считайте чувствительными данными доступа.",
                ],
                scenario="Коллега просит прислать ваш пароль от VPN, чтобы быстро что-то проверить. Сильная практика — показать правильный путь поддержки, а не делиться учетными данными.",
                checklist=[
                    "Критичные рабочие аккаунты используют уникальные пароли.",
                    "Вы знаете, где хранится процедура аварийного доступа без передачи личных учетных данных.",
                    "Вы можете объяснить, зачем MFA — это норма, а не необязательная опция.",
                ],
                reflection="Какая из ваших рабочих систем создала бы наибольший риск, если бы пароль от нее совпадал с паролем в другом сервисе?",
            ),
            lesson_seed(
                locale="ru",
                topic_key="passwords",
                title="Почему опасно повторно использовать пароль",
                summary="Один взлом стороннего сервиса превращается в проблему сразу для нескольких систем, если пароль повторяется.",
                image_key="security-password-reuse",
                video_url=video_url,
                duration_minutes=8,
                why_it_matters="Сотрудники часто недооценивают, как быстро украденные учетные данные проверяются на других сервисах. Для credential stuffing злоумышленнику не нужно знать вашу компанию лично.",
                practice=[
                    "Исходите из того, что публичные утечки быстро проверяются на популярных бизнес-сервисах.",
                    "Если пароль где-то утек, меняйте его везде, где он использовался повторно.",
                    "Уникальные пароли не дают одной проблеме каскадно перейти в другие системы.",
                ],
                scenario="Соцсеть объявила об утечке. Если тот же пароль использовался для почты или CRM, это уже не личная история, а корпоративный риск.",
                checklist=[
                    "Вы понимаете, что такое credential stuffing.",
                    "Вы можете определить, где повтор пароля нанес бы самый большой ущерб.",
                    "У вас есть практичный способ быстро заменить повторяющиеся пароли.",
                ],
                reflection="Что произойдет в вашей команде, если пароль от почты окажется таким же, как еще в двух-трех рабочих системах?",
            ),
            lesson_seed(
                locale="ru",
                topic_key="phishing",
                title="Как распознать фишинговое письмо",
                summary="Фишинг редко выглядит явно вредоносным. Он маскируется под срочность, авторитет и привычный рабочий процесс.",
                image_key="security-phishing",
                video_url=video_url,
                duration_minutes=11,
                why_it_matters="Фишинг срабатывает, когда человек спешит, устал или слишком доверяет знакомому логотипу. Поэтому защита — это практические привычки, а не только теоретические знания.",
                practice=[
                    "Проверяйте домен отправителя, а не только отображаемое имя.",
                    "Смотрите реальный адрес ссылки до клика.",
                    "Считайте тревожными сигналами срочность, секретность и странные запросы на оплату или доступ.",
                    "Относитесь к неожиданным вложениям как к высокому риску до проверки.",
                ],
                scenario="Письмо с пометкой «Финансы: срочно» просит скачать новую форму платежа до конца дня. Логотип знакомый, но домен и тип вложения не совпадают с обычным процессом.",
                checklist=[
                    "Вы сначала проверяете домен и адрес ссылки.",
                    "Вы знаете, как сообщить о подозрительном письме.",
                    "Вы не пересылаете сомнительное письмо всем подряд до проверки службой ИБ.",
                ],
                reflection="Какой признак фишинга вы лично с большей вероятностью пропустите в спешке: домен, срочность или странное вложение?",
            ),
            lesson_seed(
                locale="ru",
                topic_key="data",
                title="Работа с конфиденциальными файлами",
                summary="Безопасная работа с чувствительными данными — это правильный канал, правильный круг получателей и правильное место хранения.",
                image_key="security-confidential-files",
                video_url=video_url,
                duration_minutes=10,
                why_it_matters="Файл может быть полезным и корректным, но все равно стать причиной инцидента, если попадет не в тот ящик, на не то устройство или в не ту папку. Большинство ошибок происходит в обычной рутине.",
                practice=[
                    "Передавайте файлы только через утвержденные системы с управляемым доступом.",
                    "Проверяйте получателей и права перед отправкой ссылки или вложения.",
                    "Храните клиентские и кадровые данные только там, где контролируются доступ и срок хранения.",
                    "Удаляйте лишние копии после того, как нужная версия зафиксирована в системе.",
                ],
                scenario="Вам нужно поработать с клиентской таблицей из дома. Безопасный путь — использовать утвержденный удаленный доступ, а не отправлять файл себе на личную почту.",
                checklist=[
                    "Вы знаете, какие системы одобрены для конфиденциальных данных.",
                    "Вы проверяете получателей перед отправкой файла или ссылки.",
                    "Вы не создаете лишние неконтролируемые копии ради удобства.",
                ],
                reflection="Какой «безобидный» shortcut с файлами в вашей среде чаще всего может превратиться в утечку данных?",
            ),
            lesson_seed(
                locale="ru",
                topic_key="incident",
                title="Что делать при подозрении на компрометацию",
                summary="Первые минуты после сомнительного клика, странного письма или аномалии в аккаунте важнее, чем идеальный диагноз.",
                image_key="security-incident-response",
                video_url=video_url,
                duration_minutes=9,
                why_it_matters="Люди откладывают сообщение об инциденте, потому что хотят сначала убедиться. Именно эта задержка часто дает злоумышленнику дополнительное время. Ранний сигнал помогает быстрее локализовать риск.",
                practice=[
                    "Используйте утвержденный канал инцидентов сразу, как только событие выглядит подозрительным.",
                    "Следуйте инструкциям по сдерживанию, а не импровизируйте исправления.",
                    "Сохраняйте доказательства: скриншоты, время, письмо, адрес ссылки.",
                    "Не скрывайте ошибку — скорость и точность реакции важнее чувства вины.",
                ],
                scenario="Вы открыли подозрительное вложение, но ничего явного не случилось. Этого уже достаточно, чтобы сразу сообщить о событии и сохранить детали для команды ИБ.",
                checklist=[
                    "Вы знаете канал для сообщений об инцидентах и когда его использовать.",
                    "Вы умеете отличать меры сдерживания от догадок и самодеятельности.",
                    "Вы понимаете, что быстрая эскалация ценнее показной уверенности.",
                ],
                reflection="Если бы вы прямо сейчас заподозрили компрометацию, кому и что именно вы бы написали первым сообщением?",
            ),
        ],
        test_title="Адаптивный тест по информационной безопасности",
        questions=[
            QuestionSeed("passwords", 1, "Как безопаснее всего хранить много уникальных паролей?", "Рекомендуемый вариант — менеджер паролей.", [("Использовать менеджер паролей", True), ("Записать их на стикере", False), ("Повторять один сильный пароль везде", False)]),
            QuestionSeed("phishing", 1, "Что проверить первым в подозрительном письме?", "Начинать лучше с адреса и домена отправителя.", [("Адрес и домен отправителя", True), ("Только красивый ли логотип", False), ("Только цветовое оформление письма", False)]),
            QuestionSeed("data", 2, "Можно ли отправить конфиденциальный файл на личную почту, чтобы поработать дома?", "Чувствительные данные должны оставаться только в одобренных корпоративных каналах.", [("Нет, использовать можно только утвержденные каналы", True), ("Да, если файл небольшой", False), ("Да, если потом удалить его", False)]),
            QuestionSeed("incident", 2, "Вы нажали на подозрительную ссылку. Что делать первым?", "Раннее сообщение снижает последствия.", [("Сразу сообщить об инциденте через утвержденный канал", True), ("Подождать, пока что-то сломается", False), ("Тихо почистить историю браузера", False)]),
            QuestionSeed("passwords", 3, "Почему повторное использование пароля опасно даже при сложном пароле?", "Одна утечка может открыть доступ сразу в несколько систем.", [("Одна утечка может скомпрометировать несколько аккаунтов", True), ("Сложные пароли из-за этого быстрее истекают", False), ("Из-за этого длина пароля перестает учитываться", False)]),
            QuestionSeed("phishing", 3, "Какой признак сильнее всего указывает на фишинг?", "Несовпадение ожидаемого и фактического домена — серьезный красный флаг.", [("Ссылка ведет на другой домен, чем ожидается", True), ("Вежливое приветствие", False), ("Обычная подпись внизу письма", False)]),
            QuestionSeed("data", 4, "Коллега просит клиентские данные, но у него нет бизнес-необходимости. Что делать?", "Доступ к данным должен опираться на принцип need-to-know.", [("Отказать и направить запрос через правильный путь согласования", True), ("Отправить только часть файла", False), ("Поделиться, если коллега работает в том же офисе", False)]),
            QuestionSeed("incident", 4, "Почему об инциденте ИБ нужно сообщать быстро, даже если вы не уверены?", "Быстрый сигнал помогает сдержать угрозу и сохранить доказательства.", [("Ранняя реакция может уменьшить ущерб и сохранить следы инцидента", True), ("Поздний отчет автоматически удаляет данные", False), ("Если есть сомнение, значит инцидента точно нет", False)]),
            QuestionSeed("passwords", 5, "Какой набор лучше всего отражает хорошую парольную практику?", "Уникальные пароли, менеджер, MFA и отсутствие шаринга — базовый стандарт.", [("Уникальные пароли, менеджер, MFA и без шаринга", True), ("Общий пароль команды и ежемесячный повтор", False), ("Простой пароль и записка в блокноте", False)]),
            QuestionSeed("phishing", 5, "Письмо требует открыть вложение в течение 10 минут и пришло с неизвестного адреса. Лучшее действие?", "Срочность плюс неизвестный отправитель — классический паттерн фишинга.", [("Не открывать и сообщить в ИБ", True), ("Открыть на телефоне вместо ноутбука", False), ("Переслать коллегам спросить, выглядит ли безопасно", False)], estimated_seconds=35),
        ],
    )


def _ru_service_course() -> CourseSeed:
    video_url = "/media/service-demo.mp4"
    return CourseSeed(
        title="Стандарты клиентского сервиса и сложные разговоры",
        description="Курс для первой линии: прием запросов, ожидания по SLA, работа с жалобами и деэскалация напряженных диалогов.",
        topics=[
            TopicSeed("sla", "Сервисные ожидания", "Сроки реакции, владение запросом и приоритизация."),
            TopicSeed("tone", "Профессиональный тон", "Ясная, эмпатичная и ориентированная на результат коммуникация."),
            TopicSeed("complaints", "Работа с жалобами", "Структура для выслушивания, уточнения и решения."),
            TopicSeed("deescalation", "Деэскалация", "Как снижать напряжение, не нарушая политику и SLA."),
        ],
        lessons=[
            lesson_seed(
                locale="ru",
                topic_key="sla",
                title="Кто владеет запросом",
                summary="Первый ответивший сразу владеет следующим шагом, даже если позже задачу решает другая команда.",
                image_key="service-request-ownership",
                video_url=video_url,
                duration_minutes=8,
                why_it_matters="Для клиента задержка ощущается как тишина и путаница, а не как внутренний роутинг между командами. Владение запросом означает, что клиент всегда понимает, кто координирует следующий шаг.",
                practice=[
                    "Быстро подтверждайте получение запроса и называйте следующий checkpoint.",
                    "Сразу уточняйте, вы решаете задачу сами или координируете передачу.",
                    "При handoff сохраняйте в системе видимую запись о владельце.",
                ],
                scenario="Запрос попал не в ту очередь. Сильный сервис — не просто молча перекинуть его дальше, а сообщить клиенту, что происходит, кто теперь ведет кейс и когда будет обновление.",
                checklist=[
                    "У каждого активного запроса есть видимый владелец.",
                    "Клиент знает время следующего обновления.",
                    "Роутинг не снимает ответственности за коммуникацию.",
                ],
                reflection="На каком этапе ваши запросы чаще всего «теряют владельца» при передаче между командами?",
            ),
            lesson_seed(
                locale="ru",
                topic_key="tone",
                title="Эмпатия без ложных обещаний",
                summary="Эмпатия не означает соглашаться со всем. Важно признать влияние проблемы и при этом честно говорить о следующем реальном шаге.",
                image_key="service-empathy",
                video_url=video_url,
                duration_minutes=10,
                why_it_matters="В сложном разговоре тон либо снижает напряжение, либо усиливает его. Уважительный и конкретный ответ строит доверие еще до полного решения проблемы.",
                practice=[
                    "Называйте эмоцию клиента, не звуча при этом оборонительно.",
                    "Обещайте только тот следующий шаг, который действительно можете выполнить.",
                    "Формулируйте сроки аккуратно и конкретно.",
                    "Избегайте вежливых, но пустых фраз без полезного смысла.",
                ],
                scenario="Клиент говорит, что уже дважды объяснял одну и ту же проблему. Сильный ответ признает раздражение, точно пересказывает суть кейса и называет следующий момент обновления.",
                checklist=[
                    "В ответе есть и эмпатия, и конкретное действие.",
                    "Вы не обещаете того, что вне вашей зоны контроля.",
                    "Срок в ответе можно потом проверить и подтвердить.",
                ],
                reflection="Какая фраза в вашей сервисной переписке звучит вежливо, но почти не помогает клиенту продвинуться дальше?",
            ),
            lesson_seed(
                locale="ru",
                topic_key="complaints",
                title="Структура обработки жалобы",
                summary="Хорошая работа с жалобой — это повторяемая последовательность: выслушать, переформулировать, уточнить, предложить варианты и подтвердить срок.",
                image_key="service-complaints",
                video_url=video_url,
                duration_minutes=11,
                why_it_matters="Жалоба кажется хаотичной, когда сотрудник пытается решить все сразу. Видимая структура успокаивает разговор и защищает качество решения.",
                practice=[
                    "Дайте клиенту закончить первоначальное описание проблемы.",
                    "Переформулируйте суть своими словами, чтобы подтвердить понимание.",
                    "Задавайте только те уточняющие вопросы, которые нужны для следующего решения.",
                    "Закрывайте ответ вариантами, владельцем и сроком.",
                ],
                scenario="Клиент жалуется на сорванное обещание и плохой предыдущий ответ. Вместо защиты прошлой коммуникации вы уточняете факты, подтверждаете бизнес-влияние и договариваетесь о следующем checkpoint.",
                checklist=[
                    "Вы подтвердили проблему до предложения решения.",
                    "Вы сократили повторение, сделав ясное резюме.",
                    "Финальный ответ включал следующие шаги и срок.",
                ],
                reflection="Что для вас сложнее в работе с жалобой: выслушать до конца, уточнить или закрепить срок?",
            ),
            lesson_seed(
                locale="ru",
                topic_key="deescalation",
                title="Как успокоить напряженного клиента",
                summary="Деэскалация — это снижение эмоционального градуса при сохранении пользы, фактов и соблюдения правил.",
                image_key="service-deescalation",
                video_url=video_url,
                duration_minutes=9,
                why_it_matters="Клиент успокаивается, когда чувствует, что его услышали и что следующий шаг реален. Напряжение растет, когда в ответ звучат скрипт, оправдания или туманные обещания.",
                practice=[
                    "Снижайте темп речи и используйте короткие фактические фразы.",
                    "Разделяйте эмоции и факты, не обесценивая ни одно из них.",
                    "Переводите разговор к конкретному следующему checkpoint.",
                    "Не зеркальте сарказм, обвинения и повышенный эмоциональный тон.",
                ],
                scenario="Звонящий говорит, что ваша команда бесполезна, потому что он ждет слишком долго. Лучшая реакция — не спорить о справедливости, а пересказать кейс, подтвердить влияние и назвать следующий шаг и время.",
                checklist=[
                    "Ваш ответ снизил напряжение, а не усилил его.",
                    "Вы не приняли тон клиента на личный счет.",
                    "Финал ответа заканчивается контролируемым следующим действием.",
                ],
                reflection="Что лично вам помогает сохранять спокойствие, когда собеседник зол или несправедлив?",
            ),
            lesson_seed(
                locale="ru",
                topic_key="sla",
                title="Эскалация просроченных кейсов",
                summary="Кейс под риском SLA нужно эскалировать заранее, с чистым контекстом, бизнес-влиянием и понятным запросом на помощь.",
                image_key="service-overdue-escalation",
                video_url=video_url,
                duration_minutes=8,
                why_it_matters="Поздняя эскалация создает неприятные сюрпризы и для клиента, и для внутренних команд. Эскалация работает лучше всего, пока еще есть время защитить срок, а не после его срыва.",
                practice=[
                    "Поднимайте риск до фактического нарушения SLA.",
                    "Передавайте текущее состояние, блокер, влияние и какой именно support нужен.",
                    "Используйте факты и таймстемпы вместо раздражения.",
                    "После внутренней эскалации честно обновляйте клиента.",
                ],
                scenario="Зависимость от подрядчика блокирует решение, а обещанный срок ответа почти истек. Сильная практика — эскалировать с фактами и влиянием, а не ждать самого нарушения срока.",
                checklist=[
                    "Вы можете объяснить риск кейса одним коротким резюме.",
                    "Вы точно знаете, какое решение или помощь запрашиваете.",
                    "Вы можете честно обновить клиента без перекладывания вины на другие команды.",
                ],
                reflection="Какой информации чаще всего не хватает в сообщении об эскалации просроченного кейса в вашей организации?",
            ),
        ],
        test_title="Сценарный тест по клиентскому сервису",
        questions=[
            QuestionSeed("sla", 1, "Что сотрудник поддержки должен сделать первым после получения клиентского запроса?", "Сначала нужно подтвердить получение и назвать следующий шаг.", [("Подтвердить запрос и обозначить следующий шаг", True), ("Ждать полного решения и молчать", False), ("Переслать, не читая", False)]),
            QuestionSeed("tone", 1, "Какой тон лучше в напряженном разговоре?", "Профессиональный и уважительный тон снижает трение.", [("Спокойный, уважительный и конкретный", True), ("Холодный и односложный", False), ("Оборонительный и саркастичный", False)]),
            QuestionSeed("complaints", 2, "Зачем переформулировать проблему клиента своими словами?", "Это подтверждает понимание и сокращает повторное объяснение.", [("Чтобы показать, что вы правильно поняли суть", True), ("Чтобы быстрее завершить разговор без действий", False), ("Чтобы переложить вину на клиента", False)]),
            QuestionSeed("deescalation", 2, "Клиент стал эмоциональным. Что помогает больше всего?", "Спокойная структура и следующие шаги работают лучше спора.", [("Признать раздражение и перевести разговор к следующим шагам", True), ("Сразу спорить по каждому пункту", False), ("Полностью игнорировать эмоции", False)]),
            QuestionSeed("sla", 3, "Какой главный риск, если не закрепить владельца запроса?", "Нечеткое владение ведет к зависанию между командами.", [("Запрос может застрять между командами", True), ("SLA автоматически поменяется", False), ("Нельзя будет делать заметки", False)]),
            QuestionSeed("tone", 3, "Какая фраза лучше?", "Сильная фраза сочетает эмпатию и конкретное действие.", [("Понимаю, что задержка неприятна; обновлю вас до 15:00", True), ("Успокойтесь и ждите", False), ("Это не моя проблема", False)]),
            QuestionSeed("complaints", 4, "Какая последовательность лучше для обработки жалобы?", "Структура снижает неопределенность и помогает восстановить доверие.", [("Выслушать, уточнить, предложить варианты и подтвердить срок", True), ("Уйти в оправдания и быстро закрыть кейс", False), ("Сразу пообещать компенсацию без проверки правил", False)]),
            QuestionSeed("deescalation", 4, "Почему нельзя обещать то, что вы не можете гарантировать?", "Нарушенное обещание усиливает раздражение и создает вторую жалобу.", [("Это подрывает доверие и создает новый повод для жалобы", True), ("От этого CRM начинает работать медленнее", False), ("Если тон дружелюбный, это неважно", False)]),
            QuestionSeed("sla", 5, "Кейс заблокирован другой командой и SLA под риском. Лучшее действие?", "Ранняя эскалация с контекстом и влиянием защищает срок.", [("Рано эскалировать с контекстом, влиянием и нужным действием", True), ("Ждать, пока SLA уже сорвется", False), ("Ничего не говорить клиенту до полного решения", False)]),
            QuestionSeed("deescalation", 5, "Что лучше всего поддерживает деэскалацию в сложном звонке?", "Контроль над тоном и процессом создает ощущение надежности.", [("Спокойный тон, краткое резюме фактов и следующий checkpoint", True), ("Зеркалить агрессивный тон клиента", False), ("Зачитывать политику без адаптации", False)], estimated_seconds=35),
        ],
    )


def create_tenant_people(db, tenant: Tenant, role_map: dict[str, Role], password_hash: str) -> tuple[User, User, list[User]]:
    admin = User(email=f"admin@{tenant.code}.example.com", full_name=f"{tenant.name} Admin", password_hash=password_hash, preferred_locale=tenant.locale)
    teacher = User(email=f"teacher@{tenant.code}.example.com", full_name=f"{tenant.name} Teacher", password_hash=password_hash, preferred_locale=tenant.locale)
    learners = [
        User(
            email=f"learner{i}@{tenant.code}.example.com",
            full_name=f"{tenant.name} Learner {i}",
            password_hash=password_hash,
            preferred_locale=tenant.locale,
        )
        for i in range(1, 13)
    ]
    db.add_all([admin, teacher, *learners])
    db.flush()
    db.add(Membership(user_id=admin.id, tenant_id=tenant.id, role_id=role_map[RoleName.org_admin.value].id, is_active=True))
    db.add(Membership(user_id=teacher.id, tenant_id=tenant.id, role_id=role_map[RoleName.teacher.value].id, is_active=True))
    for learner in learners:
        db.add(Membership(user_id=learner.id, tenant_id=tenant.id, role_id=role_map[RoleName.learner.value].id, is_active=True))
    return admin, teacher, learners


def create_grouping(db, tenant: Tenant, learners: list[User]) -> Group:
    group = Group(tenant_id=tenant.id, name=f"{tenant.name} New Hires")
    db.add(group)
    db.flush()
    for learner in learners[:6]:
        db.add(GroupMember(tenant_id=tenant.id, group_id=group.id, user_id=learner.id))
    return group


def populate_course(
    db,
    *,
    tenant: Tenant,
    teacher: User,
    learners: list[User],
    seed: CourseSeed,
    group: Group,
    topic_registry: dict[int, dict[str, Topic]],
) -> tuple[Course, Test]:
    course = Course(
        tenant_id=tenant.id,
        title=seed.title,
        description=seed.description,
        status="published",
        created_by_id=teacher.id,
        is_published=True,
    )
    db.add(course)
    db.flush()

    local_topics: dict[str, Topic] = {}
    for topic_seed in seed.topics:
        topic = Topic(tenant_id=tenant.id, title=topic_seed.title, description=topic_seed.description)
        db.add(topic)
        db.flush()
        local_topics[topic_seed.key] = topic
    topic_registry[course.id] = local_topics

    for index, lesson_seed in enumerate(seed.lessons, start=1):
        db.add(
            Lesson(
                tenant_id=tenant.id,
                course_id=course.id,
                topic_id=local_topics[lesson_seed.topic_key].id,
                title=lesson_seed.title,
                summary=lesson_seed.summary,
                content=lesson_seed.content,
                content_pages=deepcopy(lesson_seed.content_pages),
                duration_minutes=lesson_seed.duration_minutes,
                image_url=lesson_seed.image_url,
                video_url=lesson_seed.video_url,
                sort_order=index,
            )
        )
    db.flush()
    stored_lessons = db.scalars(
        select(Lesson)
        .where(Lesson.tenant_id == tenant.id, Lesson.course_id == course.id)
        .order_by(Lesson.sort_order, Lesson.id)
    ).all()
    for stored_lesson, lesson_seed in zip(stored_lessons, seed.lessons):
        stored_lesson.summary = lesson_seed.summary
        stored_lesson.content = lesson_seed.content
        stored_lesson.content_pages = deepcopy(lesson_seed.content_pages)
        stored_lesson.duration_minutes = lesson_seed.duration_minutes
        stored_lesson.image_url = lesson_seed.image_url
        stored_lesson.video_url = lesson_seed.video_url

    test = Test(
        tenant_id=tenant.id,
        course_id=course.id,
        title=seed.test_title,
        baseline_difficulty=3,
        question_limit=min(10, len(seed.questions)),
    )
    db.add(test)
    db.flush()

    for question_seed in seed.questions:
        question = Question(
            tenant_id=tenant.id,
            test_id=test.id,
            text=question_seed.text,
            explanation=question_seed.explanation,
            difficulty=question_seed.difficulty,
            estimated_seconds=question_seed.estimated_seconds,
        )
        db.add(question)
        db.flush()
        db.add(QuestionTopic(tenant_id=tenant.id, question_id=question.id, topic_id=local_topics[question_seed.topic_key].id))
        for option_text, is_correct in question_seed.options:
            db.add(AnswerOption(question_id=question.id, text=option_text, is_correct=is_correct))

    for index, learner in enumerate(learners, start=1):
        progress = min(100, (index % 5) * 20)
        db.add(
            Enrollment(
                tenant_id=tenant.id,
                course_id=course.id,
                user_id=learner.id,
                progress_percent=progress,
                completed=progress >= 100,
            )
        )
    db.add(CourseAssignment(tenant_id=tenant.id, course_id=course.id, group_id=group.id, assigned_by_id=teacher.id))
    db.add(CourseAssignment(tenant_id=tenant.id, course_id=course.id, user_id=learners[-1].id, assigned_by_id=teacher.id))
    return course, test


def normalize_lesson_media(db, *, tenant: Tenant) -> None:
    courses = {course.id: course for course in db.query(Course).filter(Course.tenant_id == tenant.id).all()}
    lessons = db.query(Lesson).filter(Lesson.tenant_id == tenant.id).all()
    for lesson in lessons:
        course = courses.get(lesson.course_id)
        if course is None:
            continue
        cover_path = localized_cover_path(course.title, tenant.locale)
        image_path = lesson.image_url or cover_path
        video_path = lesson.video_url
        pages = lesson.content_pages or []
        for page in pages:
            blocks = page.get("blocks", [])
            for block in blocks:
                if block.get("type") == "image":
                    block["url"] = image_path
                    block.setdefault("alt", lesson.title)
                if block.get("type") == "video" and video_path:
                    block["url"] = video_path
                    block.setdefault("status", "ready")
        lesson.content_pages = pages


def build_attempt_history(db, *, tenant: Tenant, learners: list[User], tests: list[Test], topic_registry: dict[int, dict[str, Topic]]) -> None:
    for learner_index, learner in enumerate(learners[:5]):
        for test_index, test in enumerate(tests):
            questions = db.query(Question).filter(Question.test_id == test.id).order_by(Question.id).limit(4).all()
            if not questions:
                continue
            attempt = Attempt(
                tenant_id=tenant.id,
                test_id=test.id,
                user_id=learner.id,
                current_difficulty=3,
                asked_question_ids=[question.id for question in questions],
                difficulty_path=[3, 4, 3, 2],
                status="finished",
            )
            db.add(attempt)
            db.flush()

            weak_topics = []
            incorrect_topic_id = None
            for idx, question in enumerate(questions):
                correct_option = db.query(AnswerOption).filter(AnswerOption.question_id == question.id, AnswerOption.is_correct.is_(True)).first()
                wrong_option = db.query(AnswerOption).filter(AnswerOption.question_id == question.id, AnswerOption.is_correct.is_(False)).first()
                is_correct = (idx + learner_index + test_index) % 3 != 0
                selected = correct_option if is_correct else wrong_option
                db.add(
                    AttemptAnswer(
                        tenant_id=tenant.id,
                        attempt_id=attempt.id,
                        question_id=question.id,
                        answer_option_id=selected.id if selected else None,
                        is_correct=is_correct,
                        response_seconds=20 + idx * 12 + (12 if not is_correct else 0),
                    )
                )
                if not is_correct:
                    link = db.query(QuestionTopic).filter(QuestionTopic.question_id == question.id).first()
                    incorrect_topic_id = link.topic_id if link else None

            if incorrect_topic_id is None:
                incorrect_topic_id = next(iter(topic_registry[test.course_id].values())).id
            weak_topic = db.get(Topic, incorrect_topic_id)
            weak_topics.append({"topic_id": weak_topic.id, "topic_title": weak_topic.title, "score": 3 + learner_index})
            result = Result(
                tenant_id=tenant.id,
                attempt_id=attempt.id,
                score_percent=50 + (test_index * 10),
                weak_topics=weak_topics,
                recommendation_count=2,
            )
            db.add(result)
            db.flush()
            lesson = db.query(Lesson).filter(Lesson.course_id == test.course_id, Lesson.topic_id == weak_topic.id).order_by(Lesson.sort_order).first()
            db.add(
                Recommendation(
                    tenant_id=tenant.id,
                    user_id=learner.id,
                    result_id=result.id,
                    topic_id=weak_topic.id,
                    lesson_id=lesson.id if lesson else None,
                    priority=1,
                    text=review_topic_recommendation(tenant.locale, weak_topic.title),
                )
            )
            db.add(
                Recommendation(
                    tenant_id=tenant.id,
                    user_id=learner.id,
                    result_id=result.id,
                    topic_id=weak_topic.id,
                    lesson_id=lesson.id if lesson else None,
                    priority=2,
                    text=follow_up_recommendation(tenant.locale),
                )
            )


def run() -> None:
    reset_database()
    db = SessionLocal()

    roles = [Role(name=role.value, description=role.value.replace("_", " ")) for role in RoleName]
    db.add_all(roles)
    db.flush()
    role_map = {role.name: role for role in roles}

    tenants = [
        Tenant(name="Acme Learning", code="acme", locale="ru"),
        Tenant(name="Beta Skills", code="beta", locale="en"),
        Tenant(name="Gamma Academy", code="gamma", locale="en"),
    ]
    db.add_all(tenants)
    db.flush()

    password_hash = hash_password("Password123!")
    sys_admin = User(email="sysadmin@example.com", full_name="System Admin", password_hash=password_hash, preferred_locale="ru")
    db.add(sys_admin)
    db.flush()

    for tenant in tenants:
        db.add(Membership(user_id=sys_admin.id, tenant_id=tenant.id, role_id=role_map[RoleName.system_admin.value].id, is_active=True))

    for tenant in tenants:
        catalog = build_course_catalog(tenant.locale)
        admin, teacher, learners = create_tenant_people(db, tenant, role_map, password_hash)
        group = create_grouping(db, tenant, learners)
        topic_registry: dict[int, dict[str, Topic]] = {}
        tests: list[Test] = []
        for course_seed in catalog:
            _, test = populate_course(
                db,
                tenant=tenant,
                teacher=teacher,
                learners=learners,
                seed=course_seed,
                group=group,
                topic_registry=topic_registry,
            )
            tests.append(test)
        normalize_lesson_media(db, tenant=tenant)
        build_attempt_history(db, tenant=tenant, learners=learners, tests=tests, topic_registry=topic_registry)

    db.commit()
    db.close()
    print("Seed completed. Demo password: Password123!")


if __name__ == "__main__":
    run()

