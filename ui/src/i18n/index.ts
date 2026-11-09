import { useVeyra } from "../lib/useVeyra";
import en from "./en.json";
import it from "./it.json";
import zh from "./zh.json";

type Dictionary = Record<string, string>;

const dictionaries: Record<string, Dictionary> = { en, it, zh };
export const LANGUAGES: { code: string; label: string }[] = [
  { code: "en", label: "English" },
  { code: "it", label: "Italiano" },
  { code: "zh", label: "简体中文" },
];

export function translate(
  language: string,
  key: string,
  variables?: Record<string, string | number>,
): string {
  const dictionary = dictionaries[language] ?? dictionaries.en;
  let text = dictionary[key] ?? dictionaries.en[key] ?? key;
  if (variables) {
    for (const [name, value] of Object.entries(variables)) {
      text = text.replaceAll(`{${name}}`, String(value));
    }
  }
  return text;
}

export function useI18n() {
  const { settings } = useVeyra();
  const language = settings?.interface.language ?? "en";
  return {
    language,
    t: (key: string, variables?: Record<string, string | number>) =>
      translate(language, key, variables),
  };
}
