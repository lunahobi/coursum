import { getInitialLanguage, getMessages } from "../app-core";
import en from "./messages-en";
import ru from "./messages-ru";

export type Language = "ru" | "en";
export type UiMessages = typeof ru & typeof en;

export { getInitialLanguage, getMessages };
