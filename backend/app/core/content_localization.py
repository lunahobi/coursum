from __future__ import annotations


def is_russian(locale: str | None) -> bool:
    return (locale or "").lower().startswith("ru")


def review_topic_recommendation(locale: str | None, topic_title: str) -> str:
    if is_russian(locale):
        return (
            f"\u041f\u043e\u0432\u0442\u043e\u0440\u0438\u0442\u0435 "
            f"\u0442\u0435\u043c\u0443 \u00ab{topic_title}\u00bb \u0438 "
            "\u0437\u0430\u043d\u043e\u0432\u043e \u043f\u0440\u043e\u0439\u0434\u0438\u0442\u0435 "
            "\u0441\u0432\u044f\u0437\u0430\u043d\u043d\u044b\u0439 \u0443\u0440\u043e\u043a "
            "\u043f\u0435\u0440\u0435\u0434 \u0441\u043b\u0435\u0434\u0443\u044e\u0449\u0435\u0439 "
            "\u043f\u043e\u043f\u044b\u0442\u043a\u043e\u0439."
        )
    return f"Review '{topic_title}' and repeat the linked lesson before the next attempt."


def follow_up_recommendation(locale: str | None) -> str:
    if is_russian(locale):
        return (
            "\u0421\u043d\u0430\u0447\u0430\u043b\u0430 \u0440\u0430\u0437\u0431\u0435\u0440\u0438\u0442\u0435 "
            "\u043c\u0435\u0434\u043b\u0435\u043d\u043d\u044b\u0435 \u0438 "
            "\u043d\u0435\u0432\u0435\u0440\u043d\u044b\u0435 \u043e\u0442\u0432\u0435\u0442\u044b, "
            "\u0437\u0430\u0442\u0435\u043c \u043f\u043e\u0432\u0442\u043e\u0440\u0438\u0442\u0435 "
            "\u0441\u043c\u0435\u0448\u0430\u043d\u043d\u044b\u0439 \u0442\u0435\u0441\u0442 "
            "\u043f\u043e \u0442\u0435\u043c\u0435."
        )
    return "Focus on slower and incorrect answers first, then retry a mixed-difficulty assessment."


def recommendation_reason(
    locale: str | None, topic_title: str | None, signal_score: int
) -> str:
    resolved_topic = topic_title or (
        "\u044d\u0442\u0443 \u0442\u0435\u043c\u0443" if is_russian(locale) else "this topic"
    )
    if is_russian(locale):
        if signal_score >= 4:
            return (
                f"\u041f\u043e \u0442\u0435\u043c\u0435 \u00ab{resolved_topic}\u00bb "
                "\u043d\u0430\u043a\u043e\u043f\u0438\u043b\u043e\u0441\u044c "
                "\u043d\u0435\u0441\u043a\u043e\u043b\u044c\u043a\u043e "
                "\u043e\u0448\u0438\u0431\u043e\u043a \u0438\u043b\u0438 "
                "\u043c\u0435\u0434\u043b\u0435\u043d\u043d\u044b\u0445 \u043e\u0442\u0432\u0435\u0442\u043e\u0432."
            )
        if signal_score >= 2:
            return (
                f"\u041f\u043e \u0442\u0435\u043c\u0435 \u00ab{resolved_topic}\u00bb "
                "\u0431\u044b\u043b\u0438 \u043e\u0448\u0438\u0431\u043a\u0438 "
                "\u0438\u043b\u0438 \u043e\u0442\u0432\u0435\u0442\u044b "
                "\u0437\u0430\u043d\u044f\u043b\u0438 \u0431\u043e\u043b\u044c\u0448\u0435 "
                "\u0432\u0440\u0435\u043c\u0435\u043d\u0438, \u0447\u0435\u043c "
                "\u043e\u0436\u0438\u0434\u0430\u043b\u043e\u0441\u044c."
            )
        return (
            f"\u0421\u0442\u043e\u0438\u0442 \u043a\u043e\u0440\u043e\u0442\u043a\u043e "
            f"\u043f\u043e\u0432\u0442\u043e\u0440\u0438\u0442\u044c \u0442\u0435\u043c\u0443 "
            f"\u00ab{resolved_topic}\u00bb, \u0447\u0442\u043e\u0431\u044b "
            "\u0437\u0430\u043a\u0440\u0435\u043f\u0438\u0442\u044c "
            "\u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b."
        )
    if signal_score >= 4:
        return f"There were several incorrect or slow answers in '{resolved_topic}'."
    if signal_score >= 2:
        return f"'{resolved_topic}' included incorrect or slower-than-expected answers."
    return f"A short review of '{resolved_topic}' will help reinforce the material."
