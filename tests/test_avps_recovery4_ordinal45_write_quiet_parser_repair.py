from pathlib import Path
import re
import textwrap
import unittest


WORKFLOW = Path('.github/workflows/avps-v2-recovery4-ordinal45-final-dispatch-publisher-v3.yml')
BEGIN = '# BEGIN_WRITE_QUIET_END_LINE_PARSER_V1'
END = '# END_WRITE_QUIET_END_LINE_PARSER_V1'


def _workflow_text():
    return WORKFLOW.read_text(encoding='utf-8')


def _parser_namespace():
    text = _workflow_text()
    pattern = re.compile(
        r'^\s*# BEGIN_WRITE_QUIET_END_LINE_PARSER_V1\n(.*?)^\s*# END_WRITE_QUIET_END_LINE_PARSER_V1$',
        re.MULTILINE | re.DOTALL,
    )
    blocks = pattern.findall(text)
    if len(blocks) != 3:
        raise AssertionError(f'expected three embedded parser blocks, got {len(blocks)}')
    normalized = [textwrap.dedent(block).strip() for block in blocks]
    if len(set(normalized)) != 1:
        raise AssertionError('embedded WRITE_QUIET parser blocks drifted')
    namespace = {}
    exec(normalized[0], namespace)
    return namespace


class WriteQuietParserRepairContract(unittest.TestCase):
    def test_embedded_parser_is_identical_at_all_three_call_sites(self):
        namespace = _parser_namespace()
        self.assertIn('write_quiet_end_binding', namespace)
        self.assertIn('record_write_quiet_end', namespace)
        self.assertIn('is_write_quiet_begin', namespace)

    def test_valid_marker_line_and_standalone_metadata_aliases(self):
        parse = _parser_namespace()['write_quiet_end_binding']
        for key in ('begin', 'beginComment', 'begin_comment'):
            with self.subTest(key=key, surface='marker'):
                self.assertEqual(parse(f'WRITE_QUIET_END | stage=x | {key}=123'), 123)
            with self.subTest(key=key, surface='standalone'):
                self.assertEqual(parse(f'WRITE_QUIET_END | stage=x\n{key}=123'), 123)

    def test_legacy_space_delimited_end_and_owner_prefix(self):
        parse = _parser_namespace()['write_quiet_end_binding']
        self.assertEqual(parse('WRITE_QUIET_END begin=123 stage=x'), 123)
        self.assertEqual(parse('WRITE_QUIET_END beginComment=123 stage=x'), 123)
        self.assertEqual(parse('WRITE_QUIET_END begin_comment=123 stage=x'), 123)
        self.assertEqual(
            parse('TOTAL_SKY_OWNER::WRITE_QUIET_END | stage=x | beginComment=123'),
            123,
        )

    def test_end_marker_grammar_is_first_line_exact(self):
        parse = _parser_namespace()['write_quiet_end_binding']
        for body in (
            'header\nATMOSPHERE_OWNER::WRITE_QUIET_END | stage=x\nbegin=123',
            'header\nWRITE_QUIET_END | beginComment=123',
            'header\n> WRITE_QUIET_END | beginComment=123',
            'header\nnot-a-marker: WRITE_QUIET_END | beginComment=123',
            'header\n`WRITE_QUIET_END | beginComment=123`',
        ):
            with self.subTest(body=body):
                self.assertIsNone(parse(body))

    def test_begin_grammar_is_first_line_exact_and_owner_aware(self):
        is_begin = _parser_namespace()['is_write_quiet_begin']
        for body in (
            'WRITE_QUIET_BEGIN | stage=x',
            'TOTAL_SKY_OWNER::WRITE_QUIET_BEGIN | stage=x',
            'ATMOSPHERE_OWNER::WRITE_QUIET_BEGIN token=x',
        ):
            with self.subTest(body=body):
                self.assertTrue(is_begin(body))
        for body in (
            'prose WRITE_QUIET_BEGIN | stage=x',
            'Total_Sky_OWNER::WRITE_QUIET_BEGIN | stage=x',
            'TOTAL-SKY-OWNER::WRITE_QUIET_BEGIN | stage=x',
            'header\nTOTAL_SKY_OWNER::WRITE_QUIET_BEGIN | stage=x',
        ):
            with self.subTest(body=body):
                self.assertFalse(is_begin(body))

    def test_unrelated_prose_and_quoted_markers_do_not_close(self):
        parse = _parser_namespace()['write_quiet_end_binding']
        self.assertIsNone(parse('prose WRITE_QUIET_END | beginComment=123'))
        self.assertIsNone(parse('header\n> WRITE_QUIET_END | beginComment=123'))
        self.assertIsNone(parse('header\nnot-a-marker: WRITE_QUIET_END | beginComment=123'))
        self.assertIsNone(parse('header\n`WRITE_QUIET_END | beginComment=123`'))

    def test_malformed_ambiguous_and_conflicting_bindings_fail_closed(self):
        parse = _parser_namespace()['write_quiet_end_binding']
        bad = (
            'WRITE_QUIET_END | stage=x',
            'WRITE_QUIET_END | beginComment=abc',
            'WRITE_QUIET_END | beginComment=123 | beginComment=123',
            'WRITE_QUIET_END | begin=123 | beginComment=123',
            'WRITE_QUIET_END begin=123 beginComment=124',
            'WRITE_QUIET_END | stage=x\nbeginComment=123\nbegin=123',
            'WRITE_QUIET_END | beginComment=123\nbegin=124',
            'TOTAL_SKY_OWNER::WRITE_QUIET_END | stage=x\nNarrative only with historical `begin=123` mention',
        )
        for body in bad:
            with self.subTest(body=body):
                with self.assertRaises(SystemExit):
                    parse(body)

    def test_mismatched_and_duplicate_bindings_fail_closed(self):
        record = _parser_namespace()['record_write_quiet_end']
        closed = set()
        self.assertTrue(
            record(
                'WRITE_QUIET_END | stage=x\nbeginComment=123',
                200,
                {123},
                closed,
            )
        )
        self.assertEqual(closed, {123})
        with self.assertRaises(SystemExit):
            record('WRITE_QUIET_END | beginComment=123', 201, {123}, closed)
        with self.assertRaises(SystemExit):
            record('WRITE_QUIET_END | beginComment=999', 202, {123}, set())
        with self.assertRaises(SystemExit):
            record('WRITE_QUIET_END | beginComment=300', 250, {300}, set())

    def test_old_first_line_only_end_parser_is_gone_and_writer_is_canonical(self):
        text = _workflow_text()
        self.assertEqual(text.count(BEGIN), 3)
        self.assertEqual(text.count(END), 3)
        self.assertNotIn("first.startswith('WRITE_QUIET_END')", text)
        self.assertNotIn("elif first.startswith('WRITE_QUIET_BEGIN'):", text)
        self.assertIn("elif is_write_quiet_begin(body):", text)
        self.assertIn(
            "end_body=f'WRITE_QUIET_END | AVPS_V2_RECOVERY4_ORDINAL45_SNAPSHOT_V1 | beginComment={begin} |",
            text,
        )
        self.assertNotIn(
            "end_body=f'WRITE_QUIET_END | AVPS_V2_RECOVERY4_ORDINAL45_SNAPSHOT_V1 | begin={begin} |",
            text,
        )


if __name__ == '__main__':
    unittest.main()
