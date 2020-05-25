import re


locality_regex = re.compile(r'/agas\{locality#(\d+)[^}]*\}')

pfx_counter_regex = re.compile(
    r'/([a-z_]+){locality#(\d+)/total}/(?:(?:(count|time)/)'
    r'([a-z/_-]+)|([a-z/_-]+)/(?:(count|time))),([0-9]+),'
    r'([0-9.]+),\[[a-z]+\],([0-9.\+e]+)(?:,\[([a-z]+)?\])?'
)

level_regex = re.compile(r'^max_level\s=\s(\d+)$', re.MULTILINE)
