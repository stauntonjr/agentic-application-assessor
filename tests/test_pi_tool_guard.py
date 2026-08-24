import json
import unittest

from tools.pi_tool_probe import all_tool_ends, final_assistant_text, json_events, settled, tool_ends


class PiToolProbeTests(unittest.TestCase):
    def test_json_events_ignores_non_json_startup_output(self) -> None:
        output = "startup noise\n" + json.dumps({"type": "agent_settled"}) + "\n"
        self.assertEqual([{"type": "agent_settled"}], json_events(output))

    def test_final_assistant_text_uses_last_completed_answer(self) -> None:
        events = [
            {
                "type": "message_end",
                "message": {
                    "role": "assistant",
                    "stopReason": "stop",
                    "content": [{"type": "text", "text": "first"}],
                },
            },
            {
                "type": "message_end",
                "message": {
                    "role": "assistant",
                    "stopReason": "stop",
                    "content": [{"type": "text", "text": "final"}],
                },
            },
        ]
        self.assertEqual("final", final_assistant_text(events))

    def test_tool_and_settled_filters(self) -> None:
        events = [
            {"type": "tool_execution_end", "toolName": "read"},
            {"type": "tool_execution_end", "toolName": "other"},
            {"type": "agent_settled"},
        ]
        self.assertEqual(1, len(tool_ends(events, "read")))
        self.assertEqual(2, len(all_tool_ends(events)))
        self.assertTrue(settled(events))


if __name__ == "__main__":
    unittest.main()
