import re


def get_general_counter_form_pattern():
    return re.compile(
        r'/(?P<object>[^{]+)\{locality#(?P<locality>\d+)'
        r'/(?:(?:(?P<instance1>pool#[^/]+/[^#]+)'
        r'#(?P<thread_id>\d+))|(?P<instance2>[^}]+))\}'
        r'/(?P<counter>[^@]+)(?:@(?P<params>.+))?')


def get_pfx_counter_line_pattern():
    return re.compile(
        r'^/[^{]+\{[^}]+\}/([^,]+,){4,5}[^,\n]+$', re.MULTILINE)
