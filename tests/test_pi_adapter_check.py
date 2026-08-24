import unittest

from tools.pi_adapter_check import (
    REQUIRED_COMMANDS,
    command_errors,
    registration_errors,
    strict_schema_errors,
)


class PiAdapterCheckTests(unittest.TestCase):
    def test_expected_command_set_passes(self) -> None:
        payload = {
            "data": {
                "commands": [
                    {"name": name, "source": source} for name, source in REQUIRED_COMMANDS.items()
                ]
            }
        }
        self.assertEqual([], command_errors(payload))

    def test_missing_or_wrong_command_is_reported(self) -> None:
        payload = {"data": {"commands": [{"name": "harness-loop", "source": "skill"}]}}
        errors = command_errors(payload)
        self.assertIn("missing prompt command: harness-loop", errors)
        self.assertIn("missing extension command: harness-adapter", errors)

    def test_strict_schema_requires_closed_required_objects(self) -> None:
        schema = {
            "type": "object",
            "properties": {"value": {"type": "string"}},
            "required": [],
        }
        self.assertEqual(
            ["parameters object is not closed", "parameters does not require every property"],
            strict_schema_errors(schema),
        )

    def test_registration_rejects_missing_guard_semantics(self) -> None:
        payload = {
            "tool": {
                "name": "harness_questionnaire",
                "constrainedSampling": {"type": "json_schema", "strict": "prefer"},
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                    "additionalProperties": False,
                },
            },
            "events": ["agent_start", "tool_execution_start"],
            "guard": {},
            "audit_entry": {
                "type": "harness.invalid-tool-ceiling",
                "data": {
                    "limit": 3,
                    "observed": 3,
                    "toolNames": ["first", "second", "third"],
                },
            },
        }
        self.assertEqual(
            ["invalid-tool guard scenarios differ: {}"],
            registration_errors(payload),
        )


if __name__ == "__main__":
    unittest.main()
