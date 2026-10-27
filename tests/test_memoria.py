import unittest

from memoria import display_item, extract_json, render_markdown, verify_quotes


TRANSCRIPT = "In 1987, Mateo kept marigolds outside his shop. He made cinnamon tea."


class MemoriaTests(unittest.TestCase):
    def test_extract_json_from_fence(self):
        raw = '''```json
{"title":"Tea","summary":"A memory.","people":["Mateo"],"places":[],"time_references":["1987"],"themes":["family"],"quotes":["He made cinnamon tea."],"follow_up_questions":["What next?"]}
```'''
        self.assertEqual(extract_json(raw)["title"], "Tea")

    def test_missing_key_fails_closed(self):
        with self.assertRaises(ValueError):
            extract_json('{"title":"Incomplete"}')

    def test_hallucinated_quote_is_rejected(self):
        card = {"quotes": ["He made cinnamon tea.", "He owned a blue airplane."]}
        self.assertEqual(verify_quotes(card, TRANSCRIPT), ["He made cinnamon tea."])

    def test_quote_whitespace_is_normalized(self):
        self.assertEqual(verify_quotes({"quotes": ["He made   cinnamon tea."]}, TRANSCRIPT), ["He made   cinnamon tea."])

    def test_person_dict_is_human_readable(self):
        self.assertEqual(display_item({"name":"Mateo", "relationship":"Grandfather"}), "Mateo — Grandfather")

    def test_markdown_contains_transcript(self):
        card = {"title":"Shop", "summary":"A faithful summary.", "people":[], "places":[], "time_references":[], "themes":[], "quotes":[], "follow_up_questions":[]}
        transcription = {"text":TRANSCRIPT, "model":"faster-whisper/test", "language":"en"}
        rendered = render_markdown(card, transcription, 1.2)
        self.assertIn(TRANSCRIPT, rendered)
        self.assertIn("No verbatim quote", rendered)


if __name__ == "__main__":
    unittest.main()
